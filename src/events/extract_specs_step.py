"""Event step for extracting product specs and reviews."""
from pydantic import BaseModel
from src.services import product_service
from src.utils.state_keys import StateKeys
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

class ExtractSpecsInput(BaseModel):
    request_id: str

config = {
    "name": "ExtractSpecs",
    "type": "event",
    "description": "Extract product specifications and review summaries",
    "subscribes": ["extract-specs"],
    "emits": ["generate-embeddings"],
    "flows": ["shopping-flow"],
    "input": ExtractSpecsInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 2,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Extract specs and reviews for products, store in state, emit next event."""
    try:
        # Parse input
        data = ExtractSpecsInput(**input_data)
        
        context.logger.info("Extracting product specs", {
            "request_id": data.request_id
        })
        
        # Fetch products from state
        group_id, key = StateKeys.products(data.request_id)
        products = await context.state.get(group_id, key)
        
        if not products:
            context.logger.warn("No products found in state", {"request_id": data.request_id})
            return
        
        # Unwrap if needed
        if isinstance(products, dict) and "data" in products:
            products = products.get("data", [])
        
        # Extract specs and reviews for each product
        for product in products:
            try:
                # Extract specs from description
                if product.get("description"):
                    specs = await product_service.extract_product_specs(product["description"])
                    product["specs"] = specs
                else:
                    product["specs"] = {}
                
                # For now, use description as review summary placeholder
                if product.get("description"):
                    product["review_summary"] = product["description"][:200] + "..."
                else:
                    product["review_summary"] = "No reviews available"
                
                # Ensure source link is present as references
                if product.get("url"):
                    product["references"] = [{
                        "id": product.get("id", ""),
                        "url": product["url"],
                        "title": product.get("name", "Product"),
                        "text": product.get("description", "")
                    }]
                else:
                    product["references"] = []
                    
            except Exception as e:
                context.logger.info(f"Failed to process product {product.get('id')}", {
                    "error": str(e),
                    "product_id": product.get("id")
                })
                product["specs"] = {}
                product["review_summary"] = "No reviews available"
                product["references"] = []
        
        # Store updated products
        await context.state.set(group_id, key, products)
        
        context.logger.info("Extracted product specs", {
            "request_id": data.request_id,
            "products_processed": len(products)
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "specs_extracted",
            "product_count": len(products)
        })
        
        # Emit next event: generate embeddings
        await context.emit({
            "topic": "generate-embeddings",
            "data": {
                "request_id": data.request_id,
                "mode": "shopping"
            }
        })
        
    except Exception as e:
        context.logger.error("Error extracting specs", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "extract_specs"
        })
        raise

