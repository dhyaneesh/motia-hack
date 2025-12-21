"""Shopping mode API endpoint for product search and visualization."""
from pydantic import BaseModel
from typing import List, Dict, Optional
from src.utils.state_keys import StateKeys
import uuid
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class ShoppingRequest(BaseModel):
    query: str
    num_results: int = 10

class ShoppingResponse(BaseModel):
    requestId: str
    status: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ShoppingAPI",
    "type": "api",
    "path": "/api/shopping",
    "method": "POST",
    "description": "Search for products and return an interactive product graph visualization with images, prices, ratings, and specifications.",
    "emits": ["search-products"],
    "flows": ["shopping-flow"],
    "middleware": [create_timing_middleware("ShoppingAPI")],
    "bodySchema": ShoppingRequest.model_json_schema(),
    "responseSchema": {
        200: ShoppingResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        body = req.get("body", {})
        query = body.get("query", "")
        num_results = body.get("num_results", 10)
        
        if not query:
            return {
                "status": 400,
                "body": {"error": "Query is required"}
            }
        
        context.logger.info("Processing shopping query", {"query": query, "num_results": num_results})
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store initial request data in state
        data_group_id, data_key = StateKeys.request_data(request_id)
        await context.state.set(data_group_id, data_key, {
            "query": query,
            "num_results": num_results,
            "mode": "shopping"
        })
        
        # Store initial status
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "processing",
            "stage": "initialized"
        })
        
        # Emit search-products event
        await context.emit({
            "topic": "search-products",
            "data": {
                "request_id": request_id,
                "query": query,
                "num_results": num_results
            }
        })
        
        context.logger.info("Emitted search-products event", {"request_id": request_id})
        
        return {
            "status": 200,
            "body": {
                "requestId": request_id,
                "status": "processing"
            }
        }
    except Exception as e:
        context.logger.error("Error processing shopping request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
