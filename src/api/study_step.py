"""Study mode API endpoint for concept learning with hierarchy and learning paths."""
from pydantic import BaseModel
from typing import List, Dict
from src.services import llm_service
from src.utils.state_keys import StateKeys
import uuid
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class StudyRequest(BaseModel):
    question: str

class StudyResponse(BaseModel):
    requestId: str
    answer: str
    status: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "StudyAPI",
    "type": "api",
    "path": "/api/study",
    "method": "POST",
    "description": "Process a study question and return concepts organized by hierarchy levels with learning paths.",
    "emits": ["extract-concepts"],
    "flows": ["study-flow"],
    "middleware": [create_timing_middleware("StudyAPI")],
    "bodySchema": StudyRequest.model_json_schema(),
    "responseSchema": {
        200: StudyResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        body = req.get("body", {})
        question = body.get("question", "")
        
        if not question:
            return {
                "status": 400,
                "body": {"error": "Question is required"}
            }
        
        context.logger.info("Processing study question", {"question": question})
        
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
            "mode": "study"
        })
        
        # Store initial status
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "processing",
            "stage": "initialized"
        })
        
        # Emit extract-concepts event (will route to assign-levels for study mode)
        await context.emit({
            "topic": "extract-concepts",
            "data": {
                "request_id": request_id,
                "question": question,
                "answer": answer,
                "max_concepts": 10,
                "mode": "study"
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
        context.logger.error("Error processing study request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
