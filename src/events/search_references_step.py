"""Event step for searching references for concepts using Tavily API."""
import asyncio
from pydantic import BaseModel
from src.services import tavily_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class SearchReferencesInput(BaseModel):
    request_id: str
    mode: str = "default"

config = {
    "name": "SearchReferences",
    "type": "event",
    "description": "Search for references for each concept using Tavily API",
    "subscribes": ["search-references"],
    "emits": ["generate-embeddings"],
    "flows": ["knowledge-graph-flow", "study-flow"],
    "input": SearchReferencesInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 3,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Search for references for each concept, attach to concepts, emit next event."""
    try:
        # Parse input
        data = SearchReferencesInput(**input_data)
        
        context.logger.info("Searching references", {
            "request_id": data.request_id,
            "mode": data.mode
        })
        
        # Fetch concepts from state
        group_id, key = StateKeys.concepts(data.request_id)
        concepts = await context.state.get(group_id, key)
        
        if not concepts:
            context.logger.warn("No concepts found in state", {"request_id": data.request_id})
            # Still emit generate-embeddings with empty concepts
            await context.emit({
                "topic": "generate-embeddings",
                "data": {
                    "request_id": data.request_id,
                    "mode": data.mode
                }
            })
            return
        
        # Unwrap if needed
        if isinstance(concepts, dict) and "data" in concepts:
            concepts = concepts.get("data", [])
        
        # Parallel Tavily searches with timeout
        async def fetch_references(concept):
            """Fetch references for a single concept."""
            try:
                search_results = await tavily_service.search(
                    concept["name"],
                    num_results=2  # Reduced for faster response
                )
                return search_results
            except Exception as e:
                context.logger.info(f"Tavily search failed for {concept.get('name')}", {
                    "error": str(e),
                    "concept_id": concept.get("id")
                })
                return []
        
        # Fetch all references in parallel with timeout
        reference_tasks = [fetch_references(concept) for concept in concepts]
        try:
            reference_results = await asyncio.wait_for(
                asyncio.gather(*reference_tasks, return_exceptions=True),
                timeout=10.0  # 10 second timeout for all searches
            )
        except asyncio.TimeoutError:
            context.logger.warn("Tavily searches timed out", {"request_id": data.request_id})
            reference_results = [[] for _ in concepts]
        
        # Attach references to concepts
        for concept, references in zip(concepts, reference_results):
            if isinstance(references, Exception):
                concept["references"] = []
            else:
                concept["references"] = references
        
        # Store updated concepts
        await context.state.set(group_id, key, concepts)
        
        context.logger.info("References search completed", {
            "request_id": data.request_id,
            "concepts_with_refs": sum(1 for c in concepts if c.get("references"))
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "references_searched",
            "concept_count": len(concepts)
        })
        
        # Emit next event
        await context.emit({
            "topic": "generate-embeddings",
            "data": {
                "request_id": data.request_id,
                "mode": data.mode
            }
        })
        
    except Exception as e:
        context.logger.error("Error searching references", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "search_references"
        })
        raise

