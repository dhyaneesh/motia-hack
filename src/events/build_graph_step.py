"""Event step for building knowledge graph from clusters and concepts."""
from pydantic import BaseModel
from typing import Optional
from src.services.graph_service import graph_service
from src.utils.state_keys import StateKeys
import networkx as nx
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class BuildGraphInput(BaseModel):
    request_id: str
    mode: str = "default"  # 'default', 'study', 'shopping'
    previous_query: Optional[str] = None  # For context-aware merging

config = {
    "name": "BuildGraph",
    "type": "event",
    "description": "Build knowledge graph from clusters and concepts",
    "subscribes": ["build-graph"],
    "emits": [
        {"topic": "connect-cross-query", "conditional": True},
        {"topic": "graph-ready", "label": "Graph Complete"}
    ],
    "flows": ["knowledge-graph-flow", "study-flow", "shopping-flow"],
    "input": BuildGraphInput.model_json_schema()
}

async def handler(input_data, context):
    """Build graph from clusters and concepts, store in state, emit next events."""
    try:
        # Parse input
        data = BuildGraphInput(**input_data)
        
        # Fetch request data to get previous_query
        request_data_group_id, request_data_key = StateKeys.request_data(data.request_id)
        request_data = await context.state.get(request_data_group_id, request_data_key)
        
        if isinstance(request_data, dict) and "data" in request_data:
            request_data = request_data.get("data", {})
        
        previous_query = request_data.get("previous_query") if isinstance(request_data, dict) else None
        
        context.logger.info("Building graph", {
            "request_id": data.request_id,
            "mode": data.mode,
            "has_previous_query": previous_query is not None
        })
        
        # Fetch clusters, concepts, and embeddings from state
        cluster_group_id, cluster_key = StateKeys.clusters(data.request_id)
        clusters = await context.state.get(cluster_group_id, cluster_key)
        
        if isinstance(clusters, dict) and "data" in clusters:
            clusters = clusters.get("data", [])
        
        group_id, key = StateKeys.concepts(data.request_id)
        concepts = await context.state.get(group_id, key)
        
        if isinstance(concepts, dict) and "data" in concepts:
            concepts = concepts.get("data", [])
        
        emb_group_id, emb_key = StateKeys.embeddings(data.request_id)
        embeddings = await context.state.get(emb_group_id, emb_key)
        
        if isinstance(embeddings, dict) and "data" in embeddings:
            embeddings = embeddings.get("data", [])
        
        # Load existing graph state if this is a follow-up query
        should_merge = previous_query is not None
        existing_node_data = {}
        existing_graph_nodes = []
        existing_edges = []
        existing_embeddings = {}
        
        if should_merge:
            flow_type = "knowledge_graph" if data.mode == "default" else f"{data.mode}_graph"
            existing_node_data = await context.state.get(*StateKeys.existing_graph(flow_type)) or {}
            existing_graph_nodes = await context.state.get(*StateKeys.existing_graph_nodes(flow_type)) or []
            existing_edges = await context.state.get(*StateKeys.existing_graph_edges(flow_type)) or []
            existing_embeddings = await context.state.get(*StateKeys.existing_embeddings(flow_type)) or {}
            
            # Unwrap if needed
            if isinstance(existing_node_data, dict) and "data" in existing_node_data and len(existing_node_data) == 1:
                existing_node_data = existing_node_data.get("data", {})
            if isinstance(existing_graph_nodes, dict) and "data" in existing_graph_nodes:
                existing_graph_nodes = existing_graph_nodes.get("data", [])
            if isinstance(existing_edges, dict) and "data" in existing_edges:
                existing_edges = existing_edges.get("data", [])
            if isinstance(existing_embeddings, dict) and "data" in existing_embeddings:
                existing_embeddings = existing_embeddings.get("data", {})
            
            # Restore graph service state
            graph_service.graph = nx.Graph()
            graph_service.node_data = existing_node_data.copy() if existing_node_data else {}
            
            # Rebuild networkx graph from stored nodes
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
            
            # Restore edges
            for edge in existing_edges:
                if edge.get("source") and edge.get("target"):
                    edge_type = edge.get("type", "cluster")
                    graph_service.graph.add_edge(
                        edge["source"],
                        edge["target"],
                        weight=edge.get("weight", 1.0),
                        type=edge_type
                    )
        
        # Build graph based on mode
        products = None  # Initialize for shopping mode
        if data.mode == "shopping":
            # Shopping mode: build product graph
            products = await context.state.get(*StateKeys.products(data.request_id))
            if isinstance(products, dict) and "data" in products:
                products = products.get("data", [])
            
            # Ensure products is a list
            if not isinstance(products, list):
                products = []
            
            if not products:
                context.logger.warn("No products found for shopping mode", {
                    "request_id": data.request_id
                })
            
            graph = graph_service.build_product_graph(
                clusters,
                products or [],
                embeddings=embeddings,
                k=2
            )
        elif data.mode == "study":
            # Study mode: build study graph
            graph = graph_service.build_study_graph(
                clusters,
                concepts,
                embeddings=embeddings,
                k=2
            )
        else:
            # Default knowledge graph mode
            graph = graph_service.build_graph(
                clusters,
                concepts,
                embeddings=embeddings,
                k=2,
                merge=should_merge
            )
        
        # Deduplicate highly similar nodes
        # Create embeddings dict from concepts or products based on mode
        embeddings_dict = {}
        if data.mode == "shopping":
            # Shopping mode: use products
            if products and embeddings:
                for idx, product in enumerate(products):
                    product_id = product.get("id")
                    if product_id and idx < len(embeddings):
                        embedding = embeddings[idx]
                        if hasattr(embedding, 'tolist'):
                            embedding = embedding.tolist()
                        embeddings_dict[product_id] = embedding
        else:
            # Default or study mode: use concepts
            if concepts and embeddings:
                for idx, concept in enumerate(concepts):
                    concept_id = concept.get("id")
                    if concept_id and idx < len(embeddings):
                        embedding = embeddings[idx]
                        if hasattr(embedding, 'tolist'):
                            embedding = embedding.tolist()
                        embeddings_dict[concept_id] = embedding
        
        # Merge existing embeddings for cross-query deduplication
        if existing_embeddings:
            embeddings_dict.update(existing_embeddings)
        
        # Run deduplication (0.85 threshold = 85% similarity)
        merge_map = graph_service.deduplicate_nodes(embeddings_dict, similarity_threshold=0.85)
        
        if merge_map:
            context.logger.info("Deduplicated similar nodes", {
                "request_id": data.request_id,
                "merged_count": len(merge_map),
                "merge_map_sample": dict(list(merge_map.items())[:3])
            })
            
            # Update embeddings dict to remove merged nodes
            for old_id in merge_map.keys():
                if old_id in embeddings_dict:
                    del embeddings_dict[old_id]
            
            # Rebuild graph visualization after deduplication
            if data.mode == "shopping":
                graph = graph_service._to_react_flow_format(
                    nx.spring_layout(graph_service.graph, k=2, iterations=50, seed=42),
                    node_type="productNode"
                )
            elif data.mode == "study":
                graph = graph_service._to_react_flow_format(
                    nx.spring_layout(graph_service.graph, k=2, iterations=50, seed=42),
                    node_type="conceptCard"
                )
            else:
                graph = graph_service._to_react_flow_format(
                    nx.spring_layout(graph_service.graph, k=2, iterations=50, seed=42)
                )
        
        # Store graph in state
        graph_group_id, graph_key = StateKeys.graph(data.request_id)
        await context.state.set(graph_group_id, graph_key, graph)
        
        # Store updated graph data for persistence
        node_ids_list = list(graph_service.graph.nodes())
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": edge_data.get("type", "cluster"),
                "visual_type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
            })
        
        # Store embeddings for new concepts (merge with existing, after deduplication)
        updated_embeddings = existing_embeddings.copy() if existing_embeddings else {}
        # Use deduplicated embeddings_dict
        updated_embeddings.update(embeddings_dict)
        
        # Persist graph state
        flow_type = "knowledge_graph" if data.mode == "default" else f"{data.mode}_graph"
        await context.state.set(*StateKeys.existing_graph(flow_type), graph_service.node_data)
        await context.state.set(*StateKeys.existing_graph_nodes(flow_type), node_ids_list)
        await context.state.set(*StateKeys.existing_graph_edges(flow_type), edges_list)
        await context.state.set(*StateKeys.existing_embeddings(flow_type), updated_embeddings)
        
        context.logger.info("Graph built", {
            "request_id": data.request_id,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "merged": should_merge
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "graph_built",
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"])
        })
        
        # Emit next event based on whether we need cross-query connections
        if should_merge and existing_embeddings and len(embeddings) > 0:
            # Need to connect new nodes to existing nodes
            await context.emit({
                "topic": "connect-cross-query",
                "data": {
                    "request_id": data.request_id,
                    "mode": data.mode
                }
            })
        else:
            # Graph is ready
            await context.emit({
                "topic": "graph-ready",
                "data": {
                    "request_id": data.request_id,
                    "mode": data.mode
                }
            })
        
    except Exception as e:
        context.logger.error("Error building graph", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "build_graph"
        })
        raise

