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
    
    # For very small sets, skip clustering and return single cluster
    if len(concepts) <= 3:
        return [{
            "id": "0",
            "label": "Main",
            "conceptIds": [c.get("id", f"concept_{i}") for i, c in enumerate(concepts)],
            "concepts": concepts
        }]
    
    try:
        # Convert to numpy array
        embedding_matrix = np.array(embeddings)
        
        # Optimized HDBSCAN parameters for speed
        # Reduced min_cluster_size for smaller datasets, increased epsilon for faster clustering
        min_cluster_size = max(2, len(concepts) // 4)  # Adaptive cluster size
        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric='cosine',
            cluster_selection_epsilon=0.4,  # Increased from 0.3 for faster clustering
            min_samples=1  # Reduced for faster processing
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
        
        # Generate cluster labels using LLM (parallelized)
        import asyncio
        async def generate_label(cluster):
            if len(cluster["concepts"]) > 0:
                return await generate_cluster_label(cluster["concepts"])
            else:
                return "Unnamed Cluster"
        
        # Generate all labels in parallel
        label_tasks = [generate_label(cluster) for cluster in clusters.values()]
        labels = await asyncio.gather(*label_tasks)
        
        # Assign labels to clusters
        for cluster, label in zip(clusters.values(), labels):
            cluster["label"] = label
        
        return list(clusters.values())
    except Exception as e:
        raise Exception(f"Error clustering concepts: {str(e)}")

