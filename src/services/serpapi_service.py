"""Service for SerpAPI integration to search products and fetch images."""
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")

# Lazy import to avoid breaking flow collection if package is not installed
def _get_google_search():
    """Lazy import of GoogleSearch to avoid import errors during flow collection."""
    try:
        from serpapi import GoogleSearch
        return GoogleSearch
    except ImportError:
        # Try alternative import path
        try:
            from serpapi.google_search import GoogleSearch
            return GoogleSearch
        except ImportError:
            raise ImportError(
                "serpapi package not found. Install it with: pip install google-search-results"
            )


async def search_products(query: str, num_results: int = 10) -> List[Dict]:
    """
    Search for products using SerpAPI and return product data with images.
    
    Args:
        query: Search query string
        num_results: Number of results to return
        
    Returns:
        List of product dictionaries with image URLs, prices, ratings, retailer info
    """
    if not SERPAPI_API_KEY:
        raise Exception("SERPAPI_API_KEY not found in environment variables")
    
    try:
        GoogleSearch = _get_google_search()
        params = {
            "q": query,
            "tbm": "shop",  # Shopping search
            "api_key": SERPAPI_API_KEY,
            "num": num_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        products = []
        
        # Parse shopping results
        if "shopping_results" in results:
            for item in results["shopping_results"][:num_results]:
                product = {
                    "id": item.get("product_id", f"product_{len(products)}"),
                    "name": item.get("title", "Unknown Product"),
                    "image_url": item.get("thumbnail", ""),
                    "price": _parse_price(item.get("price", "")),
                    "rating": item.get("rating", 0.0),
                    "retailer": item.get("source", "Unknown"),
                    "url": item.get("link", ""),
                    "description": item.get("snippet", ""),
                    "reviews": item.get("reviews", 0)
                }
                products.append(product)
        
        # If no shopping results, try regular search with images
        if not products and "organic_results" in results:
            for item in results["organic_results"][:num_results]:
                product = {
                    "id": item.get("position", f"product_{len(products)}"),
                    "name": item.get("title", "Unknown Product"),
                    "image_url": item.get("thumbnail", ""),
                    "price": None,
                    "rating": None,
                    "retailer": item.get("source", "Unknown"),
                    "url": item.get("link", ""),
                    "description": item.get("snippet", ""),
                    "reviews": 0
                }
                products.append(product)
        
        return products
        
    except Exception as e:
        raise Exception(f"Error searching products with SerpAPI: {str(e)}")


def _parse_price(price_str: str) -> Optional[float]:
    """Parse price string to float."""
    if not price_str:
        return None
    
    try:
        # Remove currency symbols and commas
        price_clean = price_str.replace("$", "").replace(",", "").replace("€", "").replace("£", "")
        # Extract first number
        import re
        match = re.search(r"[\d.]+", price_clean)
        if match:
            return float(match.group())
    except:
        pass
    
    return None


async def get_product_images(query: str, num_images: int = 5) -> List[str]:
    """
    Fetch product images for a query.
    
    Args:
        query: Search query string
        num_images: Number of images to return
        
    Returns:
        List of image URLs
    """
    if not SERPAPI_API_KEY:
        raise Exception("SERPAPI_API_KEY not found in environment variables")
    
    try:
        GoogleSearch = _get_google_search()
        params = {
            "q": query,
            "tbm": "isch",  # Image search
            "api_key": SERPAPI_API_KEY,
            "num": num_images
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        images = []
        
        if "images_results" in results:
            for item in results["images_results"][:num_images]:
                image_url = item.get("thumbnail") or item.get("original")
                if image_url:
                    images.append(image_url)
        
        return images
        
    except Exception as e:
        raise Exception(f"Error fetching product images with SerpAPI: {str(e)}")
