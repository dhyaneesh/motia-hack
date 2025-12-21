"""Event step for searching products using SerpAPI."""
from pydantic import BaseModel
from typing import Optional, Dict
from src.services import serpapi_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class SearchProductsInput(BaseModel):
    request_id: str
    query: str
    num_results: int = 10
    parsed_attributes: Optional[Dict] = None
    filters: Optional[Dict] = None

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
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Search for products, store in state, emit next event."""
    try:
        # Parse input
        data = SearchProductsInput(**input_data)
        
        context.logger.info("Searching products", {
            "request_id": data.request_id,
            "query": data.query,
            "num_results": data.num_results,
            "parsed_attributes": data.parsed_attributes,
            "filters": data.filters
        })
        
        # Prepare filters for SerpAPI
        serpapi_filters = {}
        if data.filters:
            # Extract price filters
            if data.filters.get("price_min") is not None:
                serpapi_filters["price_min"] = float(data.filters["price_min"])
            if data.filters.get("price_max") is not None:
                serpapi_filters["price_max"] = float(data.filters["price_max"])
            # Extract rating filter
            if data.filters.get("rating_min") is not None:
                serpapi_filters["rating_min"] = float(data.filters["rating_min"])
            # Extract brand if available
            if data.parsed_attributes and data.parsed_attributes.get("brand"):
                serpapi_filters["brand"] = data.parsed_attributes["brand"]
        
        # Search products via SerpAPI (using optimized query from LLM parsing)
        products = await serpapi_service.search_products(
            data.query, 
            data.num_results,
            filters=serpapi_filters if serpapi_filters else None
        )
        
        # Apply filters if provided (price range, rating, etc.)
        if data.filters:
            filtered_products = []
            for product in products:
                # Apply price filters
                if data.filters.get("price_min") is not None:
                    if product.get("price") is None or product.get("price") < data.filters["price_min"]:
                        continue
                if data.filters.get("price_max") is not None:
                    if product.get("price") is None or product.get("price") > data.filters["price_max"]:
                        continue
                # Apply rating filter
                if data.filters.get("rating_min") is not None:
                    if product.get("rating") is None or product.get("rating") < data.filters["rating_min"]:
                        continue
                filtered_products.append(product)
            products = filtered_products
        
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

