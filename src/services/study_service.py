"""Service for study mode: concept hierarchy and learning paths."""
import os
import json
from typing import List, Dict
from google import genai

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def assign_concept_level(concept: Dict, context: Dict = None) -> int:
    """
    Assign concept level: Beginner (1), Intermediate (2), Advanced (3).
    
    Args:
        concept: Concept dictionary with name and description
        context: Optional context dictionary
        
    Returns:
        Level integer (1, 2, or 3)
    """
    try:
        prompt = f"""Analyze the complexity of this concept and assign it a level:
        - Level 1 (Beginner): Basic, introductory concepts that require no prior knowledge
        - Level 2 (Intermediate): Concepts that require some foundational knowledge
        - Level 3 (Advanced): Complex concepts requiring significant prior knowledge
        
        Concept: {concept.get('name', '')}
        Description: {concept.get('description', '')}
        
        Return ONLY the number (1, 2, or 3), no other text."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        # Extract number
        level = int(text[0]) if text and text[0].isdigit() else 2
        return max(1, min(3, level))  # Clamp between 1 and 3
        
    except Exception as e:
        # Default to intermediate
        return 2


async def build_learning_path(concepts: List[Dict]) -> List[Dict]:
    """
    Generate suggested learning sequence for concepts.
    
    Args:
        concepts: List of concept dictionaries with levels
        
    Returns:
        List of concepts in suggested learning order
    """
    try:
        # Sort by level first (Beginner -> Intermediate -> Advanced)
        concepts_with_levels = []
        for concept in concepts:
            level = concept.get("level", 2)
            concepts_with_levels.append((level, concept))
        
        # Sort by level, then by name for consistency
        concepts_with_levels.sort(key=lambda x: (x[0], x[1].get("name", "")))
        
        # Assign learning path positions
        learning_path = []
        for position, (level, concept) in enumerate(concepts_with_levels):
            concept_copy = concept.copy()
            concept_copy["learning_path_position"] = position
            learning_path.append(concept_copy)
        
        return learning_path
        
    except Exception as e:
        # Fallback: return concepts as-is
        return concepts


# identify_prerequisites function removed - feature no longer used
