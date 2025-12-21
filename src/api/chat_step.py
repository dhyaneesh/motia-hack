import os
from pydantic import BaseModel
from typing import Optional
from src.services import llm_service, tavily_service, embedding_service, clustering_service
from src.services.graph_service import graph_service
from src.services.mode_service import detect_mode, process_query
from src.services.image_service import process_image_search
import base64
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class ChatRequest(BaseModel):
    question: str
    context: dict = {}
    mode: str = "default"  # 'default', 'shopping', 'study', or 'auto'
    image: Optional[str] = None  # base64 encoded image for multi-modal search
    previousQuery: Optional[str] = None  # Previous query for context-aware graph merging

class ChatResponse(BaseModel):
    answer: str
    graph: dict
    clusters: list

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ChatAPI",
    "type": "api",
    "path": "/api/chat",
    "method": "POST",
    "description": "Process a question using AI and return an answer with an interactive knowledge graph visualization. Extracts concepts, generates embeddings, clusters related concepts, and builds a graph structure.",
    "emits": [],
    "flows": ["knowledge-graph-flow"],
    "middleware": [create_timing_middleware("ChatAPI")],
    "bodySchema": ChatRequest.model_json_schema(),
    "responseSchema": {
        200: ChatResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        body = req.get("body", {})
        question = body.get("question", "")
        mode = body.get("mode", "default")
        image = body.get("image")
        previous_query = body.get("previousQuery")  # Previous query for context-aware merging
        
        if not question and not image:
            return {
                "status": 400,
                "body": {"error": "Question or image is required"}
            }
        
        # Auto-detect mode if 'auto' or process mode
        if mode == "auto" or not mode:
            mode = detect_mode(question) if question else "default"
        
        context.logger.info("Processing request", {
            "question": question[:100] if question else None,
            "mode": mode,
            "has_image": image is not None
        })
        
        # Route to mode-specific processing (for now, default behavior)
        # Shopping and Study modes will have their own endpoints
        if mode == "shopping" or mode == "study":
            # For now, return a message directing to specific endpoints
            # In future, we can route here or keep separate endpoints
            context.logger.info(f"Mode {mode} detected, but using default processing for now")
        
        # Process image if provided
        if image:
            try:
                image_bytes = base64.b64decode(image)
                image_result = await process_image_search(image_bytes, mode)
                # Use extracted query from image
                if image_result.get("search_query"):
                    question = image_result["search_query"]
                    context.logger.info("Processed image search", {"extracted_query": question})
            except Exception as e:
                context.logger.info("Image processing failed", {"error": str(e)})
        
        # 1. Generate answer using Gemini
        answer = await llm_service.generate_answer(question)
        context.logger.info("Generated answer", {"answer_length": len(answer)})
        
        # 2. Extract concepts from question and answer (limited to 10 for performance)
        concepts = await llm_service.extract_concepts(question, answer, max_concepts=10)
        context.logger.info("Extracted concepts", {"concept_count": len(concepts)})
        
        # 3. Search Tavily for each concept to get references (parallelized for speed)
        import asyncio
        async def fetch_references(concept):
            try:
                # Reduced timeout and results for faster response
                search_results = await tavily_service.search(concept["name"], num_results=2)  # Reduced from 3 to 2
                return search_results
            except Exception as e:
                context.logger.info(f"Tavily search failed for {concept['name']}", {"error": str(e)})
                return []
        
        # Fetch all references in parallel with timeout
        reference_tasks = [fetch_references(concept) for concept in concepts]
        try:
            reference_results = await asyncio.wait_for(
                asyncio.gather(*reference_tasks, return_exceptions=True),
                timeout=10.0  # 10 second timeout for all searches
            )
        except asyncio.TimeoutError:
            context.logger.warn("Tavily searches timed out, using empty references")
            reference_results = [[] for _ in concepts]
        
        for concept, references in zip(concepts, reference_results):
            if isinstance(references, Exception):
                concept["references"] = []
            else:
                concept["references"] = references
        
        # 4. Generate embeddings for all concepts (batch API for speed)
        embedding_texts = [f"{c['name']} {c.get('description', '')}" for c in concepts]
        embeddings = await embedding_service.get_embeddings(embedding_texts)
        context.logger.info("Generated embeddings", {"embedding_count": len(embeddings)})
        
        # 5. Load existing graph state to continue building on it
        existing_node_data = await context.state.get("knowledge_graph", "node_data") or {}
        existing_graph_nodes = await context.state.get("knowledge_graph", "graph_nodes") or []
        existing_edges = await context.state.get("knowledge_graph", "graph_edges") or []
        existing_embeddings = await context.state.get("knowledge_graph", "embeddings") or {}
        
        # Unwrap data if it has a "data" wrapper from Motia state
        if isinstance(existing_node_data, dict) and "data" in existing_node_data and len(existing_node_data) == 1:
            existing_node_data = existing_node_data.get("data", {})
        if isinstance(existing_graph_nodes, dict) and "data" in existing_graph_nodes:
            existing_graph_nodes = existing_graph_nodes.get("data", [])
        if isinstance(existing_edges, dict) and "data" in existing_edges:
            existing_edges = existing_edges.get("data", [])
        if isinstance(existing_embeddings, dict) and "data" in existing_embeddings:
            existing_embeddings = existing_embeddings.get("data", {})
        
        # Clear and restore graph service state (it's a global singleton)
        # This ensures clean state for each request
        import networkx as nx
        graph_service.graph = nx.Graph()
        graph_service.node_data = {}
        
        # Restore existing graph to graph_service
        if existing_node_data:
            graph_service.node_data = existing_node_data.copy()
            # Rebuild networkx graph from stored nodes with their attributes
            for node_id in existing_graph_nodes:
                node_info = existing_node_data.get(node_id, {})
                if isinstance(node_info, dict):
                    graph_service.graph.add_node(
                        node_id,
                        name=node_info.get("name", "Unknown"),
                        description=node_info.get("description", ""),
                        type=node_info.get("type", "concept"),
                        cluster_id=node_info.get("cluster_id", "")
                    )
            for edge in existing_edges:
                if edge.get("source") and edge.get("target"):
                    # Preserve edge type if available
                    edge_type = edge.get("type", "cluster")
                    graph_service.graph.add_edge(
                        edge["source"], 
                        edge["target"], 
                        weight=edge.get("weight", 1.0),
                        type=edge_type
                    )
            context.logger.info("Restored existing graph state", {
                "existing_nodes": len(existing_graph_nodes),
                "existing_edges": len(existing_edges),
                "node_data_keys": list(graph_service.node_data.keys())[:5]
            })
        
        # 6. Cluster concepts by similarity
        clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        context.logger.info("Clustered concepts", {"cluster_count": len(clusters)})
        
        # 7. Build graph from clusters and concepts with KNN edges
        # Use merge=True if this is a follow-up query (previousQuery exists)
        should_merge = previous_query is not None and len(existing_graph_nodes) > 0
        graph = graph_service.build_graph(clusters, concepts, embeddings=embeddings, k=2, merge=should_merge)
        context.logger.info("Built graph", {
            "node_count": len(graph["nodes"]), 
            "edge_count": len(graph["edges"]),
            "merged": should_merge
        })
        
        # 7a. Connect new nodes to existing nodes if this is a follow-up query
        cross_query_edges = []
        if should_merge and existing_embeddings and len(embeddings) > 0:
            # Create mapping of new concept IDs to their embeddings
            new_embeddings_dict = {}
            for idx, concept in enumerate(concepts):
                concept_id = concept.get("id")
                if concept_id and idx < len(embeddings):
                    new_embeddings_dict[concept_id] = embeddings[idx]
            
            # Get list of new node IDs (concepts from current query)
            new_node_ids = [c.get("id") for c in concepts if c.get("id")]
            
            if new_node_ids and new_embeddings_dict:
                context.logger.info("Connecting cross-query nodes", {
                    "new_nodes": len(new_node_ids),
                    "existing_nodes": len(existing_embeddings)
                })
                cross_query_edges = graph_service.connect_cross_query_nodes(
                    new_node_ids,
                    new_embeddings_dict,
                    existing_embeddings,
                    similarity_threshold=0.6,
                    max_connections_per_node=3
                )
                context.logger.info("Created cross-query edges", {"edge_count": len(cross_query_edges)})
                
                # Add cross-query edges to the graph response
                graph["edges"].extend(cross_query_edges)
        
        # 8. Store updated graph data in Motia state for persistence across requests
        node_ids_list = list(graph_service.graph.nodes())
        # Store edges for persistence
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": edge_data.get("type", "cluster"),  # Preserve actual edge type (knn, cluster, cross-query, expanded)
                "visual_type": "smoothstep",  # React Flow visual type
                "weight": edge_data.get("weight", 1.0)
            })
        
        # Store embeddings for new concepts (merge with existing)
        updated_embeddings = existing_embeddings.copy() if existing_embeddings else {}
        for idx, concept in enumerate(concepts):
            concept_id = concept.get("id")
            if concept_id and idx < len(embeddings):
                # Convert numpy array to list if needed
                embedding = embeddings[idx]
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                updated_embeddings[concept_id] = embedding
        
        context.logger.info("Storing graph state", {
            "node_data_keys_count": len(graph_service.node_data),
            "node_data_keys_sample": list(graph_service.node_data.keys())[:5],
            "graph_nodes_count": len(node_ids_list),
            "graph_nodes_sample": node_ids_list[:5],
            "edges_count": len(edges_list),
            "embeddings_count": len(updated_embeddings)
        })
        
        await context.state.set("knowledge_graph", "node_data", graph_service.node_data)
        await context.state.set("knowledge_graph", "graph_nodes", node_ids_list)
        await context.state.set("knowledge_graph", "graph_edges", edges_list)
        await context.state.set("knowledge_graph", "embeddings", updated_embeddings)
        
        return {
            "status": 200,
            "body": {
                "answer": answer,
                "graph": graph,
                "clusters": clusters
            }
        }
    except Exception as e:
        context.logger.error("Error processing chat request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

