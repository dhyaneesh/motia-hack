import os
import json
from pydantic import BaseModel
from google import genai
from src.services.graph_service import graph_service
from src.services import exa_service, llm_service

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Response schemas
class ExpandNodeResponse(BaseModel):
    newNodes: list
    newEdges: list

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ExpandNode",
    "type": "api",
    "path": "/api/nodes/:nodeId/expand",
    "method": "POST",
    "description": "Expand a knowledge graph node by fetching additional related concepts from external sources. Uses Exa AI to search for related content and extracts new concepts using LLM.",
    "emits": [],
    "flows": ["knowledge-graph-flow"],
    "responseSchema": {
        200: ExpandNodeResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        404: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        path_params = req.get("pathParams", {})
        node_id = path_params.get("nodeId")
        if not node_id:
            return {
                "status": 400,
                "body": {"error": "Node ID is required"}
            }
        
        context.logger.info("Expanding node", {"node_id": node_id})
        
        # Get current node
        node = graph_service.get_node(node_id)
        if not node:
            return {
                "status": 404,
                "body": {"error": "Node not found"}
            }
        
        # Search for more related content using Exa
        search_query = f"{node['name']} {node['description']}"
        new_results = await exa_service.search(search_query, num_results=5)
        
        # Extract new concepts from articles
        article_texts = [r.get("text", "")[:1000] for r in new_results[:3]]  # Limit text length
        combined_text = "\n\n".join(article_texts)
        
        # Use LLM to extract concepts from articles
        try:
            prompt = f"""Extract key concepts from these articles related to "{node['name']}":
            {combined_text}
            
            Return ONLY a valid JSON array:
            [{{"id": "unique_id", "name": "concept name", "type": "concept|entity|event|person", "description": "brief description"}}]
            """
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            new_concepts = json.loads(text)
            
            # Attach references to new concepts
            for concept in new_concepts:
                concept["references"] = new_results[:2]  # Attach first 2 references
            
        except Exception as e:
            context.logger.info("Failed to extract concepts from articles", {"error": str(e)})
            # Fallback: create concepts from article titles
            new_concepts = []
            for idx, result in enumerate(new_results[:3]):
                new_concepts.append({
                    "id": f"expanded_{node_id}_{idx}",
                    "name": result.get("title", "Related Article"),
                    "type": "concept",
                    "description": result.get("text", "")[:200],
                    "references": [result]
                })
        
        # Load graph data from Motia state first
        node_data = await context.state.get("knowledge_graph", "node_data")
        graph_nodes = await context.state.get("knowledge_graph", "graph_nodes")
        
        if node_data:
            graph_service.node_data = node_data
        if graph_nodes:
            # Rebuild graph structure
            import networkx as nx
            graph_service.graph = nx.Graph()
            for nid in graph_nodes:
                if nid in graph_service.node_data:
                    node_info = graph_service.node_data[nid]
                    if node_info is None or not isinstance(node_info, dict):
                        continue
                    graph_service.graph.add_node(
                        nid,
                        name=node_info.get("name", "Unknown"),
                        description=node_info.get("description", ""),
                        type=node_info.get("type", "concept"),
                        cluster_id=node_info.get("cluster_id", "")
                    )
            
            # Rebuild edges
            cluster_nodes = {}
            for nid, data in graph_service.node_data.items():
                if data is None or not isinstance(data, dict):
                    continue
                cluster_id = data.get("cluster_id", "")
                if cluster_id not in cluster_nodes:
                    cluster_nodes[cluster_id] = []
                cluster_nodes[cluster_id].append(nid)
            
            for cluster_id, node_ids in cluster_nodes.items():
                for i, nid1 in enumerate(node_ids):
                    for nid2 in node_ids[i+1:]:
                        if graph_service.graph.has_node(nid1) and graph_service.graph.has_node(nid2):
                            graph_service.graph.add_edge(nid1, nid2, weight=0.8, type="cluster")
        
        # Add to graph
        new_nodes, new_edges = graph_service.expand_node(node_id, new_concepts)
        
        # Save updated graph data back to state
        await context.state.set("knowledge_graph", "node_data", graph_service.node_data)
        await context.state.set("knowledge_graph", "graph_nodes", list(graph_service.graph.nodes()))
        
        context.logger.info("Expanded node", {
            "node_id": node_id,
            "new_nodes": len(new_nodes),
            "new_edges": len(new_edges)
        })
        
        return {
            "status": 200,
            "body": {
                "newNodes": new_nodes,
                "newEdges": new_edges
            }
        }
    except Exception as e:
        context.logger.error("Error expanding node", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

