"""Service for generating quiz questions from knowledge graph concepts."""
import os
import json
from typing import List, Dict
from google import genai

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def generate_quiz(concepts: List[Dict], num_questions: int = 5) -> List[Dict]:
    """
    Generate practice questions from concept knowledge graph.
    
    Args:
        concepts: List of concept dictionaries
        num_questions: Number of questions to generate
        
    Returns:
        List of question dictionaries with type, question, options, answer
    """
    try:
        # Prepare concept information
        concept_info = "\n".join([
            f"- {c.get('name', '')}: {c.get('description', '')}"
            for c in concepts[:10]  # Limit for token efficiency
        ])
        
        prompt = f"""Generate {num_questions} quiz questions based on these concepts. Mix question types: multiple choice, true/false, and short answer.

        Concepts:
        {concept_info}
        
        Return ONLY a valid JSON array:
        [
          {{
            "type": "multiple_choice" | "true_false" | "short_answer",
            "question": "question text",
            "options": ["option1", "option2", ...] (only for multiple_choice),
            "correct_answer": "correct answer",
            "explanation": "brief explanation",
            "concept_id": "related concept id"
          }}
        ]
        
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
        
        questions = json.loads(text)
        
        # Ensure each question has required fields
        for i, q in enumerate(questions):
            if "concept_id" not in q and concepts:
                q["concept_id"] = concepts[i % len(concepts)].get("id", "")
            if "explanation" not in q:
                q["explanation"] = "See concept details for more information."
        
        return questions[:num_questions]
        
    except Exception as e:
        # Fallback: generate simple questions
        fallback_questions = []
        for i, concept in enumerate(concepts[:num_questions]):
            fallback_questions.append({
                "type": "multiple_choice",
                "question": f"What is {concept.get('name', 'this concept')}?",
                "options": [
                    concept.get("description", "Option 1")[:50],
                    "Option 2",
                    "Option 3",
                    "Option 4"
                ],
                "correct_answer": concept.get("description", "Option 1")[:50],
                "explanation": f"See {concept.get('name', 'concept')} for details.",
                "concept_id": concept.get("id", "")
            })
        return fallback_questions
