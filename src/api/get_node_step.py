from pydantic import BaseModel
from typing import List, Dict, Any
from src.services.graph_service import graph_service
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Response schemas
class NodeDetailsResponse(BaseModel):
    id: str
    name: str
    description: str
    type: str
    clusterId: str
    references: List[Dict[str, Any]]
    relatedNodes: List[Dict[str, Any]]

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "GetNodeDetails",
    "type": "api",
    "path": "/api/nodes/:nodeId",
    "method": "GET",
    "description": "Retrieve detailed information about a specific knowledge graph node including its metadata, references, and related nodes. Used for displaying node details in the sidebar.",
    "emits": [],
    "flows": ["knowledge-graph-flow"],
    "middleware": [create_timing_middleware("GetNodeDetails")],
    "responseSchema": {
        200: NodeDetailsResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        404: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        path_params = req.get("pathParams", {})
        node_id = path_params.get("nodeId")
        if not node_id:
            return {
                "status": 400,
                "body": {"error": "Node ID is required"}
            }
        
        context.logger.info("Fetching node details", {"node_id": node_id})
        
        # Load graph data from Motia state (persists across requests)
        node_data = await context.state.get("knowledge_graph", "node_data")
        graph_nodes = await context.state.get("knowledge_graph", "graph_nodes")
        
        context.logger.info("Raw state data", {
            "node_data_type": type(node_data).__name__,
            "node_data_is_none": node_data is None,
            "graph_nodes_type": type(graph_nodes).__name__,
            "graph_nodes_is_none": graph_nodes is None,
            "node_data_keys_sample": list(node_data.keys())[:5] if isinstance(node_data, dict) else None,
            "graph_nodes_sample": graph_nodes[:5] if isinstance(graph_nodes, list) else None
        })
        
        # Unwrap node_data if it has a "data" wrapper from Motia state
        if isinstance(node_data, dict) and "data" in node_data and len(node_data) == 1:
            node_data = node_data.get("data", {})
            context.logger.info("Unwrapped node_data from 'data' key", {
                "unwrapped_keys_sample": list(node_data.keys())[:5] if isinstance(node_data, dict) else None
            })
        
        # Unwrap graph_nodes if it has a "data" wrapper
        if isinstance(graph_nodes, dict) and "data" in graph_nodes:
            graph_nodes = graph_nodes.get("data", [])
            context.logger.info("Unwrapped graph_nodes from 'data' key")
        
        if not node_data or not isinstance(node_data, dict):
            node_data = {}
        if not graph_nodes or not isinstance(graph_nodes, list):
            graph_nodes = []
        
        # Restore graph service state from Motia state
        graph_service.node_data = node_data or {}
        
        # Rebuild graph structure for related nodes lookup
        import networkx as nx
        graph_service.graph = nx.Graph()
        
        # Use graph_nodes list if available, otherwise use node_data keys
        node_ids_to_process = graph_nodes if graph_nodes else list(node_data.keys())
        
        for node_id_in_graph in node_ids_to_process:
            # Skip if not a string (defensive check)
            if not isinstance(node_id_in_graph, str):
                continue
                
            if node_id_in_graph in node_data:
                node_info = node_data.get(node_id_in_graph)
                if node_info is None or not isinstance(node_info, dict):
                    continue
                graph_service.graph.add_node(
                    node_id_in_graph,
                    name=node_info.get("name", "Unknown"),
                    description=node_info.get("description", ""),
                    type=node_info.get("type", "concept"),
                    cluster_id=node_info.get("cluster_id", "")
                )
        
        # Try to restore edges from state first
        stored_edges = await context.state.get("knowledge_graph", "graph_edges")
        if isinstance(stored_edges, dict) and "data" in stored_edges:
            stored_edges = stored_edges.get("data", [])
        
        edges_restored = False
        if isinstance(stored_edges, list) and stored_edges:
            # Restore edges from stored state
            for edge in stored_edges:
                if isinstance(edge, dict):
                    source = edge.get("source")
                    target = edge.get("target")
                    if source and target and graph_service.graph.has_node(source) and graph_service.graph.has_node(target):
                        weight = edge.get("weight", 0.8)
                        edge_type = edge.get("type", "cluster")
                        graph_service.graph.add_edge(source, target, weight=weight, type=edge_type)
                        edges_restored = True
        
        # If edges weren't restored, rebuild them from clusters
        if not edges_restored:
            cluster_nodes = {}
            if node_data and isinstance(node_data, dict):
                for nid, data in node_data.items():
                    if data is None or not isinstance(data, dict):
                        continue
                    cluster_id = data.get("cluster_id", "")
                    if cluster_id not in cluster_nodes:
                        cluster_nodes[cluster_id] = []
                    cluster_nodes[cluster_id].append(nid)
            
            for cluster_id, node_ids in cluster_nodes.items():
                for i, nid1 in enumerate(node_ids):
                    for nid2 in node_ids[i+1:]:
                        if graph_service.graph.has_node(nid1) and graph_service.graph.has_node(nid2):
                            graph_service.graph.add_edge(nid1, nid2, weight=0.8, type="cluster")
        
        # Debug: Log available node IDs
        available_ids = list(graph_service.node_data.keys())[:10]  # First 10 for debugging
        context.logger.info("Available node IDs (sample)", {
            "sample_ids": available_ids, 
            "total_nodes": len(graph_service.node_data),
            "graph_nodes_count": len(graph_nodes),
            "graph_rebuilt_nodes": len(graph_service.graph.nodes())
        })
        
        # Retrieve node from graph service
        node = graph_service.get_node(node_id)
        
        if not node:
            # Fallback: try to find node directly in node_data
            if node_id in node_data:
                node_info = node_data[node_id]
                if isinstance(node_info, dict):
                    node = {
                        "id": node_id,
                        "name": node_info.get("name", "Unknown"),
                        "description": node_info.get("description", ""),
                        "type": node_info.get("type", "concept"),
                        "cluster_id": node_info.get("cluster_id", ""),
                        "references": node_info.get("references", [])
                    }
                    # Add to graph service for future lookups
                    graph_service.node_data[node_id] = node_info
                    if not graph_service.graph.has_node(node_id):
                        graph_service.graph.add_node(
                            node_id,
                            name=node_info.get("name", "Unknown"),
                            description=node_info.get("description", ""),
                            type=node_info.get("type", "concept"),
                            cluster_id=node_info.get("cluster_id", "")
                        )
        
        if not node:
            context.logger.info("Node not found in graph service", {
                "requested_id": node_id,
                "available_count": len(graph_service.node_data),
                "available_ids_sample": list(graph_service.node_data.keys())[:10]
            })
            return {
                "status": 404,
                "body": {"error": f"Node not found: {node_id}"}
            }
        
        # Get related nodes
        related_nodes = graph_service.get_related_nodes(node_id)
        
        return {
            "status": 200,
            "body": {
                "id": node_id,
                "name": node["name"],
                "description": node["description"],
                "type": node["type"],
                "clusterId": node["cluster_id"],
                "references": node["references"],
                "relatedNodes": related_nodes
            }
        }
    except Exception as e:
        context.logger.error("Error fetching node details", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

