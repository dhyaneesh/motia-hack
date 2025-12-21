"""Event step for identifying prerequisites for concepts."""
from pydantic import BaseModel
from src.services.study_service import identify_prerequisites
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class IdentifyPrerequisitesInput(BaseModel):
    request_id: str

config = {
    "name": "IdentifyPrerequisites",
    "type": "event",
    "description": "Identify prerequisite concepts for each concept",
    "subscribes": ["identify-prerequisites"],
    "emits": ["build-learning-path"],
    "flows": ["study-flow"],
    "input": IdentifyPrerequisitesInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 2,
            "timeout": 60,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Identify prerequisites for concepts, store in state, emit next event."""
    try:
        # Parse input
        data = IdentifyPrerequisitesInput(**input_data)
        
        context.logger.info("Identifying prerequisites", {
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
        
        # Identify prerequisites for each concept
        for concept in concepts:
            try:
                prerequisites = await identify_prerequisites(concept, concepts)
                concept["prerequisites"] = prerequisites
            except Exception as e:
                context.logger.info(f"Failed to identify prerequisites for {concept.get('name')}", {
                    "error": str(e),
                    "concept_id": concept.get("id")
                })
                concept["prerequisites"] = []
        
        # Store updated concepts
        await context.state.set(group_id, key, concepts)
        
        context.logger.info("Identified prerequisites", {
            "request_id": data.request_id,
            "concepts_with_prereqs": sum(1 for c in concepts if c.get("prerequisites"))
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "prerequisites_identified",
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
        context.logger.error("Error identifying prerequisites", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "identify_prerequisites"
        })
        raise

