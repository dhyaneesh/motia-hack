"""API endpoint to build learning path on-demand for study mode."""
from pydantic import BaseModel
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class BuildLearningPathRequest(BaseModel):
    request_id: str

class BuildLearningPathResponse(BaseModel):
    requestId: str
    status: str
    message: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "BuildLearningPathAPI",
    "type": "api",
    "path": "/api/study/build-learning-path",
    "method": "POST",
    "description": "Build learning path on-demand for study mode. Assigns levels to concepts and builds optimal learning sequence.",
    "emits": ["assign-levels"],
    "flows": ["study-flow"],
    "middleware": [create_timing_middleware("BuildLearningPathAPI")],
    "bodySchema": BuildLearningPathRequest.model_json_schema(),
    "responseSchema": {
        200: BuildLearningPathResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    """Trigger learning path building on-demand."""
    try:
        body = req.get("body", {})
        request_id = body.get("request_id")
        
        if not request_id:
            return {
                "status": 400,
                "body": {"error": "Request ID is required"}
            }
        
        context.logger.info("Building learning path on-demand", {"request_id": request_id})
        
        # Check if graph already exists
        graph_group_id, graph_key = StateKeys.graph(request_id)
        existing_graph = await context.state.get(graph_group_id, graph_key)
        
        if not existing_graph:
            return {
                "status": 400,
                "body": {"error": "Graph must be built first. Please wait for initial graph to complete."}
            }
        
        # Emit assign-levels event (will chain to build-learning-path, then update graph)
        await context.emit({
            "topic": "assign-levels",
            "data": {
                "request_id": request_id
            }
        })
        
        context.logger.info("Emitted assign-levels event for on-demand learning path", {"request_id": request_id})
        
        return {
            "status": 200,
            "body": {
                "requestId": request_id,
                "status": "processing",
                "message": "Building learning path..."
            }
        }
    except Exception as e:
        context.logger.error("Error building learning path on-demand", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
