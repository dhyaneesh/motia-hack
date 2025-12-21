"""API endpoint for polling chat request status and retrieving graph data."""
from pydantic import BaseModel
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class ChatStatusResponse(BaseModel):
    status: str  # 'processing', 'completed', 'failed'
    graph: dict = None
    clusters: list = None
    error: str = None

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ChatStatus",
    "type": "api",
    "path": "/api/chat/status/:requestId",
    "method": "GET",
    "description": "Get the status of a chat request and retrieve graph data when completed",
    "emits": [],
    "flows": ["knowledge-graph-flow"],
    "middleware": [create_timing_middleware("ChatStatus")],
    "responseSchema": {
        200: ChatStatusResponse.model_json_schema(),
        404: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    """Retrieve chat request status and graph data from state."""
    try:
        path_params = req.get("pathParams", {})
        request_id = path_params.get("requestId")
        
        if not request_id:
            return {
                "status": 400,
                "body": {"error": "Request ID is required"}
            }
        
        # Fetch status from state
        status_group, status_key = StateKeys.status(request_id)
        status_data = await context.state.get(status_group, status_key)
        
        if not status_data:
            return {
                "status": 404,
                "body": {"error": f"Request {request_id} not found"}
            }
        
        # Unwrap if needed
        if isinstance(status_data, dict) and "data" in status_data:
            status_data = status_data.get("data", {})
        
        current_status = status_data.get("status", "processing")
        
        response_body = {
            "status": current_status
        }
        
        # If completed, include graph and clusters
        if current_status == "completed":
            # Fetch graph
            graph_group_id, graph_key = StateKeys.graph(request_id)
            graph = await context.state.get(graph_group_id, graph_key)
            
            if isinstance(graph, dict) and "data" in graph:
                graph = graph.get("data", {})
            
            # Fetch clusters
            cluster_group_id, cluster_key = StateKeys.clusters(request_id)
            clusters = await context.state.get(cluster_group_id, cluster_key)
            
            if isinstance(clusters, dict) and "data" in clusters:
                clusters = clusters.get("data", [])
            
            response_body["graph"] = graph or {"nodes": [], "edges": []}
            response_body["clusters"] = clusters or []
        
        # If failed, include error
        if current_status == "failed":
            response_body["error"] = status_data.get("error", "Unknown error")
        
        return {
            "status": 200,
            "body": response_body
        }
        
    except Exception as e:
        context.logger.error("Error retrieving chat status", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

