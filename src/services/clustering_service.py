import numpy as np
from sklearn.cluster import HDBSCAN
from typing import List, Dict
from .llm_service import generate_cluster_label


async def cluster_concepts(embeddings: List[List[float]], concepts: List[Dict]) -> List[Dict]:
    """Cluster concepts by semantic similarity using HDBSCAN."""
    if len(concepts) < 2:
        return [{
            "id": "0",
            "label": "Main",
            "conceptIds": [c.get("id", f"concept_{i}") for i, c in enumerate(concepts)]
        }]
    
    try:
        # Convert to numpy array
        embedding_matrix = np.array(embeddings)
        
        # Perform HDBSCAN clustering
        clusterer = HDBSCAN(
            min_cluster_size=2,
            metric='cosine',
            cluster_selection_epsilon=0.3
        )
        labels = clusterer.fit_predict(embedding_matrix)
        
        # Group concepts by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label == -1:  # Noise point
                cluster_id = f"noise_{idx}"
            else:
                cluster_id = str(label)
            
            if cluster_id not in clusters:
                clusters[cluster_id] = {
                    "id": cluster_id,
                    "conceptIds": [],
                    "concepts": []
                }
            
            concept_id = concepts[idx].get("id", f"concept_{idx}")
            clusters[cluster_id]["conceptIds"].append(concept_id)
            clusters[cluster_id]["concepts"].append(concepts[idx])
        
        # Generate cluster labels using LLM
        for cluster in clusters.values():
            if len(cluster["concepts"]) > 0:
                cluster["label"] = await generate_cluster_label(cluster["concepts"])
            else:
                cluster["label"] = "Unnamed Cluster"
        
        return list(clusters.values())
    except Exception as e:
        raise Exception(f"Error clustering concepts: {str(e)}")

