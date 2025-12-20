import networkx as nx
from typing import Dict, List, Optional
import uuid


class GraphService:
    """Service for building and managing knowledge graphs using NetworkX."""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.node_data = {}  # Store full node data separately
    
    def build_graph(self, clusters: List[Dict], concepts: List[Dict]) -> Dict:
        """Build knowledge graph from clusters and concepts."""
        # Clear previous graph
        self.graph = nx.Graph()
        self.node_data = {}
        
        # Create a concept lookup
        concept_lookup = {c.get("id"): c for c in concepts}
        
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
        
        # Add edges within clusters (connect concepts in same cluster)
        for cluster in clusters:
            concept_ids = cluster.get("conceptIds", [])
            # Connect each concept to others in the same cluster
            for i, concept_id1 in enumerate(concept_ids):
                for concept_id2 in concept_ids[i+1:]:
                    if self.graph.has_node(concept_id1) and self.graph.has_node(concept_id2):
                        self.graph.add_edge(concept_id1, concept_id2, weight=0.8, type="cluster")
        
        # Calculate positions using spring layout
        if len(self.graph.nodes()) > 0:
            positions = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
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
                "type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
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
        
        for concept in new_concepts:
            concept_id = concept.get("id", f"concept_{uuid.uuid4().hex[:8]}")
            
            # Add to node data
            self.node_data[concept_id] = {
                "name": concept.get("name", "Unknown"),
                "description": concept.get("description", ""),
                "type": concept.get("type", "concept"),
                "cluster_id": self.node_data[node_id]["cluster_id"],
                "references": concept.get("references", [])
            }
            
            # Add to graph
            self.graph.add_node(
                concept_id,
                name=concept.get("name", "Unknown"),
                description=concept.get("description", ""),
                type=concept.get("type", "concept"),
                cluster_id=self.node_data[node_id]["cluster_id"]
            )
            
            # Connect to original node
            self.graph.add_edge(node_id, concept_id, weight=0.7, type="expanded")
            
            # Calculate position relative to original node
            original_pos = None
            for n in self.graph.nodes():
                if n == node_id:
                    # Get approximate position from existing nodes
                    if len(self.graph.nodes()) > 1:
                        positions = nx.spring_layout(self.graph, k=2, iterations=20, seed=42)
                        original_pos = positions.get(node_id, (0, 0))
                    else:
                        original_pos = (0, 0)
                    break
            
            new_pos = {
                "x": (original_pos[0] if original_pos else 0) * 800 + 200,
                "y": (original_pos[1] if original_pos else 0) * 600 + 200
            }
            
            new_nodes.append({
                "id": concept_id,
                "type": "conceptNode",
                "position": new_pos,
                "data": {
                    "name": concept.get("name", "Unknown"),
                    "description": concept.get("description", ""),
                    "nodeType": concept.get("type", "concept"),
                    "clusterId": self.node_data[node_id]["cluster_id"],
                    "references": concept.get("references", [])
                }
            })
            
            new_edges.append({
                "id": f"{node_id}-{concept_id}",
                "source": node_id,
                "target": concept_id,
                "type": "smoothstep",
                "weight": 0.7
            })
        
        return new_nodes, new_edges
    
    def build_product_graph(self, clusters: List[Dict], products: List[Dict]) -> Dict:
        """Build knowledge graph from product clusters."""
        # Clear previous graph
        self.graph = nx.Graph()
        self.node_data = {}
        
        # Create a product lookup
        product_lookup = {p.get("id"): p for p in products}
        
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
        
        # Add edges within clusters (connect products in same cluster)
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
    
    def build_study_graph(self, clusters: List[Dict], concepts: List[Dict]) -> Dict:
        """Build knowledge graph from study concepts with hierarchy levels."""
        # Clear previous graph
        self.graph = nx.Graph()
        self.node_data = {}
        
        # Create a concept lookup
        concept_lookup = {c.get("id"): c for c in concepts}
        
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
        
        # Add edges within clusters
        for cluster in clusters:
            concept_ids = cluster.get("conceptIds", [])
            for i, concept_id1 in enumerate(concept_ids):
                for concept_id2 in concept_ids[i+1:]:
                    if self.graph.has_node(concept_id1) and self.graph.has_node(concept_id2):
                        self.graph.add_edge(concept_id1, concept_id2, weight=0.8, type="cluster")
        
        # Add prerequisite edges
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

