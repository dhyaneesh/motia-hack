"""Event step for building learning path from concepts."""
from pydantic import BaseModel
from src.services.study_service import build_learning_path
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class BuildLearningPathInput(BaseModel):
    request_id: str

config = {
    "name": "BuildLearningPath",
    "type": "event",
    "description": "Build optimal learning path sequence for concepts",
    "subscribes": ["build-learning-path"],
    "emits": ["search-references"],  # Then goes to search references, embeddings, clustering, graph building
    "flows": ["study-flow"],
    "input": BuildLearningPathInput.model_json_schema()
}

async def handler(input_data, context):
    """Build learning path, store in state, emit next event."""
    try:
        # Parse input
        data = BuildLearningPathInput(**input_data)
        
        context.logger.info("Building learning path", {
            "request_id": data.request_id
        })
        
        # Fetch concepts from state
        group_id, key = StateKeys.concepts(data.request_id)
        concepts = await context.state.get(group_id, key)
        
        if not concepts:
            context.logger.warn("No concepts found in state", {"request_id": data.request_id})
            return
        
        # Unwrap if needed
        if isinstance(concepts, dict) and "data" in concepts:
            concepts = concepts.get("data", [])
        
        # Build learning path
        learning_path = await build_learning_path(concepts)
        
        # Store learning path in state
        path_group_id, path_key = StateKeys.learning_path(data.request_id)
        await context.state.set(path_group_id, path_key, learning_path)
        
        # Update concepts with learning path positions
        for concept in concepts:
            for lp_concept in learning_path:
                if concept.get("id") == lp_concept.get("id"):
                    concept["learning_path_position"] = lp_concept.get("learning_path_position")
                    break
        
        # Store updated concepts
        await context.state.set(group_id, key, concepts)
        
        context.logger.info("Built learning path", {
            "request_id": data.request_id,
            "path_length": len(learning_path)
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "learning_path_built",
            "path_length": len(learning_path)
        })
        
        # Emit next event: search references (then embeddings, clustering, graph)
        await context.emit({
            "topic": "search-references",
            "data": {
                "request_id": data.request_id,
                "mode": "study"
            }
        })
        
    except Exception as e:
        context.logger.error("Error building learning path", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "build_learning_path"
        })
        raise

