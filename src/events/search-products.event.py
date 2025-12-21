"""Event step for searching products using SerpAPI."""
from pydantic import BaseModel
from src.services import serpapi_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

class SearchProductsInput(BaseModel):
    request_id: str
    query: str
    num_results: int = 10

config = {
    "name": "SearchProducts",
    "type": "event",
    "description": "Search for products using SerpAPI",
    "subscribes": ["search-products"],
    "emits": ["extract-specs"],
    "flows": ["shopping-flow"],
    "input": SearchProductsInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 3,
            "timeout": 30,
            "backoffRate": 2
        }
    }
}

@with_timing("SearchProducts")
async def handler(input_data, context):
    """Search for products, store in state, emit next event."""
    try:
        # Parse input
        data = SearchProductsInput(**input_data)
        
        context.logger.info("Searching products", {
            "request_id": data.request_id,
            "query": data.query,
            "num_results": data.num_results
        })
        
        # Search products via SerpAPI
        products = await serpapi_service.search_products(data.query, data.num_results)
        
        context.logger.info("Found products", {
            "request_id": data.request_id,
            "product_count": len(products)
        })
        
        # Store products in state
        group_id, key = StateKeys.products(data.request_id)
        await context.state.set(group_id, key, products)
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "products_searched",
            "product_count": len(products)
        })
        
        # Emit next event
        await context.emit({
            "topic": "extract-specs",
            "data": {
                "request_id": data.request_id
            }
        })
        
    except Exception as e:
        context.logger.error("Error searching products", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "search_products"
        })
        raise

