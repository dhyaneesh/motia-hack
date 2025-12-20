"""Shopping mode API endpoint for product search and visualization."""
from pydantic import BaseModel
from typing import List, Dict, Optional
from src.services import serpapi_service, product_service, embedding_service, clustering_service
from src.services.graph_service import graph_service

# Request/Response schemas
class ShoppingRequest(BaseModel):
    query: str
    num_results: int = 10

class ShoppingResponse(BaseModel):
    products: List[Dict]
    graph: Dict
    clusters: List[Dict]

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ShoppingAPI",
    "type": "api",
    "path": "/api/shopping",
    "method": "POST",
    "description": "Search for products and return an interactive product graph visualization with images, prices, ratings, and specifications.",
    "emits": [],
    "flows": ["shopping-flow"],
    "bodySchema": ShoppingRequest.model_json_schema(),
    "responseSchema": {
        200: ShoppingResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        body = req.get("body", {})
        query = body.get("query", "")
        num_results = body.get("num_results", 10)
        
        if not query:
            return {
                "status": 400,
                "body": {"error": "Query is required"}
            }
        
        context.logger.info("Processing shopping query", {"query": query, "num_results": num_results})
        
        # 1. Search products via SerpAPI
        products = await serpapi_service.search_products(query, num_results)
        context.logger.info("Found products", {"product_count": len(products)})
        
        if not products:
            return {
                "status": 200,
                "body": {
                    "products": [],
                    "graph": {"nodes": [], "edges": []},
                    "clusters": []
                }
            }
        
        # 2. Extract specs and summarize reviews for each product
        for product in products:
            try:
                # Extract specs from description
                if product.get("description"):
                    specs = await product_service.extract_product_specs(product["description"])
                    product["specs"] = specs
                
                # For now, use description as review summary placeholder
                # In production, you'd fetch actual reviews from SerpAPI or another source
                if product.get("description"):
                    product["review_summary"] = product["description"][:200] + "..."
                else:
                    product["review_summary"] = "No reviews available"
                
                # Ensure source link is present
                if product.get("url"):
                    product["references"] = [{
                        "id": product.get("id", ""),
                        "url": product["url"],
                        "title": product.get("name", "Product"),
                        "text": product.get("description", "")
                    }]
                else:
                    product["references"] = []
                    
            except Exception as e:
                context.logger.info(f"Failed to process product {product.get('id')}", {"error": str(e)})
                product["specs"] = {}
                product["review_summary"] = "No reviews available"
                product["references"] = []
        
        # 3. Generate embeddings for visual similarity
        product_texts = [
            f"{p.get('name', '')} {p.get('description', '')}" 
            for p in products
        ]
        embeddings = await embedding_service.get_embeddings(product_texts)
        context.logger.info("Generated embeddings", {"embedding_count": len(embeddings)})
        
        # 4. Cluster products by similarity
        clusters = await product_service.cluster_products_by_similarity(products)
        context.logger.info("Clustered products", {"cluster_count": len(clusters)})
        
        # 5. Build graph with product nodes
        graph = graph_service.build_product_graph(clusters, products)
        context.logger.info("Built product graph", {
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"])
        })
        
        # 6. Store graph data in Motia state for persistence
        node_ids_list = list(graph_service.graph.nodes())
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
            })
        
        await context.state.set("shopping_graph", "node_data", graph_service.node_data)
        await context.state.set("shopping_graph", "graph_nodes", node_ids_list)
        await context.state.set("shopping_graph", "graph_edges", edges_list)
        
        return {
            "status": 200,
            "body": {
                "products": products,
                "graph": graph,
                "clusters": clusters
            }
        }
    except Exception as e:
        context.logger.error("Error processing shopping request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
