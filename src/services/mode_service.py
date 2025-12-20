"""Service for detecting and managing application modes."""
from typing import Dict, List


def detect_mode(query: str) -> str:
    """
    Auto-detect mode from query intent.
    
    Returns:
        'shopping', 'study', or 'default'
    """
    query_lower = query.lower()
    
    # Shopping keywords
    shopping_keywords = [
        'buy', 'purchase', 'shop', 'shopping', 'price', 'prices', 'cost', 'costs',
        'cheap', 'affordable', 'discount', 'sale', 'deal', 'best price', 'compare prices',
        'where to buy', 'buy online', 'retailer', 'store', 'amazon', 'ebay', 'walmart'
    ]
    
    # Study keywords
    study_keywords = [
        'explain', 'learn', 'learn about', 'how does', 'what is', 'what are',
        'understand', 'concept', 'theory', 'principle', 'definition', 'meaning',
        'tutorial', 'guide', 'study', 'learn how', 'teach me', 'help me understand'
    ]
    
    # Check for shopping intent
    for keyword in shopping_keywords:
        if keyword in query_lower:
            return 'shopping'
    
    # Check for study intent
    for keyword in study_keywords:
        if keyword in query_lower:
            return 'study'
    
    # Default fallback
    return 'default'


def process_query(query: str, mode: str, context: Dict = None) -> Dict:
    """
    Route to mode-specific processors.
    
    Args:
        query: User query string
        mode: Mode to use ('default', 'shopping', 'study')
        context: Optional context dictionary
        
    Returns:
        Dictionary with mode and processed query info
    """
    if context is None:
        context = {}
    
    # Auto-detect if mode is 'auto' or not specified
    if mode == 'auto' or not mode:
        mode = detect_mode(query)
    
    return {
        'mode': mode,
        'query': query,
        'context': context
    }
