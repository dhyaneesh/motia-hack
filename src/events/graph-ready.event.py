"""Event step that marks graph as ready and updates status to completed."""
from pydantic import BaseModel
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

class GraphReadyInput(BaseModel):
    request_id: str
    mode: str = "default"

config = {
    "name": "GraphReady",
    "type": "event",
    "description": "Mark graph as ready and update request status to completed",
    "subscribes": ["graph-ready"],
    "emits": [],
    "flows": ["knowledge-graph-flow", "study-flow", "shopping-flow"],
    "input": GraphReadyInput.model_json_schema()
}

@with_timing("GraphReady")
async def handler(input_data, context):
    """Update request status to completed when graph is ready."""
    try:
        # Parse input
        data = GraphReadyInput(**input_data)
        
        context.logger.info("Graph ready", {
            "request_id": data.request_id,
            "mode": data.mode
        })
        
        # Update status to completed
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "completed",
            "stage": "graph_ready"
        })
        
        context.logger.info("Status updated to completed", {
            "request_id": data.request_id
        })
        
    except Exception as e:
        context.logger.error("Error updating graph ready status", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "graph_ready"
        })

