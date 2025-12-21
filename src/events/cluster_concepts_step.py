"""Event step for clustering concepts/products by similarity."""
from pydantic import BaseModel
from src.services import clustering_service, product_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class ClusterConceptsInput(BaseModel):
    request_id: str
    mode: str = "default"  # 'default', 'study', 'shopping'

config = {
    "name": "ClusterConcepts",
    "type": "event",
    "description": "Cluster concepts or products by semantic similarity using HDBSCAN",
    "subscribes": ["cluster-concepts"],
    "emits": ["build-graph"],
    "flows": ["knowledge-graph-flow", "study-flow", "shopping-flow"],
    "input": ClusterConceptsInput.model_json_schema()
}

async def handler(input_data, context):
    """Cluster concepts/products, store clusters, emit next event."""
    try:
        # Parse input
        data = ClusterConceptsInput(**input_data)
        
        context.logger.info("Clustering concepts", {
            "request_id": data.request_id,
            "mode": data.mode
        })
        
        # Fetch embeddings from state
        emb_group_id, emb_key = StateKeys.embeddings(data.request_id)
        embeddings = await context.state.get(emb_group_id, emb_key)
        
        if not embeddings:
            context.logger.warn("No embeddings found in state", {"request_id": data.request_id})
            # Still emit build-graph with empty clusters
            await context.emit({
                "topic": "build-graph",
                "data": {
                    "request_id": data.request_id,
                    "mode": data.mode
                }
            })
            return
        
        # Unwrap if needed
        if isinstance(embeddings, dict) and "data" in embeddings:
            embeddings = embeddings.get("data", [])
        
        if data.mode == "shopping":
            # Shopping mode: cluster products
            group_id, key = StateKeys.products(data.request_id)
            products = await context.state.get(group_id, key)
            
            if isinstance(products, dict) and "data" in products:
                products = products.get("data", [])
            
            # Cluster products by similarity
            clusters = await product_service.cluster_products_by_similarity(products)
            
        else:
            # Knowledge graph or study mode: cluster concepts
            group_id, key = StateKeys.concepts(data.request_id)
            concepts = await context.state.get(group_id, key)
            
            if isinstance(concepts, dict) and "data" in concepts:
                concepts = concepts.get("data", [])
            
            # Cluster concepts
            clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        
        # Store clusters
        cluster_group_id, cluster_key = StateKeys.clusters(data.request_id)
        await context.state.set(cluster_group_id, cluster_key, clusters)
        
        context.logger.info("Clustering completed", {
            "request_id": data.request_id,
            "cluster_count": len(clusters)
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "clustered",
            "cluster_count": len(clusters)
        })
        
        # Emit next event
        await context.emit({
            "topic": "build-graph",
            "data": {
                "request_id": data.request_id,
                "mode": data.mode
            }
        })
        
    except Exception as e:
        context.logger.error("Error clustering concepts", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "cluster_concepts"
        })
        raise

