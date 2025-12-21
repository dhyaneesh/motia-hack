"""Event step for extracting concepts from question and answer using LLM."""
import json
from pydantic import BaseModel
from typing import Optional
from src.services import llm_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class ExtractConceptsInput(BaseModel):
    request_id: str
    question: str
    answer: str
    max_concepts: int = 10
    mode: str = "default"  # 'default', 'study', 'shopping'

config = {
    "name": "ExtractConcepts",
    "type": "event",
    "description": "Extract key concepts from question and answer using LLM",
    "subscribes": ["extract-concepts"],
    "emits": [
        {"topic": "search-references", "conditional": True},  # For knowledge-graph and study flows
        {"topic": "assign-levels", "conditional": True}  # For study flow
    ],
    "flows": ["knowledge-graph-flow", "study-flow"],
    "input": ExtractConceptsInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 3,
            "timeout": 30,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Extract concepts from question and answer, store in state, emit next events."""
    try:
        # Parse input
        data = ExtractConceptsInput(**input_data)
        
        context.logger.info("Extracting concepts", {
            "request_id": data.request_id,
            "mode": data.mode,
            "max_concepts": data.max_concepts
        })
        
        # Extract concepts using LLM
        concepts = await llm_service.extract_concepts(
            data.question,
            data.answer,
            max_concepts=data.max_concepts
        )
        
        context.logger.info("Extracted concepts", {
            "request_id": data.request_id,
            "concept_count": len(concepts)
        })
        
        # Store concepts in state
        group_id, key = StateKeys.concepts(data.request_id)
        await context.state.set(group_id, key, concepts)
        
        # Update request status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "concepts_extracted",
            "concept_count": len(concepts)
        })
        
        # Emit next events based on mode
        if data.mode in ["default", "auto"]:
            # Knowledge graph flow: search for references
            await context.emit({
                "topic": "search-references",
                "data": {
                    "request_id": data.request_id,
                    "mode": data.mode
                }
            })
        elif data.mode == "study":
            # Study flow: assign levels first
            await context.emit({
                "topic": "assign-levels",
                "data": {
                    "request_id": data.request_id
                }
            })
        
        context.logger.info("Concepts extraction completed", {
            "request_id": data.request_id,
            "concepts_extracted": len(concepts)
        })
        
    except Exception as e:
        context.logger.error("Error extracting concepts", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "extract_concepts"
        })
        raise

