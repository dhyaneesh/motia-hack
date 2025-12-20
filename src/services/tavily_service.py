import os
from dotenv import load_dotenv
import httpx
from typing import List, Dict

# Load environment variables from .env file
load_dotenv()

# Tavily API configuration
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_API_URL = "https://api.tavily.com/search"

async def search(query: str, num_results: int = 5) -> List[Dict]:
    """Search for articles using Tavily API and return with full content."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TAVILY_API_URL,
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": True,
                    "max_results": num_results,
                },
                timeout=8.0  # Reduced from 30s to 8s for faster failure
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for r in data.get("results", []):
                # Tavily returns content in 'content' field, or 'raw_content' if include_raw_content=True
                content = r.get("content", "") or r.get("raw_content", "")
                results.append({
                    "id": r.get("url", f"tavily_{len(results)}"),
                    "url": r.get("url", ""),
                    "title": r.get("title", "Untitled"),
                    "text": content,
                    "published_date": None,  # Tavily doesn't provide published_date
                    "author": None  # Tavily doesn't provide author
                })
            
            return results
    except Exception as e:
        raise Exception(f"Error searching Tavily: {str(e)}")


async def search_multiple(queries: List[str], num_results_per_query: int = 3) -> Dict[str, List[Dict]]:
    """Search for multiple queries and return results grouped by query."""
    results = {}
    for query in queries:
        try:
            results[query] = await search(query, num_results_per_query)
        except Exception as e:
            results[query] = []
    return results

