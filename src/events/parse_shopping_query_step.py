"""Event step for parsing natural language shopping queries using LLM."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.utils.state_keys import StateKeys
import json
import os
import sys
from pathlib import Path
from google import genai

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class ParseShoppingQueryInput(BaseModel):
    request_id: str
    query: str
    num_results: int = 10

class ParsedQuery(BaseModel):
    product_type: str  # Main product category
    search_query: str  # Optimized search query for product search APIs
    attributes: Dict[str, Any]  # Extracted attributes (colors, size, material, etc.)
    filters: Dict[str, Any]  # Potential filters (price range, brand, etc.)

config = {
    "name": "ParseShoppingQuery",
    "type": "event",
    "description": "Parse natural language shopping queries to extract product attributes and optimize search terms",
    "subscribes": ["parse-shopping-query"],
    "emits": ["search-products"],
    "flows": ["shopping-flow"],
    "input": ParseShoppingQueryInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 2,
            "backoffRate": 2
        }
    }
}

async def handler(input_data, context):
    """Parse natural language query, extract attributes, optimize search query."""
    try:
        # Parse input
        data = ParseShoppingQueryInput(**input_data)
        
        context.logger.info("Parsing shopping query", {
            "request_id": data.request_id,
            "query": data.query
        })
        
        # Use LLM to parse the natural language query
        prompt = f"""Parse this natural language shopping query and extract structured product information. Return ONLY a valid JSON object with no markdown formatting:

{{
    "product_type": "main product category (e.g., 'blanket', 'laptop', 'shoes')",
    "search_query": "optimized search query for product search APIs (prioritize product type and key attributes)",
    "attributes": {{
        "colors": ["color1", "color2"],
        "size": "size if mentioned",
        "material": "material if mentioned",
        "season": "season if mentioned",
        "brand": "brand if mentioned",
        "style": "style if mentioned",
        "features": ["feature1", "feature2"]
    }},
    "filters": {{
        "price_min": null,
        "price_max": null,
        "rating_min": null
    }}
}}

Shopping Query: {data.query}

Instructions:
- Extract the main product type/category
- Create an optimized search_query that combines product type with key attributes (colors, season, etc.)
- Extract all mentioned attributes (colors, size, material, season, brand, style, features)
- If price range or rating is mentioned, include in filters
- Return ONLY the JSON object, no markdown, no explanations

Return the JSON object only, no other text."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        
        # Parse JSON response
        parsed_data = json.loads(text)
        
        # Validate and structure the parsed data
        parsed_query = {
            "product_type": parsed_data.get("product_type", ""),
            "search_query": parsed_data.get("search_query", data.query),  # Fallback to original query
            "attributes": parsed_data.get("attributes", {}),
            "filters": parsed_data.get("filters", {})
        }
        
        # Store parsed query in state
        parsed_group_id, parsed_key = StateKeys.parsed_shopping_query(data.request_id)
        await context.state.set(parsed_group_id, parsed_key, parsed_query)
        
        # Update request data with parsed information
        data_group_id, data_key = StateKeys.request_data(data.request_id)
        request_data = await context.state.get(data_group_id, data_key)
        if isinstance(request_data, dict) and "data" in request_data:
            request_data = request_data.get("data", {})
        
        if isinstance(request_data, dict):
            request_data["parsed_query"] = parsed_query
            request_data["original_query"] = data.query
            await context.state.set(data_group_id, data_key, request_data)
        
        context.logger.info("Parsed shopping query", {
            "request_id": data.request_id,
            "product_type": parsed_query["product_type"],
            "search_query": parsed_query["search_query"],
            "attributes": parsed_query["attributes"]
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "query_parsed",
            "product_type": parsed_query["product_type"]
        })
        
        # Use num_results from input
        num_results = data.num_results
        
        # Emit search-products event with optimized query
        await context.emit({
            "topic": "search-products",
            "data": {
                "request_id": data.request_id,
                "query": parsed_query["search_query"],  # Use optimized query
                "num_results": num_results,
                "parsed_attributes": parsed_query["attributes"],
                "filters": parsed_query["filters"]
            }
        })
        
    except json.JSONDecodeError as e:
        context.logger.error("Error parsing LLM JSON response", {
            "error": str(e),
            "request_id": data.request_id,
            "response_text": text if 'text' in locals() else "N/A"
        })
        # Fallback: use original query
        await context.emit({
            "topic": "search-products",
            "data": {
                "request_id": data.request_id,
                "query": data.query,
                "num_results": 10
            }
        })
    except Exception as e:
        context.logger.error("Error parsing shopping query", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Fallback: use original query
        await context.emit({
            "topic": "search-products",
            "data": {
                "request_id": data.request_id,
                "query": data.query,
                "num_results": 10
            }
        })
