import os
from pydantic import BaseModel
from typing import Optional
from src.services import llm_service
from src.services.mode_service import detect_mode
from src.services.image_service import process_image_search
from src.utils.state_keys import StateKeys
import base64
import uuid
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class ChatRequest(BaseModel):
    question: str
    context: dict = {}
    mode: str = "default"  # 'default', 'shopping', 'study', or 'auto'
    image: Optional[str] = None  # base64 encoded image for multi-modal search
    previousQuery: Optional[str] = None  # Previous query for context-aware graph merging

class ChatResponse(BaseModel):
    requestId: str
    answer: str
    status: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ChatAPI",
    "type": "api",
    "path": "/api/chat",
    "method": "POST",
    "description": "Process a question using AI and return an answer with an interactive knowledge graph visualization. Extracts concepts, generates embeddings, clusters related concepts, and builds a graph structure.",
    "emits": ["extract-concepts"],
    "flows": ["knowledge-graph-flow"],
    "middleware": [create_timing_middleware("ChatAPI")],
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
        previous_query = body.get("previousQuery")
        
        if not question and not image:
            return {
                "status": 400,
                "body": {"error": "Question or image is required"}
            }
        
        # Auto-detect mode if 'auto' or process mode
        if mode == "auto" or not mode:
            mode = detect_mode(question) if question else "default"
        
        context.logger.info("Processing chat request", {
            "question": question[:100] if question else None,
            "mode": mode,
            "has_image": image is not None
        })
        
        # Process image if provided
        if image:
            try:
                image_bytes = base64.b64decode(image)
                image_result = await process_image_search(image_bytes, mode)
                if image_result.get("search_query"):
                    question = image_result["search_query"]
                    context.logger.info("Processed image search", {"extracted_query": question})
            except Exception as e:
                context.logger.info("Image processing failed", {"error": str(e)})
        
        # Generate answer using Gemini (keep in API for immediate response)
        answer = await llm_service.generate_answer(question)
        context.logger.info("Generated answer", {"answer_length": len(answer)})
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store initial request data in state
        data_group_id, data_key = StateKeys.request_data(request_id)
        await context.state.set(data_group_id, data_key, {
            "question": question,
            "answer": answer,
            "mode": mode,
            "previous_query": previous_query
        })
        
        # Store initial status
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "processing",
            "stage": "initialized"
        })
        
        # Emit extract-concepts event to start the processing pipeline
        await context.emit({
            "topic": "extract-concepts",
            "data": {
                "request_id": request_id,
                "question": question,
                "answer": answer,
                "max_concepts": 10,
                "mode": mode
            }
        })
        
        context.logger.info("Emitted extract-concepts event", {"request_id": request_id})
        
        return {
            "status": 200,
            "body": {
                "requestId": request_id,
                "answer": answer,
                "status": "processing"
            }
        }
    except Exception as e:
        context.logger.error("Error processing chat request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

