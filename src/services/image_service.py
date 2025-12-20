"""Service for processing image searches using vision models."""
import os
import base64
from typing import Dict
from google import genai

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


async def process_image_search(image_file: bytes, mode: str) -> Dict:
    """
    Process uploaded image for search based on mode.
    
    Args:
        image_file: Image file bytes
        mode: 'shopping' or 'study'
        
    Returns:
        Dictionary with extracted information and search query
    """
    try:
        # Convert image to base64 for Gemini Vision API
        image_base64 = base64.b64encode(image_file).decode('utf-8')
        
        if mode == "shopping":
            # Extract product features for shopping
            prompt = """Analyze this image and describe the product shown. Extract:
            1. Product name/type
            2. Key features
            3. Brand (if visible)
            4. Color/style
            
            Return a search query that would help find similar products online."""
        else:
            # Extract concepts for study
            prompt = """Analyze this image and identify:
            1. Main concepts or topics shown
            2. Key information or ideas
            3. What someone might want to learn about this
            
            Return a search query that would help find educational content about these concepts."""
        
        # Detect MIME type (default to jpeg)
        # In production, you'd detect this from the image file
        mime_type = "image/jpeg"
        
        # Use Gemini Vision API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                {
                    "mime_type": mime_type,
                    "data": image_base64
                }
            ]
        )
        
        search_query = response.text.strip()
        
        return {
            "search_query": search_query,
            "mode": mode,
            "extracted_info": response.text
        }
        
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")
