"""Service for study mode: concept hierarchy and learning paths."""
import os
import json
from typing import List, Dict
from google import genai

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def assign_concept_level(concept: Dict, context: Dict = None) -> int | None:
    """
    Assign concept level: Beginner (1), Intermediate (2), Advanced (3).
    
    Args:
        concept: Concept dictionary with name and description
        context: Optional context dictionary
        
    Returns:
        Level integer (1, 2, or 3) or None if assignment fails
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
        # Extract number - try multiple strategies
        level = None
        if text:
            # Try to find a digit in the response
            import re
            digits = re.findall(r'\d', text)
            if digits:
                level = int(digits[0])
            else:
                # Try to parse common responses
                text_lower = text.lower()
                if 'beginner' in text_lower or '1' in text_lower:
                    level = 1
                elif 'intermediate' in text_lower or '2' in text_lower:
                    level = 2
                elif 'advanced' in text_lower or '3' in text_lower:
                    level = 3
        
        # If level was found, clamp it between 1 and 3
        if level is not None:
            return max(1, min(3, level))
        
        # Return None if assignment failed
        return None
        
    except Exception as e:
        # Return None if assignment fails
        return None


async def build_learning_path(concepts: List[Dict]) -> List[Dict]:
    """
    Generate suggested learning sequence for concepts.
    
    Args:
        concepts: List of concept dictionaries with levels
        
    Returns:
        List of concepts in suggested learning order
    """
    try:
        # Sort by level first (Beginner -> Intermediate -> Advanced -> Concepts without levels)
        concepts_with_levels = []
        concepts_without_levels = []
        
        for concept in concepts:
            level = concept.get("level")
            # Check if level is a valid numeric level (1, 2, or 3)
            if level is not None and isinstance(level, int) and level in [1, 2, 3]:
                concepts_with_levels.append((level, concept))
            else:
                # Use "Concept" as placeholder for sorting (will be sorted last)
                # Ensure level is set to "Concept" if it's not a valid numeric level
                if level != "Concept":
                    concept["level"] = "Concept"
                concepts_without_levels.append((999, concept))  # Use high number to sort last
        
        # Sort by level, then by name for consistency
        concepts_with_levels.sort(key=lambda x: (x[0], x[1].get("name", "")))
        concepts_without_levels.sort(key=lambda x: x[1].get("name", ""))
        
        # Combine: concepts with levels first, then concepts without levels
        all_concepts = concepts_with_levels + concepts_without_levels
        
        # Assign learning path positions
        learning_path = []
        for position, (level, concept) in enumerate(all_concepts):
            concept_copy = concept.copy()
            concept_copy["learning_path_position"] = position
            # Ensure level is set to "Concept" if it's not a valid numeric level
            if concept_copy.get("level") is None or (not isinstance(concept_copy.get("level"), int) or concept_copy.get("level") not in [1, 2, 3]):
                concept_copy["level"] = "Concept"
            learning_path.append(concept_copy)
        
        return learning_path
        
    except Exception as e:
        # Fallback: return concepts as-is
        return concepts


# identify_prerequisites function removed - feature no longer used
