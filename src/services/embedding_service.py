import os
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone
from typing import List

# Load environment variables from .env file
load_dotenv()

# Configure Gemini for embeddings
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = os.environ.get("PINECONE_INDEX", "knowledge-graph")
index = None


def get_index():
    """Get or create Pinecone index."""
    global index
    if index is None:
        try:
            index = pc.Index(index_name)
        except Exception:
            # Index doesn't exist, create it
            pc.create_index(
                name=index_name,
                dimension=768,  # Gemini text-embedding-004 dimension
                metric="cosine"
            )
            index = pc.Index(index_name)
    return index


async def get_embedding(text: str) -> List[float]:
    """Generate embedding for text using Gemini."""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']  # 768-dimensional vector
    except Exception as e:
        raise Exception(f"Error generating embedding: {str(e)}")


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    embeddings = []
    for text in texts:
        embedding = await get_embedding(text)
        embeddings.append(embedding)
    return embeddings


async def store_embedding(id: str, text: str, metadata: dict = None):
    """Store embedding in Pinecone."""
    try:
        embedding = await get_embedding(text)
        idx = get_index()
        idx.upsert(
            vectors=[{
                "id": id,
                "values": embedding,
                "metadata": metadata or {}
            }]
        )
    except Exception as e:
        raise Exception(f"Error storing embedding: {str(e)}")


async def search_similar(query_text: str, top_k: int = 5) -> List[dict]:
    """Search for similar texts in Pinecone."""
    try:
        query_embedding = await get_embedding(query_text)
        idx = get_index()
        results = idx.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return results.matches
    except Exception as e:
        raise Exception(f"Error searching similar: {str(e)}")

