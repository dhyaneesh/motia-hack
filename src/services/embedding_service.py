import os
from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone
from typing import List

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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
        result = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        # New API returns embeddings (plural) - extract values from ContentEmbedding objects
        if hasattr(result, 'embeddings'):
            embeddings = result.embeddings
            # If it's a list, get the first embedding and extract its values
            if isinstance(embeddings, list) and len(embeddings) > 0:
                embedding_obj = embeddings[0]
                # Extract values from ContentEmbedding object
                if hasattr(embedding_obj, 'values'):
                    return list(embedding_obj.values)
                elif hasattr(embedding_obj, 'embedding'):
                    return list(embedding_obj.embedding)
                else:
                    # Try to convert directly if it's already a list
                    return list(embedding_obj) if hasattr(embedding_obj, '__iter__') else [embedding_obj]
            # If it's a single embedding object
            elif hasattr(embeddings, 'values'):
                return list(embeddings.values)
            elif hasattr(embeddings, 'embedding'):
                return list(embeddings.embedding)
            else:
                return list(embeddings) if hasattr(embeddings, '__iter__') else [embeddings]
        # Fallback to embedding (singular) for backward compatibility
        elif hasattr(result, 'embedding'):
            embedding = result.embedding
            if hasattr(embedding, 'values'):
                return list(embedding.values)
            elif hasattr(embedding, '__iter__'):
                return list(embedding)
            else:
                return [embedding]
        else:
            raise Exception("Unexpected embedding result format")
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

