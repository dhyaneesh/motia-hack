"""Event step for generating embeddings for concepts/products."""
from pydantic import BaseModel
from typing import Optional
from src.services import embedding_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

class GenerateEmbeddingsInput(BaseModel):
    request_id: str
    mode: str = "default"  # 'default', 'study', 'shopping'

config = {
    "name": "GenerateEmbeddings",
    "type": "event",
    "description": "Generate embeddings for concepts or products using Gemini",
    "subscribes": ["generate-embeddings"],
    "emits": ["cluster-concepts"],
    "flows": ["knowledge-graph-flow", "study-flow", "shopping-flow"],
    "input": GenerateEmbeddingsInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 3,
            "timeout": 60,  # Longer timeout for batch embeddings
            "backoffRate": 2
        }
    }
}

@with_timing("GenerateEmbeddings")
async def handler(input_data, context):
    """Generate embeddings for concepts/products, store in state, emit next event."""
    try:
        # Parse input
        data = GenerateEmbeddingsInput(**input_data)
        
        context.logger.info("Generating embeddings", {
            "request_id": data.request_id,
            "mode": data.mode
        })
        
        # Fetch items from state based on mode
        if data.mode == "shopping":
            # Shopping mode: fetch products
            group_id, key = StateKeys.products(data.request_id)
            items = await context.state.get(group_id, key)
            if not items:
                context.logger.warn("No products found in state", {"request_id": data.request_id})
                return
            
            # Unwrap if needed
            if isinstance(items, dict) and "data" in items:
                items = items.get("data", [])
            
            # Generate embeddings for products
            product_texts = [
                f"{p.get('name', '')} {p.get('description', '')}"
                for p in items
            ]
            embeddings = await embedding_service.get_embeddings(product_texts)
            
            # Store embeddings
            emb_group_id, emb_key = StateKeys.embeddings(data.request_id)
            await context.state.set(emb_group_id, emb_key, embeddings)
            
        else:
            # Knowledge graph or study mode: fetch concepts
            group_id, key = StateKeys.concepts(data.request_id)
            concepts = await context.state.get(group_id, key)
            
            if not concepts:
                context.logger.warn("No concepts found in state", {"request_id": data.request_id})
                # Still emit cluster-concepts
                await context.emit({
                    "topic": "cluster-concepts",
                    "data": {
                        "request_id": data.request_id,
                        "mode": data.mode
                    }
                })
                return
            
            # Unwrap if needed
            if isinstance(concepts, dict) and "data" in concepts:
                concepts = concepts.get("data", [])
            
            # Generate embeddings for concepts
            embedding_texts = [
                f"{c['name']} {c.get('description', '')}"
                for c in concepts
            ]
            embeddings = await embedding_service.get_embeddings(embedding_texts)
            
            # Store embeddings
            emb_group_id, emb_key = StateKeys.embeddings(data.request_id)
            await context.state.set(emb_group_id, emb_key, embeddings)
        
        context.logger.info("Embeddings generated", {
            "request_id": data.request_id,
            "embedding_count": len(embeddings)
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "embeddings_generated",
            "embedding_count": len(embeddings)
        })
        
        # Emit next event
        await context.emit({
            "topic": "cluster-concepts",
            "data": {
                "request_id": data.request_id,
                "mode": data.mode
            }
        })
        
    except Exception as e:
        context.logger.error("Error generating embeddings", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "generate_embeddings"
        })
        raise

