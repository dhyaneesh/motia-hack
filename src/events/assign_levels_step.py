"""Event step for assigning difficulty levels to concepts."""
from pydantic import BaseModel
from src.services.study_service import assign_concept_level
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class AssignLevelsInput(BaseModel):
    request_id: str

config = {
    "name": "AssignLevels",
    "type": "event",
    "description": "Assign difficulty levels (beginner/intermediate/advanced) to concepts",
    "subscribes": ["assign-levels"],
    "emits": ["build-learning-path"],
    "flows": ["study-flow"],
    "input": AssignLevelsInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 2,
            "timeout": 60,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Assign levels to concepts, store in state, emit next event."""
    try:
        # Parse input
        data = AssignLevelsInput(**input_data)
        
        context.logger.info("Assigning concept levels", {
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
        
        # Assign levels to each concept
        for concept in concepts:
            try:
                level = await assign_concept_level(concept)
                concept["level"] = level
            except Exception as e:
                context.logger.info(f"Failed to assign level for {concept.get('name')}", {
                    "error": str(e),
                    "concept_id": concept.get("id")
                })
                concept["level"] = 2  # Default to intermediate
        
        # Store updated concepts
        await context.state.set(group_id, key, concepts)
        
        context.logger.info("Assigned concept levels", {
            "request_id": data.request_id,
            "beginner": sum(1 for c in concepts if c.get("level") == 1),
            "intermediate": sum(1 for c in concepts if c.get("level") == 2),
            "advanced": sum(1 for c in concepts if c.get("level") == 3)
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "levels_assigned",
            "concept_count": len(concepts)
        })
        
        # Emit next event
        await context.emit({
            "topic": "build-learning-path",
            "data": {
                "request_id": data.request_id
            }
        })
        
    except Exception as e:
        context.logger.error("Error assigning levels", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "assign_levels"
        })
        raise

