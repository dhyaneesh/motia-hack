from src.services.graph_service import graph_service

config = {
    "name": "GetNodeDetails",
    "type": "api",
    "path": "/api/nodes/:nodeId",
    "method": "GET",
    "description": "Get detailed information about a node for sidebar display",
    "emits": [],
    "flows": ["knowledge-graph-flow"]
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
        
        # Retrieve node from graph service
        node = graph_service.get_node(node_id)
        
        if not node:
            return {
                "status": 404,
                "body": {"error": "Node not found"}
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

