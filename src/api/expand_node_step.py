from pydantic import BaseModel
from src.utils.state_keys import StateKeys
import uuid
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Response schemas
class ExpandNodeResponse(BaseModel):
    requestId: str
    status: str

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ExpandNode",
    "type": "api",
    "path": "/api/nodes/:nodeId/expand",
    "method": "POST",
    "description": "Expand a knowledge graph node by fetching additional related content from external sources. Discovers deeper subtopics, related concepts, tools, research, people, events, and applications using web search and LLM extraction.",
    "emits": ["expand-node"],
    "flows": ["knowledge-graph-flow"],
    "middleware": [create_timing_middleware("ExpandNode")],
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
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store initial request data
        data_group_id, data_key = StateKeys.request_data(request_id)
        await context.state.set(data_group_id, data_key, {
            "node_id": node_id
        })
        
        # Store initial status
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "processing",
            "stage": "expanding_node"
        })
        
        # Emit expand-node event
        await context.emit({
            "topic": "expand-node",
            "data": {
                "request_id": request_id,
                "node_id": node_id
            }
        })
        
        context.logger.info("Emitted expand-node event", {"request_id": request_id, "node_id": node_id})
        
        return {
            "status": 200,
            "body": {
                "requestId": request_id,
                "status": "processing"
            }
        }
    except Exception as e:
        context.logger.error("Error expanding node", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
        node_data = await context.state.get("knowledge_graph", "node_data")
        graph_nodes = await context.state.get("knowledge_graph", "graph_nodes")
        
        context.logger.info("Retrieved state data", {
            "node_data_type": str(type(node_data)),
            "graph_nodes_type": str(type(graph_nodes))
        })
        
        # Unwrap node_data if it has a "data" wrapper from Motia state
        if isinstance(node_data, dict) and "data" in node_data and len(node_data) == 1:
            node_data = node_data.get("data", {})
        
        # Unwrap graph_nodes if it has a "data" wrapper
        if isinstance(graph_nodes, dict) and "data" in graph_nodes:
            graph_nodes = graph_nodes.get("data", [])
        
        # Comprehensive NumPy array conversion function
        def convert_numpy_to_native(obj):
            """Recursively convert NumPy arrays to native Python types."""
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_to_native(value) for key, value in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_numpy_to_native(item) for item in obj]
            else:
                return obj
        
        # Convert all NumPy arrays in the data structures
        node_data = convert_numpy_to_native(node_data)
        graph_nodes = convert_numpy_to_native(graph_nodes)
        
        # Use isinstance checks first to avoid NumPy array boolean ambiguity
        if isinstance(node_data, dict) and len(node_data) > 0:
            graph_service.node_data = node_data
            context.logger.info("Loaded node data", {"num_nodes": len(node_data)})
        if isinstance(graph_nodes, list) and len(graph_nodes) > 0:
            # Rebuild graph structure
            import networkx as nx
            graph_service.graph = nx.Graph()
            for nid in graph_nodes:
                if nid in graph_service.node_data:
                    node_info = graph_service.node_data[nid]
                    if node_info is None or not isinstance(node_info, dict):
                        continue
                    
                    # Ensure all values are native Python types, not NumPy
                    safe_node_info = {
                        "name": str(node_info.get("name", "Unknown")),
                        "description": str(node_info.get("description", "")),
                        "type": str(node_info.get("type", "concept")),
                        "cluster_id": str(node_info.get("cluster_id", ""))
                    }
                    
                    graph_service.graph.add_node(nid, **safe_node_info)
            
            # Try to restore edges from state first
            stored_edges = await context.state.get("knowledge_graph", "graph_edges")
            if isinstance(stored_edges, dict) and "data" in stored_edges:
                stored_edges = stored_edges.get("data", [])
            
            # Convert NumPy arrays recursively
            stored_edges = convert_numpy_to_native(stored_edges)
            
            edges_restored = False
            if isinstance(stored_edges, list) and len(stored_edges) > 0:
                # Restore edges from stored state
                for edge in stored_edges:
                    if isinstance(edge, dict):
                        source = edge.get("source")
                        target = edge.get("target")
                        if source and target and graph_service.graph.has_node(source) and graph_service.graph.has_node(target):
                            weight = edge.get("weight", 0.8)
                            edge_type = edge.get("type", "cluster")
                            graph_service.graph.add_edge(source, target, weight=weight, type=edge_type)
                            edges_restored = True
            
            # If edges weren't restored, rebuild them from clusters
            if not edges_restored:
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
        
        # NOW get current node (after state is loaded)
        node = graph_service.get_node(node_id)
        if node is None:
            context.logger.info("Node not found for expand", {
                "node_id": node_id,
                "available_nodes": list(graph_service.node_data.keys())[:10]
            })
            return {
                "status": 404,
                "body": {"error": f"Node not found: {node_id}"}
            }
        
        # Search for diverse knowledge sources related to the node
        # Create multiple search queries for better coverage
        search_queries = [
            f"{node['name']} latest research articles",
            f"{node['name']} detailed explanation guide",
            f"{node['name']} case studies examples"
        ]
        
        all_results = []
        for query in search_queries[:2]:  # Use first 2 queries to get diverse results
            results = await tavily_service.search(query, num_results=3)
            all_results.extend(results)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        new_results = unique_results[:5]  # Keep top 5 unique results
        
        # Extract diverse knowledge nodes from articles
        article_texts = [r.get("text", "")[:800] for r in new_results[:3]]  # Limit text length
        combined_text = "\n\n".join(article_texts)
        
        # Use LLM to extract knowledge nodes from articles
        try:
            prompt = f"""You are analyzing content related to "{node['name']}" to discover deeper and more specific knowledge nodes.

Context: {node.get('description', '')}

Content from various sources:
{combined_text}

Extract 3-5 specific topics, subtopics, or related areas that go deeper into "{node['name']}".
These can be:
- Specific subtopics or specialized areas
- Related tools, frameworks, or technologies
- Key concepts or theories
- Important people or organizations
- Historical events or case studies
- Research areas or methodologies
- Practical applications

For each node, provide:
- A clear, specific name (e.g., "Graph Neural Networks" not just "Neural Networks")
- The type: "concept", "tool", "person", "event", "research", "application", or "organization"
- A detailed description explaining what this is and how it relates to "{node['name']}"

Return ONLY a valid JSON array:
[{{"id": "unique_id", "name": "specific topic name", "type": "concept|tool|person|event|research|application|organization", "description": "detailed description"}}]
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
            context.logger.info("Failed to extract knowledge nodes from articles", {"error": str(e)})
            # Fallback: create knowledge nodes from article titles and content
            new_concepts = []
            for idx, result in enumerate(new_results[:3]):
                title = result.get("title", "Related Content")
                description = result.get("text", "")[:300]
                
                # Try to determine type from title and content
                topic_type = "concept"
                title_lower = title.lower()
                
                if any(word in title_lower for word in ["tool", "framework", "library", "software", "platform"]):
                    topic_type = "tool"
                elif any(word in title_lower for word in ["research", "study", "paper", "findings"]):
                    topic_type = "research"
                elif any(word in title_lower for word in ["person", "founder", "inventor", "scientist", "author"]):
                    topic_type = "person"
                elif any(word in title_lower for word in ["event", "incident", "case", "scandal", "crisis"]):
                    topic_type = "event"
                elif any(word in title_lower for word in ["company", "organization", "institute", "agency"]):
                    topic_type = "organization"
                elif any(word in title_lower for word in ["application", "use case", "implementation"]):
                    topic_type = "application"
                
                new_concepts.append({
                    "id": f"expanded_{node_id}_{idx}",
                    "name": title,
                    "type": topic_type,
                    "description": description,
                    "references": [result]
                })
        
        # Convert any NumPy arrays in new_concepts before passing to graph service
        new_concepts = convert_numpy_to_native(new_concepts)
        
        context.logger.info("Extracted concepts", {
            "num_concepts": len(new_concepts),
            "concept_types": [c.get("type") for c in new_concepts]
        })
        
        # Add to graph
        try:
            new_nodes, new_edges = graph_service.expand_node(node_id, new_concepts)
            context.logger.info("Graph expanded successfully", {
                "new_nodes_count": len(new_nodes),
                "new_edges_count": len(new_edges)
            })
        except Exception as expand_error:
            context.logger.error("Failed to expand graph", {
                "error": str(expand_error),
                "error_type": type(expand_error).__name__,
                "node_id": node_id
            })
            raise
        
        # Save updated graph data back to state
        # Update edges list with new edges
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
            })
        
        await context.state.set("knowledge_graph", "node_data", graph_service.node_data)
        await context.state.set("knowledge_graph", "graph_nodes", list(graph_service.graph.nodes()))
        await context.state.set("knowledge_graph", "graph_edges", edges_list)
        
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

