import os
from pydantic import BaseModel
from typing import Optional
from src.services import llm_service, tavily_service, embedding_service, clustering_service
from src.services.graph_service import graph_service
from src.services.mode_service import detect_mode, process_query
from src.services.image_service import process_image_search
import base64

# Request/Response schemas
class ChatRequest(BaseModel):
    question: str
    context: dict = {}
    mode: str = "default"  # 'default', 'shopping', 'study', or 'auto'
    image: Optional[str] = None  # base64 encoded image for multi-modal search

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
        
        # 2. Extract concepts from question and answer
        concepts = await llm_service.extract_concepts(question, answer)
        context.logger.info("Extracted concepts", {"concept_count": len(concepts)})
        
        # 3. Search Tavily for each concept to get references
        for concept in concepts:
            try:
                search_results = await tavily_service.search(concept["name"], num_results=3)
                concept["references"] = search_results
            except Exception as e:
                context.logger.info(f"Tavily search failed for {concept['name']}", {"error": str(e)})
                concept["references"] = []
        
        # 4. Generate embeddings for all concepts
        embedding_texts = [f"{c['name']} {c.get('description', '')}" for c in concepts]
        embeddings = await embedding_service.get_embeddings(embedding_texts)
        context.logger.info("Generated embeddings", {"embedding_count": len(embeddings)})
        
        # 5. Cluster concepts by similarity
        clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        context.logger.info("Clustered concepts", {"cluster_count": len(clusters)})
        
        # 6. Build graph from clusters and concepts
        graph = graph_service.build_graph(clusters, concepts)
        context.logger.info("Built graph", {"node_count": len(graph["nodes"]), "edge_count": len(graph["edges"])})
        
        # 7. Store graph data in Motia state for persistence across requests
        node_ids_list = list(graph_service.graph.nodes())
        # Store edges for persistence
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
            })
        
        context.logger.info("Storing graph state", {
            "node_data_keys_count": len(graph_service.node_data),
            "node_data_keys_sample": list(graph_service.node_data.keys())[:5],
            "graph_nodes_count": len(node_ids_list),
            "graph_nodes_sample": node_ids_list[:5],
            "edges_count": len(edges_list)
        })
        
        await context.state.set("knowledge_graph", "node_data", graph_service.node_data)
        await context.state.set("knowledge_graph", "graph_nodes", node_ids_list)
        await context.state.set("knowledge_graph", "graph_edges", edges_list)
        
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

