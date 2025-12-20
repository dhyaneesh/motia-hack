import os
import json
import google.generativeai as genai
from src.services.graph_service import graph_service
from src.services import exa_service, llm_service

config = {
    "name": "ExpandNode",
    "type": "api",
    "path": "/api/nodes/:nodeId/expand",
    "method": "POST",
    "description": "Expand a node to fetch more related concepts",
    "emits": [],
    "flows": ["knowledge-graph-flow"]
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
            
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
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
            context.logger.warning("Failed to extract concepts from articles", {"error": str(e)})
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
        
        # Add to graph
        new_nodes, new_edges = graph_service.expand_node(node_id, new_concepts)
        
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

