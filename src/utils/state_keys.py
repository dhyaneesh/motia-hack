"""Centralized state key management for consistent state access across steps."""

class StateKeys:
    """Utility class for generating consistent state keys."""
    
    @staticmethod
    def request_data(request_id: str) -> tuple[str, str]:
        """Get state key for request metadata."""
        return (f"request_{request_id}", "data")
    
    @staticmethod
    def concepts(request_id: str) -> tuple[str, str]:
        """Get state key for concepts."""
        return (f"request_{request_id}", "concepts")
    
    @staticmethod
    def embeddings(request_id: str) -> tuple[str, str]:
        """Get state key for embeddings."""
        return (f"request_{request_id}", "embeddings")
    
    @staticmethod
    def clusters(request_id: str) -> tuple[str, str]:
        """Get state key for clusters."""
        return (f"request_{request_id}", "clusters")
    
    @staticmethod
    def graph(request_id: str) -> tuple[str, str]:
        """Get state key for graph data."""
        return (f"request_{request_id}", "graph")
    
    @staticmethod
    def status(request_id: str) -> tuple[str, str]:
        """Get state key for request status."""
        return (f"request_{request_id}", "status")
    
    @staticmethod
    def learning_path(request_id: str) -> tuple[str, str]:
        """Get state key for learning path (study mode)."""
        return (f"request_{request_id}", "learning_path")
    
    @staticmethod
    def products(request_id: str) -> tuple[str, str]:
        """Get state key for products (shopping mode)."""
        return (f"request_{request_id}", "products")
    
    @staticmethod
    def parsed_shopping_query(request_id: str) -> tuple[str, str]:
        """Get state key for parsed shopping query (shopping mode)."""
        return (f"request_{request_id}", "parsed_query")
    
    @staticmethod
    def existing_graph(flow_type: str) -> tuple[str, str]:
        """Get state key for existing graph state (knowledge_graph, study_graph, shopping_graph)."""
        return (flow_type, "node_data")
    
    @staticmethod
    def existing_graph_nodes(flow_type: str) -> tuple[str, str]:
        """Get state key for existing graph nodes."""
        return (flow_type, "graph_nodes")
    
    @staticmethod
    def existing_graph_edges(flow_type: str) -> tuple[str, str]:
        """Get state key for existing graph edges."""
        return (flow_type, "graph_edges")
    
    @staticmethod
    def existing_embeddings(flow_type: str) -> tuple[str, str]:
        """Get state key for existing embeddings."""
        return (flow_type, "embeddings")

