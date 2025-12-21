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


async def search_products(
    query: str, 
    num_results: int = 10,
    filters: Optional[Dict] = None,
    location: Optional[str] = None,
    gl: Optional[str] = "us",  # Country code
    hl: Optional[str] = "en"   # Language code
) -> List[Dict]:
    """
    Search for products using SerpAPI Google Shopping and return product data.
    
    Args:
        query: Search query string
        num_results: Number of results to return
        filters: Optional dict with filter parameters:
            - price_min: Minimum price (float)
            - price_max: Maximum price (float)
            - brand: Brand name to filter by
            - rating_min: Minimum rating (float)
        location: Optional location string (e.g., "Austin, Texas, United States")
        gl: Country code (default: "us")
        hl: Language code (default: "en")
        
    Returns:
        List of product dictionaries with comprehensive product information
    """
    if not SERPAPI_API_KEY:
        raise Exception("SERPAPI_API_KEY not found in environment variables")
    
    try:
        GoogleSearch = _get_google_search()
        
        # Use google_shopping engine for better results
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": num_results,
            "gl": gl,
            "hl": hl
        }
        
        # Add location if provided
        if location:
            params["location"] = location
        
        # Build filter query string if filters provided
        # Note: SerpAPI uses shoprs parameter for advanced filters, but we can also
        # add filters to the query string for basic filtering
        filter_parts = []
        if filters:
            if filters.get("price_min") is not None:
                filter_parts.append(f"under ${filters['price_min']}")
            if filters.get("price_max") is not None:
                filter_parts.append(f"under ${filters['price_max']}")
            if filters.get("brand"):
                # Add brand to query for better filtering
                params["q"] = f"{query} {filters['brand']}"
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        products = []
        
        # Parse shopping results (Google Shopping API returns shopping_results)
        if "shopping_results" in results:
            for item in results["shopping_results"][:num_results]:
                # Extract comprehensive product data
                product = {
                    "id": item.get("product_id") or item.get("position") or f"product_{len(products)}",
                    "name": item.get("title", "Unknown Product"),
                    "image_url": item.get("thumbnail") or item.get("image", ""),
                    "price": _parse_price(item.get("price", "")),
                    "rating": _parse_rating(item.get("rating", None)),
                    "retailer": item.get("source", "Unknown"),
                    "url": item.get("link", ""),
                    "description": item.get("snippet") or item.get("description", ""),
                    "reviews": item.get("reviews", 0),
                    # Additional fields from Google Shopping
                    "shipping": item.get("shipping", ""),
                    "delivery": item.get("delivery", ""),
                    "category": item.get("product_type", ""),
                    "condition": item.get("condition", "new"),
                    "availability": item.get("availability", "in stock")
                }
                
                # Extract price details if available
                if "extracted_price" in item:
                    product["extracted_price"] = item["extracted_price"]
                if "original_price" in item:
                    product["original_price"] = _parse_price(item["original_price"])
                
                # Apply client-side filters if needed (as backup)
                if filters:
                    # Price filter
                    if filters.get("price_min") and product["price"]:
                        if product["price"] < filters["price_min"]:
                            continue
                    if filters.get("price_max") and product["price"]:
                        if product["price"] > filters["price_max"]:
                            continue
                    # Rating filter
                    if filters.get("rating_min") and product["rating"]:
                        if product["rating"] < filters["rating_min"]:
                            continue
                
                products.append(product)
        
        # Fallback to tbm=shop if google_shopping engine doesn't work
        if not products:
            params = {
                "q": query,
                "tbm": "shop",  # Shopping search
                "api_key": SERPAPI_API_KEY,
                "num": num_results,
                "gl": gl,
                "hl": hl
            }
            if location:
                params["location"] = location
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "shopping_results" in results:
                for item in results["shopping_results"][:num_results]:
                    product = {
                        "id": item.get("product_id", f"product_{len(products)}"),
                        "name": item.get("title", "Unknown Product"),
                        "image_url": item.get("thumbnail", ""),
                        "price": _parse_price(item.get("price", "")),
                        "rating": _parse_rating(item.get("rating", None)),
                        "retailer": item.get("source", "Unknown"),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                        "reviews": item.get("reviews", 0),
                        "shipping": item.get("shipping", ""),
                        "category": item.get("product_type", "")
                    }
                    products.append(product)
        
        # Final fallback: regular search results (last resort)
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


def _parse_rating(rating_value) -> Optional[float]:
    """Parse rating value to float."""
    if rating_value is None:
        return None
    
    try:
        if isinstance(rating_value, (int, float)):
            return float(rating_value)
        if isinstance(rating_value, str):
            # Try to extract number from string
            import re
            match = re.search(r"[\d.]+", rating_value)
            if match:
                return float(match.group())
    except:
        pass
    
    return None


def _parse_rating(rating_value) -> Optional[float]:
    """Parse rating value to float."""
    if rating_value is None:
        return None
    
    try:
        if isinstance(rating_value, (int, float)):
            return float(rating_value)
        if isinstance(rating_value, str):
            # Try to extract number from string
            import re
            match = re.search(r"[\d.]+", rating_value)
            if match:
                return float(match.group())
    except:
        pass
    
    return None


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
