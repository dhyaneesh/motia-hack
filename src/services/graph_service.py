import networkx as nx
from typing import Dict, List, Optional
import uuid
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class GraphService:
    """Service for building and managing knowledge graphs using NetworkX."""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.node_data = {}  # Store full node data separately
    
    def _build_knn_edges(self, embeddings: List[List[float]], node_ids: List[str], k: int = 2) -> List[tuple]:
        """
        Build edges using K-nearest neighbors based on embedding similarity.
        
        Args:
            embeddings: List of embedding vectors (one per node)
            node_ids: List of node IDs corresponding to embeddings
            k: Number of nearest neighbors to connect (default: 2)
            
        Returns:
            List of (source_id, target_id) tuples representing edges
        """
        if len(embeddings) != len(node_ids) or len(embeddings) < 2:
            return []
        
        # Convert to numpy array for efficient computation
        embedding_matrix = np.array(embeddings)
        
        # Calculate cosine similarity matrix
        similarity_matrix = cosine_similarity(embedding_matrix)
        
        # For each node, find its k nearest neighbors (excluding itself)
        edges = []
        edge_set = set()  # To deduplicate edges
        
        for i, node_id in enumerate(node_ids):
            # Get similarities for this node (excluding itself)
            similarities = similarity_matrix[i].copy()
            similarities[i] = -1  # Set self-similarity to -1 to exclude it
            
            # Find k nearest neighbors
            top_k_indices = np.argsort(similarities)[-k:][::-1]  # Get top k, descending order
            
            for neighbor_idx in top_k_indices:
                if neighbor_idx == i:  # Skip self
                    continue
                neighbor_id = node_ids[neighbor_idx]
                
                # Create edge tuple (normalized to avoid duplicates)
                edge = tuple(sorted([node_id, neighbor_id]))
                if edge not in edge_set:
                    edge_set.add(edge)
                    edges.append((node_id, neighbor_id))
        
        return edges
    
    def build_graph(self, clusters: List[Dict], concepts: List[Dict], embeddings: Optional[List[List[float]]] = None, k: int = 2, merge: bool = True) -> Dict:
        """Build knowledge graph from clusters and concepts.
        
        Args:
            clusters: List of cluster dictionaries
            concepts: List of concept dictionaries
            embeddings: Optional list of embedding vectors for KNN edge building
            k: Number of nearest neighbors when using embeddings (default: 2)
            merge: If True, merge with existing graph; if False, clear and rebuild (default: True)
        """
        # Only clear previous graph if not merging
        if not merge:
            self.graph = nx.Graph()
            self.node_data = {}
        
        # Create a concept lookup
        concept_lookup = {c.get("id"): c for c in concepts}
        
        # Collect all concept IDs in order
        all_concept_ids = []
        for cluster in clusters:
            for concept_id in cluster.get("conceptIds", []):
                if concept_id not in all_concept_ids and concept_lookup.get(concept_id):
                    all_concept_ids.append(concept_id)
        
        # Add nodes for each concept
        for cluster in clusters:
            cluster_id = cluster["id"]
            for concept_id in cluster.get("conceptIds", []):
                concept = concept_lookup.get(concept_id)
                if not concept:
                    continue
                
                # Store full node data
                self.node_data[concept_id] = {
                    "name": concept.get("name", "Unknown"),
                    "description": concept.get("description", ""),
                    "type": concept.get("type", "concept"),
                    "cluster_id": cluster_id,
                    "references": concept.get("references", [])
                }
                
                # Add node to graph
                self.graph.add_node(
                    concept_id,
                    name=concept.get("name", "Unknown"),
                    description=concept.get("description", ""),
                    type=concept.get("type", "concept"),
                    cluster_id=cluster_id
                )
        
        # Build edges using KNN if embeddings provided, otherwise use cluster-based edges
        if embeddings and len(embeddings) == len(concepts):
            # Create mapping from concept ID to embedding index (embeddings match concepts order)
            concept_id_to_idx = {c.get("id"): idx for idx, c in enumerate(concepts)}
            
            # Get embeddings and IDs for nodes that exist in the graph
            ordered_embeddings = []
            ordered_ids = []
            for concept_id in all_concept_ids:
                if concept_id in concept_id_to_idx and self.graph.has_node(concept_id):
                    ordered_embeddings.append(embeddings[concept_id_to_idx[concept_id]])
                    ordered_ids.append(concept_id)
            
            # Build KNN edges if we have enough nodes
            if len(ordered_embeddings) >= 2:
                knn_edges = self._build_knn_edges(ordered_embeddings, ordered_ids, k=k)
                
                # Add KNN edges to graph
                for source_id, target_id in knn_edges:
                    if self.graph.has_node(source_id) and self.graph.has_node(target_id):
                        self.graph.add_edge(source_id, target_id, weight=0.8, type="knn")
        else:
            # Fall back to cluster-based edges
            for cluster in clusters:
                concept_ids = cluster.get("conceptIds", [])
                # Connect each concept to others in the same cluster
                for i, concept_id1 in enumerate(concept_ids):
                    for concept_id2 in concept_ids[i+1:]:
                        if self.graph.has_node(concept_id1) and self.graph.has_node(concept_id2):
                            self.graph.add_edge(concept_id1, concept_id2, weight=0.8, type="cluster")
        
        # Calculate positions using spring layout (optimized iterations based on graph size)
        if len(self.graph.nodes()) > 0:
            # Reduce iterations for smaller graphs to speed up layout
            num_nodes = len(self.graph.nodes())
            iterations = min(50, max(20, num_nodes * 3))  # Adaptive: 20-50 iterations
            positions = nx.spring_layout(self.graph, k=2, iterations=iterations, seed=42)
        else:
            positions = {}
        
        return self._to_react_flow_format(positions)
    
    def _to_react_flow_format(self, positions: Dict, node_type: str = "conceptNode") -> Dict:
        """Convert NetworkX graph to React Flow format."""
        nodes = []
        for node_id, pos in positions.items():
            data = self.node_data.get(node_id, {})
            node_data = {
                "name": data.get("name", "Unknown"),
                "description": data.get("description", ""),
                "nodeType": data.get("type", "concept"),
                "clusterId": data.get("cluster_id", ""),
                "references": data.get("references", [])
            }
            
            # Add product-specific fields if present
            if data.get("type") == "product":
                node_data["imageUrl"] = data.get("image_url")
                node_data["price"] = data.get("price")
                node_data["rating"] = data.get("rating")
                node_data["retailer"] = data.get("retailer")
                node_data["url"] = data.get("url")
                node_data["specs"] = data.get("specs", {})
                node_data["reviewSummary"] = data.get("review_summary")
            
            # Add study-specific fields if present
            if "level" in data:
                node_data["level"] = data.get("level")
                node_data["prerequisites"] = data.get("prerequisites", [])
                node_data["learningPathPosition"] = data.get("learning_path_position")
            
            nodes.append({
                "id": node_id,
                "type": node_type,
                "position": {"x": pos[0] * 800, "y": pos[1] * 600},
                "data": node_data
            })
        
        edges = []
        for u, v, edge_data in self.graph.edges(data=True):
            edges.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": "smoothstep",  # React Flow visual type
                "weight": edge_data.get("weight", 1.0),
                "data": {
                    "edgeType": edge_data.get("type", "cluster")  # Store actual edge type in data for debugging/filtering
                }
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node data by ID. Tries multiple matching strategies."""
        # Direct lookup
        if node_id in self.node_data:
            data = self.node_data[node_id]
            return {
                "id": node_id,
                "name": data["name"],
                "description": data["description"],
                "type": data["type"],
                "cluster_id": data["cluster_id"],
                "references": data["references"]
            }
        
        # Try to find by name (case-insensitive, normalized)
        node_id_lower = node_id.lower().replace(' ', '_').replace('-', '_')
        for stored_id, data in self.node_data.items():
            stored_id_lower = stored_id.lower().replace(' ', '_').replace('-', '_')
            # Check if the requested ID matches the stored ID (normalized)
            if node_id_lower == stored_id_lower or node_id_lower in stored_id_lower or stored_id_lower in node_id_lower:
                return {
                    "id": stored_id,  # Return the actual stored ID
                    "name": data["name"],
                    "description": data["description"],
                    "type": data["type"],
                    "cluster_id": data["cluster_id"],
                    "references": data["references"]
                }
            # Also try matching by name
            name_lower = data.get("name", "").lower().replace(' ', '_').replace('-', '_')
            if node_id_lower == name_lower:
                return {
                    "id": stored_id,
                    "name": data["name"],
                    "description": data["description"],
                    "type": data["type"],
                    "cluster_id": data["cluster_id"],
                    "references": data["references"]
                }
        
        return None
    
    def get_related_nodes(self, node_id: str) -> List[Dict]:
        """Get nodes connected to the given node."""
        if node_id not in self.graph:
            return []
        
        related = []
        for neighbor_id in self.graph.neighbors(node_id):
            neighbor_data = self.node_data.get(neighbor_id)
            if neighbor_data:
                related.append({
                    "id": neighbor_id,
                    "name": neighbor_data["name"]
                })
        
        return related
    
    def expand_node(self, node_id: str, new_concepts: List[Dict]) -> tuple[List[Dict], List[Dict]]:
        """Add new concepts connected to an existing node."""
        if node_id not in self.graph:
            return [], []
        
        new_nodes = []
        new_edges = []
        
        # Get parent cluster_id safely (convert from NumPy if needed)
        try:
            parent_node_data = self.node_data.get(node_id, {})
            parent_cluster_id = parent_node_data.get("cluster_id", "")
            
            # Check type and convert if needed
            if isinstance(parent_cluster_id, np.ndarray):
                parent_cluster_id = parent_cluster_id.tolist()
            
            # Convert to string
            if isinstance(parent_cluster_id, list):
                parent_cluster_id = str(parent_cluster_id[0]) if parent_cluster_id else ""
            else:
                parent_cluster_id = str(parent_cluster_id) if parent_cluster_id else ""
        except Exception as e:
            print(f"Error getting parent_cluster_id: {e}, type: {type(self.node_data.get(node_id, {}).get('cluster_id'))}")
            parent_cluster_id = ""
        
        for concept in new_concepts:
            try:
                concept_id = concept.get("id", f"concept_{uuid.uuid4().hex[:8]}")
                
                # Ensure references is a list, not a NumPy array
                references = concept.get("references", [])
                if isinstance(references, np.ndarray):
                    references = references.tolist()
                
                # Add to node data
                self.node_data[concept_id] = {
                    "name": str(concept.get("name", "Unknown")),
                    "description": str(concept.get("description", "")),
                    "type": str(concept.get("type", "concept")),
                    "cluster_id": parent_cluster_id,
                    "references": references
                }
                
                # Add to graph
                self.graph.add_node(
                    concept_id,
                    name=str(concept.get("name", "Unknown")),
                    description=str(concept.get("description", "")),
                    type=str(concept.get("type", "concept")),
                    cluster_id=parent_cluster_id
                )
                
                # Connect to original node
                self.graph.add_edge(node_id, concept_id, weight=0.7, type="expanded")
            except Exception as e:
                print(f"Error processing concept {concept.get('name', 'unknown')}: {e}")
                continue
            
            # Calculate position relative to original node
            try:
                original_pos = None
                for n in self.graph.nodes():
                    if n == node_id:
                        # Get approximate position from existing nodes
                        if len(self.graph.nodes()) > 1:
                            num_nodes = len(self.graph.nodes())
                            iterations = min(20, max(10, num_nodes * 2))  # Faster for expansion
                            positions = nx.spring_layout(self.graph, k=2, iterations=iterations, seed=42)
                            original_pos = positions.get(node_id, (0, 0))
                        else:
                            original_pos = (0, 0)
                        break
                
                if original_pos is None:
                    original_pos = (0, 0)
                
                new_pos = {
                    "x": float(original_pos[0]) * 800 + 200,
                    "y": float(original_pos[1]) * 600 + 200
                }
            except Exception as e:
                print(f"Error calculating position: {e}")
                new_pos = {"x": 200, "y": 200}
            
            try:
                new_nodes.append({
                    "id": concept_id,
                    "type": "conceptNode",
                    "position": new_pos,
                    "data": {
                        "name": str(concept.get("name", "Unknown")),
                        "description": str(concept.get("description", "")),
                        "nodeType": str(concept.get("type", "concept")),
                        "clusterId": parent_cluster_id,
                        "references": references
                    }
                })
                
                new_edges.append({
                    "id": f"{node_id}-{concept_id}",
                    "source": node_id,
                    "target": concept_id,
                    "type": "smoothstep",
                    "weight": 0.7
                })
            except Exception as e:
                print(f"Error creating node/edge data structures: {e}")
                continue
        
        return new_nodes, new_edges
    
    def connect_cross_query_nodes(
        self, 
        new_node_ids: List[str], 
        new_embeddings: Dict[str, List[float]], 
        existing_embeddings: Dict[str, List[float]],
        similarity_threshold: float = 0.6,
        max_connections_per_node: int = 3
    ) -> List[Dict]:
        """
        Create edges between new nodes and existing nodes based on embedding similarity.
        
        Args:
            new_node_ids: List of node IDs from the current query
            new_embeddings: Dict mapping new node_id -> embedding vector
            existing_embeddings: Dict mapping existing node_id -> embedding vector
            similarity_threshold: Minimum cosine similarity to create an edge (default: 0.6)
            max_connections_per_node: Maximum number of connections per new node (default: 3)
            
        Returns:
            List of new edge dictionaries in React Flow format
        """
        if not new_node_ids or not new_embeddings or not existing_embeddings:
            return []
        
        new_edges = []
        
        # Convert embeddings to numpy arrays for efficient computation
        for new_node_id in new_node_ids:
            if new_node_id not in new_embeddings:
                continue
            
            new_embedding = np.array(new_embeddings[new_node_id])
            similarities = []
            
            # Calculate similarity with all existing nodes
            for existing_node_id, existing_embedding in existing_embeddings.items():
                # Skip if nodes are the same (shouldn't happen, but defensive)
                if new_node_id == existing_node_id:
                    continue
                
                # Skip if edge already exists
                if self.graph.has_edge(new_node_id, existing_node_id):
                    continue
                
                # Calculate cosine similarity
                existing_emb = np.array(existing_embedding)
                similarity = cosine_similarity([new_embedding], [existing_emb])[0][0]
                
                if similarity >= similarity_threshold:
                    similarities.append((existing_node_id, similarity))
            
            # Sort by similarity (descending) and take top connections
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_connections = similarities[:max_connections_per_node]
            
            # Create edges for top connections
            for existing_node_id, similarity in top_connections:
                # Ensure both nodes exist in the graph
                if not self.graph.has_node(new_node_id) or not self.graph.has_node(existing_node_id):
                    continue
                
                # Add edge to graph
                self.graph.add_edge(
                    new_node_id, 
                    existing_node_id, 
                    weight=float(similarity), 
                    type="cross-query"
                )
                
                # Create edge data for React Flow
                new_edges.append({
                    "id": f"{new_node_id}-{existing_node_id}",
                    "source": new_node_id,
                    "target": existing_node_id,
                    "type": "smoothstep",
                    "weight": float(similarity)
                })
        
        return new_edges
    
    def build_product_graph(self, clusters: List[Dict], products: List[Dict], embeddings: Optional[List[List[float]]] = None, k: int = 2) -> Dict:
        """Build knowledge graph from product clusters.
        
        Args:
            clusters: List of cluster dictionaries
            products: List of product dictionaries
            embeddings: Optional list of embedding vectors for KNN edge building
            k: Number of nearest neighbors when using embeddings (default: 2)
        """
        # Clear previous graph
        self.graph = nx.Graph()
        self.node_data = {}
        
        # Create a product lookup
        product_lookup = {p.get("id"): p for p in products}
        
        # Collect all product IDs in order
        all_product_ids = []
        for cluster in clusters:
            for product_id in cluster.get("productIds", []):
                if product_id not in all_product_ids and product_lookup.get(product_id):
                    all_product_ids.append(product_id)
        
        # Add nodes for each product
        for cluster in clusters:
            cluster_id = cluster["id"]
            for product_id in cluster.get("productIds", []):
                product = product_lookup.get(product_id)
                if not product:
                    continue
                
                # Store full node data with product-specific fields
                self.node_data[product_id] = {
                    "name": product.get("name", "Unknown"),
                    "description": product.get("description", ""),
                    "type": "product",
                    "cluster_id": cluster_id,
                    "image_url": product.get("image_url"),
                    "price": product.get("price"),
                    "rating": product.get("rating"),
                    "retailer": product.get("retailer"),
                    "url": product.get("url"),
                    "specs": product.get("specs", {}),
                    "review_summary": product.get("review_summary"),
                    "references": product.get("references", [])
                }
                
                # Add node to graph
                self.graph.add_node(
                    product_id,
                    name=product.get("name", "Unknown"),
                    description=product.get("description", ""),
                    type="product",
                    cluster_id=cluster_id,
                    image_url=product.get("image_url"),
                    price=product.get("price"),
                    rating=product.get("rating")
                )
        
        # Build edges using KNN if embeddings provided, otherwise use cluster-based edges
        if embeddings and len(embeddings) == len(products):
            # Create mapping from product ID to embedding index (embeddings match products order)
            product_id_to_idx = {p.get("id"): idx for idx, p in enumerate(products)}
            
            # Get embeddings and IDs for nodes that exist in the graph
            ordered_embeddings = []
            ordered_ids = []
            for product_id in all_product_ids:
                if product_id in product_id_to_idx and self.graph.has_node(product_id):
                    ordered_embeddings.append(embeddings[product_id_to_idx[product_id]])
                    ordered_ids.append(product_id)
            
            # Build KNN edges if we have enough nodes
            if len(ordered_embeddings) >= 2:
                knn_edges = self._build_knn_edges(ordered_embeddings, ordered_ids, k=k)
                
                # Add KNN edges to graph
                for source_id, target_id in knn_edges:
                    if self.graph.has_node(source_id) and self.graph.has_node(target_id):
                        self.graph.add_edge(source_id, target_id, weight=0.8, type="knn")
        else:
            # Fall back to cluster-based edges
            for cluster in clusters:
                product_ids = cluster.get("productIds", [])
                # Connect each product to others in the same cluster
                for i, product_id1 in enumerate(product_ids):
                    for product_id2 in product_ids[i+1:]:
                        if self.graph.has_node(product_id1) and self.graph.has_node(product_id2):
                            self.graph.add_edge(product_id1, product_id2, weight=0.8, type="cluster")
        
        # Calculate positions using spring layout
        if len(self.graph.nodes()) > 0:
            positions = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        else:
            positions = {}
        
        return self._to_react_flow_format(positions, node_type="productNode")
    
    def build_study_graph(self, clusters: List[Dict], concepts: List[Dict], embeddings: Optional[List[List[float]]] = None, k: int = 2) -> Dict:
        """Build knowledge graph from study concepts with hierarchy levels.
        
        Args:
            clusters: List of cluster dictionaries
            concepts: List of concept dictionaries
            embeddings: Optional list of embedding vectors for KNN edge building
            k: Number of nearest neighbors when using embeddings (default: 2)
        """
        # Clear previous graph
        self.graph = nx.Graph()
        self.node_data = {}
        
        # Create a concept lookup
        concept_lookup = {c.get("id"): c for c in concepts}
        
        # Collect all concept IDs in order
        all_concept_ids = []
        for cluster in clusters:
            for concept_id in cluster.get("conceptIds", []):
                if concept_id not in all_concept_ids and concept_lookup.get(concept_id):
                    all_concept_ids.append(concept_id)
        
        # Add nodes for each concept
        for cluster in clusters:
            cluster_id = cluster["id"]
            for concept_id in cluster.get("conceptIds", []):
                concept = concept_lookup.get(concept_id)
                if not concept:
                    continue
                
                # Store full node data with study-specific fields
                self.node_data[concept_id] = {
                    "name": concept.get("name", "Unknown"),
                    "description": concept.get("description", ""),
                    "type": concept.get("type", "concept"),
                    "cluster_id": cluster_id,
                    "level": concept.get("level", 2),  # 1=Beginner, 2=Intermediate, 3=Advanced
                    "prerequisites": concept.get("prerequisites", []),
                    "learning_path_position": concept.get("learning_path_position"),
                    "references": concept.get("references", [])
                }
                
                # Add node to graph
                self.graph.add_node(
                    concept_id,
                    name=concept.get("name", "Unknown"),
                    description=concept.get("description", ""),
                    type=concept.get("type", "concept"),
                    cluster_id=cluster_id,
                    level=concept.get("level", 2),
                    prerequisites=concept.get("prerequisites", [])
                )
        
        # Build edges using KNN if embeddings provided, otherwise use cluster-based edges
        if embeddings and len(embeddings) == len(concepts):
            # Create mapping from concept ID to embedding index (embeddings match concepts order)
            concept_id_to_idx = {c.get("id"): idx for idx, c in enumerate(concepts)}
            
            # Get embeddings and IDs for nodes that exist in the graph
            ordered_embeddings = []
            ordered_ids = []
            for concept_id in all_concept_ids:
                if concept_id in concept_id_to_idx and self.graph.has_node(concept_id):
                    ordered_embeddings.append(embeddings[concept_id_to_idx[concept_id]])
                    ordered_ids.append(concept_id)
            
            # Build KNN edges if we have enough nodes
            if len(ordered_embeddings) >= 2:
                knn_edges = self._build_knn_edges(ordered_embeddings, ordered_ids, k=k)
                
                # Add KNN edges to graph
                for source_id, target_id in knn_edges:
                    if self.graph.has_node(source_id) and self.graph.has_node(target_id):
                        self.graph.add_edge(source_id, target_id, weight=0.8, type="knn")
        else:
            # Fall back to cluster-based edges
            for cluster in clusters:
                concept_ids = cluster.get("conceptIds", [])
                for i, concept_id1 in enumerate(concept_ids):
                    for concept_id2 in concept_ids[i+1:]:
                        if self.graph.has_node(concept_id1) and self.graph.has_node(concept_id2):
                            self.graph.add_edge(concept_id1, concept_id2, weight=0.8, type="cluster")
        
        # Add prerequisite edges (always added, regardless of KNN/cluster edges)
        for concept_id, data in self.node_data.items():
            prerequisites = data.get("prerequisites", [])
            for prereq_id in prerequisites:
                if self.graph.has_node(prereq_id) and self.graph.has_node(concept_id):
                    self.graph.add_edge(prereq_id, concept_id, weight=0.9, type="prerequisite")
        
        # Calculate positions using spring layout
        if len(self.graph.nodes()) > 0:
            positions = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        else:
            positions = {}
        
        return self._to_react_flow_format(positions, node_type="conceptCard")


# Global instance
graph_service = GraphService()

