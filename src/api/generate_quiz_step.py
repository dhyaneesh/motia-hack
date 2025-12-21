"""API endpoint to generate quiz questions on-demand for study mode."""
from pydantic import BaseModel
from typing import List, Dict
from src.services.quiz_service import generate_quiz
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class GenerateQuizRequest(BaseModel):
    request_id: str
    num_questions: int = 5

class QuizQuestion(BaseModel):
    type: str
    question: str
    options: List[str] = []
    correct_answer: str
    explanation: str
    concept_id: str

class GenerateQuizResponse(BaseModel):
    requestId: str
    questions: List[Dict]
    status: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "GenerateQuizAPI",
    "type": "api",
    "path": "/api/study/generate-quiz",
    "method": "POST",
    "description": "Generate quiz questions from study mode concepts. Requires learning path to be built first.",
    "emits": [],
    "flows": ["study-flow"],
    "middleware": [create_timing_middleware("GenerateQuizAPI")],
    "bodySchema": GenerateQuizRequest.model_json_schema(),
    "responseSchema": {
        200: GenerateQuizResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    """Generate quiz questions from concepts."""
    try:
        body = req.get("body", {})
        request_id = body.get("request_id")
        num_questions = body.get("num_questions", 5)
        
        if not request_id:
            return {
                "status": 400,
                "body": {"error": "Request ID is required"}
            }
        
        context.logger.info("Generating quiz", {"request_id": request_id, "num_questions": num_questions})
        
        # Fetch concepts from state
        group_id, key = StateKeys.concepts(request_id)
        concepts = await context.state.get(group_id, key)
        
        if not concepts:
            return {
                "status": 400,
                "body": {"error": "No concepts found. Please complete a study query first."}
            }
        
        # Unwrap if needed
        if isinstance(concepts, dict) and "data" in concepts:
            concepts = concepts.get("data", [])
        
        # Check if learning path is built (concepts should have levels AND learning_path_position)
        # The learning_path_position is the definitive indicator that learning path was built
        concepts_with_path = [c for c in concepts if c.get("learning_path_position") is not None]
        
        if not concepts_with_path:
            return {
                "status": 400,
                "body": {"error": "Learning path must be built first. Please click 'Build Learning Path' button to assign levels and build the path."}
            }
        
        # Use concepts with learning path for quiz generation
        # Generate quiz questions
        questions = await generate_quiz(concepts_with_path, num_questions)
        
        context.logger.info("Generated quiz questions", {
            "request_id": request_id,
            "question_count": len(questions)
        })
        
        return {
            "status": 200,
            "body": {
                "requestId": request_id,
                "questions": questions,
                "status": "completed"
            }
        }
    except Exception as e:
        context.logger.error("Error generating quiz", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
