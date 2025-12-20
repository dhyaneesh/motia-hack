"""Service for study mode: concept hierarchy, learning paths, prerequisites."""
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
        concepts: List of concept dictionaries with levels and prerequisites
        
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


async def identify_prerequisites(concept: Dict, all_concepts: List[Dict]) -> List[str]:
    """
    Find prerequisite concepts for a given concept.
    
    Args:
        concept: Concept dictionary
        all_concepts: List of all available concepts
        
    Returns:
        List of prerequisite concept IDs
    """
    try:
        concept_names = [c.get("name", "") for c in all_concepts[:10]]  # Limit for token efficiency
        
        prompt = f"""Given this concept and a list of other concepts, identify which concepts are prerequisites (must be learned before this one).

        Concept: {concept.get('name', '')}
        Description: {concept.get('description', '')}
        
        Available concepts: {', '.join(concept_names)}
        
        Return ONLY a JSON array of concept names that are prerequisites, or an empty array [] if none.
        Example: ["Basic Math", "Algebra"]
        Return only the JSON array, no other text."""
        
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
        
        prerequisite_names = json.loads(text)
        
        # Convert names to IDs
        prerequisites = []
        for name in prerequisite_names:
            for c in all_concepts:
                if c.get("name", "").lower() == name.lower():
                    prerequisites.append(c.get("id", ""))
                    break
        
        return prerequisites
        
    except Exception as e:
        # Fallback: return empty list
        return []
