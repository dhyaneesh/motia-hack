import os
from dotenv import load_dotenv
from exa_py import Exa
from typing import List, Dict

# Load environment variables from .env file
load_dotenv()

# Initialize Exa client
exa = Exa(api_key=os.environ.get("EXA_API_KEY"))


async def search(query: str, num_results: int = 5) -> List[Dict]:
    """Search for articles using Exa AI and return with full content."""
    try:
        response = exa.search_and_contents(
            query,
            type="neural",
            num_results=num_results,
            text=True  # Include full text
        )
        
        results = []
        for r in response.results:
            # Handle published_date - could be datetime or string
            published_date = None
            if r.published_date:
                if hasattr(r.published_date, 'isoformat'):
                    published_date = r.published_date.isoformat()
                else:
                    published_date = str(r.published_date)
            
            results.append({
                "id": r.id or f"exa_{len(results)}",
                "url": r.url,
                "title": r.title or "Untitled",
                "text": r.text or "",
                "published_date": published_date,
                "author": getattr(r, 'author', None)
            })
        
        return results
    except Exception as e:
        raise Exception(f"Error searching Exa: {str(e)}")


async def search_multiple(queries: List[str], num_results_per_query: int = 3) -> Dict[str, List[Dict]]:
    """Search for multiple queries and return results grouped by query."""
    results = {}
    for query in queries:
        try:
            results[query] = await search(query, num_results_per_query)
        except Exception as e:
            results[query] = []
    return results

