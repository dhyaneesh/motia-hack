import os
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def generate_answer(question: str, context: dict = None) -> str:
    """Generate an answer to a question using Gemini LLM."""
    try:
        system_prompt = """You are a helpful knowledge assistant. Answer questions clearly and 
        identify key concepts that should be explored further. Be concise but informative."""
        
        prompt = f"{system_prompt}\n\nQuestion: {question}"
        
        if context:
            prompt += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise Exception(f"Error generating answer: {str(e)}")


async def extract_concepts(question: str, answer: str) -> list[dict]:
    """Extract key concepts from question and answer using Gemini."""
    try:
        prompt = f"""Extract key concepts from this Q&A. Return ONLY a valid JSON array with no markdown formatting:
        [{{"id": "unique_id", "name": "concept name", "type": "concept|entity|event|person", "description": "brief description"}}]
        
        Question: {question}
        Answer: {answer}
        
        Return the JSON array only, no other text."""
        
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
        
        concepts = json.loads(text)
        
        # Ensure each concept has a consistent id format
        for idx, concept in enumerate(concepts):
            if "id" not in concept or not concept.get("id"):
                # Generate ID from name if not provided
                name_slug = concept.get('name', 'unknown').lower().replace(' ', '_').replace('-', '_')
                concept["id"] = f"concept_{idx}_{name_slug}"
            else:
                # Normalize existing ID to ensure consistency
                existing_id = concept["id"]
                # If it doesn't start with "concept_", add the prefix
                if not existing_id.startswith("concept_"):
                    name_slug = existing_id.lower().replace(' ', '_').replace('-', '_')
                    concept["id"] = f"concept_{idx}_{name_slug}"
        
        return concepts
    except json.JSONDecodeError as e:
        raise Exception(f"Error parsing concepts JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extracting concepts: {str(e)}")


async def generate_cluster_label(concepts: list[dict]) -> str:
    """Generate a human-readable label for a cluster of concepts."""
    try:
        concept_names = [c.get("name", "") for c in concepts[:5]]  # Limit to first 5
        prompt = f"""Generate a short, descriptive label (2-4 words) for this group of related concepts:
        {', '.join(concept_names)}
        
        Return only the label, no other text."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        # Fallback to first concept name
        return concepts[0].get("name", "Concepts") if concepts else "Concepts"

