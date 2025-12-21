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
        
        IMPORTANT: For multiple_choice questions, generate 4 DISTINCT and MEANINGFUL options. Do NOT use generic placeholders like "Option 1", "Option 2", etc. Each option should be a plausible answer related to the concept.
        
        Return ONLY a valid JSON array:
        [
          {{
            "type": "multiple_choice" | "true_false" | "short_answer",
            "question": "question text",
            "options": ["specific option 1", "specific option 2", "specific option 3", "specific option 4"] (only for multiple_choice - must be 4 distinct meaningful options),
            "correct_answer": "correct answer",
            "explanation": "brief explanation",
            "concept_id": "related concept id"
          }}
        ]
        
        For multiple_choice questions, ensure all 4 options are:
        - Distinct and meaningful (not generic placeholders)
        - Related to the concept
        - One is clearly correct, others are plausible but incorrect
        
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
        
        # Ensure each question has required fields and validate options
        for i, q in enumerate(questions):
            if "concept_id" not in q and concepts:
                q["concept_id"] = concepts[i % len(concepts)].get("id", "")
            if "explanation" not in q:
                q["explanation"] = "See concept details for more information."
            
            # Validate and fix multiple_choice options
            if q.get("type") == "multiple_choice":
                options = q.get("options", [])
                # Check if options are generic placeholders
                if not options or any(opt in ["Option 1", "Option 2", "Option 3", "Option 4"] for opt in options):
                    # Regenerate options for this question
                    concept = next((c for c in concepts if c.get("id") == q.get("concept_id")), None)
                    if concept:
                        concept_name = concept.get('name', 'concept')
                        concept_desc = concept.get("description", "")
                        
                        # Get other concepts for wrong options
                        other_concepts = [c for c in concepts if c.get("id") != q.get("concept_id")]
                        wrong_options = []
                        for other_concept in other_concepts[:3]:
                            other_desc = other_concept.get("description", "")
                            if other_desc:
                                wrong_options.append(other_desc[:60])
                        
                        # Ensure we have 4 options
                        while len(wrong_options) < 3:
                            wrong_options.append(f"Alternative explanation for {concept_name}")
                        
                        q["options"] = [
                            concept_desc[:60] if concept_desc else f"The correct definition of {concept_name}",
                            wrong_options[0] if wrong_options else "An incorrect option",
                            wrong_options[1] if len(wrong_options) > 1 else "Another incorrect option",
                            wrong_options[2] if len(wrong_options) > 2 else "Yet another incorrect option"
                        ]
                        # Update correct_answer if it was a placeholder
                        if q.get("correct_answer") in ["Option 1", "Option 2", "Option 3", "Option 4"]:
                            q["correct_answer"] = q["options"][0]
        
        return questions[:num_questions]
        
    except Exception as e:
        # Fallback: generate simple questions with meaningful options
        fallback_questions = []
        for i, concept in enumerate(concepts[:num_questions]):
            concept_name = concept.get('name', 'this concept')
            concept_desc = concept.get("description", "")
            
            # Generate meaningful wrong options based on other concepts
            other_concepts = [c for c in concepts if c.get("id") != concept.get("id")]
            wrong_options = []
            for other_concept in other_concepts[:3]:
                other_desc = other_concept.get("description", "")
                if other_desc:
                    wrong_options.append(other_desc[:60])
            
            # Fill remaining options if needed
            while len(wrong_options) < 3:
                wrong_options.append(f"Alternative explanation for {concept_name}")
            
            fallback_questions.append({
                "type": "multiple_choice",
                "question": f"What is {concept_name}?",
                "options": [
                    concept_desc[:60] if concept_desc else f"The correct definition of {concept_name}",
                    wrong_options[0] if wrong_options else "An incorrect option",
                    wrong_options[1] if len(wrong_options) > 1 else "Another incorrect option",
                    wrong_options[2] if len(wrong_options) > 2 else "Yet another incorrect option"
                ],
                "correct_answer": concept_desc[:60] if concept_desc else f"The correct definition of {concept_name}",
                "explanation": f"See {concept_name} for details.",
                "concept_id": concept.get("id", "")
            })
        return fallback_questions
