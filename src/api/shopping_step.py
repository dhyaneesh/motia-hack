"""Shopping mode API endpoint for product search and visualization."""
from pydantic import BaseModel
from typing import List, Dict, Optional
from src.utils.state_keys import StateKeys
from src.services.image_service import process_image_search
import uuid
import base64
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class ShoppingRequest(BaseModel):
    query: str = ""  # Can be empty if image is provided
    num_results: int = 10
    # Note: image is handled separately to avoid ENAMETOOLONG errors on Windows
    # It's extracted from body directly, not via schema validation

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
    "emits": ["parse-shopping-query"],
    "flows": ["shopping-flow"],
    "middleware": [create_timing_middleware("ShoppingAPI")],
    # Note: bodySchema excludes 'image' field to prevent ENAMETOOLONG errors
    # Image is extracted directly from body in handler
    "bodySchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "default": ""},
            "num_results": {"type": "integer", "default": 10}
        },
        "required": []
    },
    "responseSchema": {
        200: ShoppingResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        # Get raw body to extract image before schema validation
        # This prevents ENAMETOOLONG errors on Windows when base64 image is in schema
        raw_body = req.get("body", {})
        
        # Extract image first (before schema validation)
        image = raw_body.get("image")  # base64 encoded image
        
        # Process image if provided (do this early to convert to query)
        query = ""
        if image:
            try:
                # Decode and process image immediately
                image_bytes = base64.b64decode(image)
                image_result = await process_image_search(image_bytes, "shopping")
                if image_result.get("search_query"):
                    query = image_result["search_query"]
                    context.logger.info("Processed image search", {
                        "extracted_query": query,
                        "has_image": True,
                        "image_size_bytes": len(image_bytes)
                    })
            except Exception as e:
                context.logger.warn("Image processing failed, using original query", {"error": str(e)})
        
        # Now get other fields (image already processed, so we can validate rest)
        query = query or raw_body.get("query", "")
        num_results = raw_body.get("num_results", 10)
        
        if not query:
            return {
                "status": 400,
                "body": {"error": "Query or image is required"}
            }
        
        context.logger.info("Processing shopping query", {
            "query": query,
            "num_results": num_results,
            "has_image": image is not None
        })
        
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
        
        # Emit parse-shopping-query event (will parse query using LLM and then search)
        await context.emit({
            "topic": "parse-shopping-query",
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
