"""Event step for connecting new nodes to existing nodes across queries."""
from pydantic import BaseModel
from src.services.graph_service import graph_service
from src.utils.state_keys import StateKeys
import networkx as nx
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

class ConnectCrossQueryInput(BaseModel):
    request_id: str
    mode: str = "default"

config = {
    "name": "ConnectCrossQuery",
    "type": "event",
    "description": "Connect new nodes to existing nodes based on embedding similarity",
    "subscribes": ["connect-cross-query"],
    "emits": ["graph-ready"],
    "flows": ["knowledge-graph-flow"],
    "input": ConnectCrossQueryInput.model_json_schema()
}

@with_timing("ConnectCrossQuery")
async def handler(input_data, context):
    """Connect new nodes to existing nodes, update graph, emit graph-ready."""
    try:
        # Parse input
        data = ConnectCrossQueryInput(**input_data)
        
        context.logger.info("Connecting cross-query nodes", {
            "request_id": data.request_id,
            "mode": data.mode
        })
        
        # Fetch concepts and embeddings from state
        group_id, key = StateKeys.concepts(data.request_id)
        concepts = await context.state.get(group_id, key)
        
        if isinstance(concepts, dict) and "data" in concepts:
            concepts = concepts.get("data", [])
        
        emb_group_id, emb_key = StateKeys.embeddings(data.request_id)
        embeddings = await context.state.get(emb_group_id, emb_key)
        
        if isinstance(embeddings, dict) and "data" in embeddings:
            embeddings = embeddings.get("data", [])
        
        # Get existing embeddings from state
        flow_type = "knowledge_graph" if data.mode == "default" else f"{data.mode}_graph"
        existing_embeddings = await context.state.get(*StateKeys.existing_embeddings(flow_type)) or {}
        
        if isinstance(existing_embeddings, dict) and "data" in existing_embeddings:
            existing_embeddings = existing_embeddings.get("data", {})
        
        # Create mapping of new concept IDs to their embeddings
        new_embeddings_dict = {}
        for idx, concept in enumerate(concepts):
            concept_id = concept.get("id")
            if concept_id and idx < len(embeddings):
                embedding = embeddings[idx]
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                new_embeddings_dict[concept_id] = embedding
        
        # Get list of new node IDs
        new_node_ids = [c.get("id") for c in concepts if c.get("id")]
        
        if new_node_ids and new_embeddings_dict and existing_embeddings:
            # Connect cross-query nodes
            cross_query_edges = graph_service.connect_cross_query_nodes(
                new_node_ids,
                new_embeddings_dict,
                existing_embeddings,
                similarity_threshold=0.6,
                max_connections_per_node=3
            )
            
            context.logger.info("Created cross-query edges", {
                "request_id": data.request_id,
                "edge_count": len(cross_query_edges)
            })
            
            # Update graph in state with new edges
            graph_group_id, graph_key = StateKeys.graph(data.request_id)
            graph = await context.state.get(graph_group_id, graph_key)
            
            if isinstance(graph, dict) and "data" in graph:
                graph = graph.get("data", {})
            
            if graph and isinstance(graph, dict):
                # Add new edges to graph
                if "edges" in graph:
                    graph["edges"].extend(cross_query_edges)
                else:
                    graph["edges"] = cross_query_edges
                
                # Store updated graph
                await context.state.set(graph_group_id, graph_key, graph)
            
            # Update stored edges in persistent state
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
            
            await context.state.set(*StateKeys.existing_graph_edges(flow_type), edges_list)
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "completed",
            "cross_query_edges": len(cross_query_edges) if new_node_ids and new_embeddings_dict and existing_embeddings else 0
        })
        
        # Emit graph-ready
        await context.emit({
            "topic": "graph-ready",
            "data": {
                "request_id": data.request_id,
                "mode": data.mode
            }
        })
        
    except Exception as e:
        context.logger.error("Error connecting cross-query nodes", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "connect_cross_query"
        })
        raise

