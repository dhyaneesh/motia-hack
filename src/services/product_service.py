"""Service for processing product data: extracting specs, summarizing reviews, clustering."""
import os
import json
from typing import List, Dict
from google import genai
from src.services import embedding_service, clustering_service

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def extract_product_specs(description: str) -> Dict:
    """
    Use LLM to extract key specifications from product description.
    
    Args:
        description: Product description text
        
    Returns:
        Dictionary of extracted specifications
    """
    try:
        prompt = f"""Extract key specifications from this product description. Return ONLY a valid JSON object with no markdown formatting:
        {{"specs": {{"key": "value"}}}}
        
        Product Description: {description}
        
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
        
        result = json.loads(text)
        return result.get("specs", {})
        
    except Exception as e:
        # Fallback: return empty specs
        return {}


async def summarize_reviews(reviews: List[str]) -> str:
    """
    Generate concise review summaries highlighting majority words.
    
    Args:
        reviews: List of review text strings
        
    Returns:
        Concise summary string with highlighted majority words
    """
    if not reviews:
        return "No reviews available"
    
    try:
        # Combine reviews (limit to first 10 for token efficiency)
        combined_reviews = "\n\n".join(reviews[:10])
        
        prompt = f"""Summarize these product reviews in 2-3 sentences. Highlight the most frequently mentioned words/phrases that appear in the majority of reviews. Be very concise.

        Reviews:
        {combined_reviews}
        
        Return only the summary, no other text."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        # Fallback: return first review snippet
        return reviews[0][:200] + "..." if reviews else "No reviews available"


async def cluster_products_by_similarity(products: List[Dict]) -> List[Dict]:
    """
    Cluster products by visual similarity using embeddings.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        List of clusters with product IDs
    """
    if len(products) < 2:
        return [{
            "id": "0",
            "label": "All Products",
            "productIds": [p.get("id", f"product_{i}") for i, p in enumerate(products)]
        }]
    
    try:
        # Generate embeddings for products (using name + description)
        product_texts = [
            f"{p.get('name', '')} {p.get('description', '')}" 
            for p in products
        ]
        
        embeddings = await embedding_service.get_embeddings(product_texts)
        
        # Use existing clustering service
        concepts = [
            {
                "id": p.get("id", f"product_{i}"),
                "name": p.get("name", "Unknown"),
                "description": p.get("description", ""),
                "type": "product"
            }
            for i, p in enumerate(products)
        ]
        
        clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        
        # Convert to product cluster format
        product_clusters = []
        for cluster in clusters:
            product_clusters.append({
                "id": cluster["id"],
                "label": cluster.get("label", "Product Group"),
                "productIds": cluster.get("conceptIds", [])
            })
        
        return product_clusters
        
    except Exception as e:
        # Fallback: single cluster
        return [{
            "id": "0",
            "label": "All Products",
            "productIds": [p.get("id", f"product_{i}") for i, p in enumerate(products)]
        }]
