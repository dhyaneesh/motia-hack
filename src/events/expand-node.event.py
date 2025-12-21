"""Event step for expanding a knowledge graph node with additional related content."""
import json
import os
from pydantic import BaseModel
from google import genai
from src.services.graph_service import graph_service
from src.services import tavily_service
from src.utils.state_keys import StateKeys
import networkx as nx
import numpy as np
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

# Configure Gemini API client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class ExpandNodeInput(BaseModel):
    request_id: str
    node_id: str

config = {
    "name": "ExpandNodeEvent",
    "type": "event",
    "description": "Expand a knowledge graph node by fetching additional related content",
    "subscribes": ["expand-node"],
    "emits": ["graph-ready"],
    "flows": ["knowledge-graph-flow"],
    "input": ExpandNodeInput.model_json_schema(),
    "infrastructure": {
        "handler": {
            "retries": 2,
            "timeout": 60,
            "backoffRate": 2
        }
    }
}

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

@with_timing("ExpandNode")
async def handler(input_data, context):
    """Expand node by searching for related content and adding to graph."""
    try:
        # Parse input
        data = ExpandNodeInput(**input_data)
        
        context.logger.info("Expanding node", {
            "request_id": data.request_id,
            "node_id": data.node_id
        })
        
        # Load graph data from state
        flow_type = "knowledge_graph"
        node_data = await context.state.get(*StateKeys.existing_graph(flow_type))
        graph_nodes = await context.state.get(*StateKeys.existing_graph_nodes(flow_type))
        
        # Unwrap if needed
        if isinstance(node_data, dict) and "data" in node_data and len(node_data) == 1:
            node_data = node_data.get("data", {})
        if isinstance(graph_nodes, dict) and "data" in graph_nodes:
            graph_nodes = graph_nodes.get("data", [])
        
        # Convert NumPy arrays
        node_data = convert_numpy_to_native(node_data)
        graph_nodes = convert_numpy_to_native(graph_nodes)
        
        # Restore graph service state
        if isinstance(node_data, dict) and len(node_data) > 0:
            graph_service.node_data = node_data
        if isinstance(graph_nodes, list) and len(graph_nodes) > 0:
            graph_service.graph = nx.Graph()
            for nid in graph_nodes:
                if nid in graph_service.node_data:
                    node_info = graph_service.node_data[nid]
                    if node_info is None or not isinstance(node_info, dict):
                        continue
                    
                    safe_node_info = {
                        "name": str(node_info.get("name", "Unknown")),
                        "description": str(node_info.get("description", "")),
                        "type": str(node_info.get("type", "concept")),
                        "cluster_id": str(node_info.get("cluster_id", ""))
                    }
                    
                    graph_service.graph.add_node(nid, **safe_node_info)
            
            # Restore edges
            stored_edges = await context.state.get(*StateKeys.existing_graph_edges(flow_type))
            if isinstance(stored_edges, dict) and "data" in stored_edges:
                stored_edges = stored_edges.get("data", [])
            stored_edges = convert_numpy_to_native(stored_edges)
            
            if isinstance(stored_edges, list) and len(stored_edges) > 0:
                for edge in stored_edges:
                    if isinstance(edge, dict):
                        source = edge.get("source")
                        target = edge.get("target")
                        if source and target and graph_service.graph.has_node(source) and graph_service.graph.has_node(target):
                            weight = edge.get("weight", 0.8)
                            edge_type = edge.get("type", "cluster")
                            graph_service.graph.add_edge(source, target, weight=weight, type=edge_type)
        
        # Get current node
        node = graph_service.get_node(data.node_id)
        if node is None:
            context.logger.warn("Node not found for expand", {
                "node_id": data.node_id,
                "available_nodes": list(graph_service.node_data.keys())[:10]
            })
            # Update status to failed
            status_group, status_key = StateKeys.status(data.request_id)
            await context.state.set(status_group, status_key, {
                "status": "failed",
                "error": f"Node not found: {data.node_id}",
                "stage": "expand_node"
            })
            return
        
        # Search for diverse knowledge sources
        search_queries = [
            f"{node['name']} latest research articles",
            f"{node['name']} detailed explanation guide"
        ]
        
        all_results = []
        for query in search_queries:
            try:
                results = await tavily_service.search(query, num_results=3)
                all_results.extend(results)
            except Exception as e:
                context.logger.info(f"Tavily search failed for {query}", {"error": str(e)})
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        new_results = unique_results[:5]
        
        # Extract knowledge nodes from articles
        article_texts = [r.get("text", "")[:800] for r in new_results[:3]]
        combined_text = "\n\n".join(article_texts)
        
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
                concept["references"] = new_results[:2]
            
        except Exception as e:
            context.logger.info("Failed to extract knowledge nodes from articles", {"error": str(e)})
            # Fallback: create knowledge nodes from article titles
            new_concepts = []
            for idx, result in enumerate(new_results[:3]):
                title = result.get("title", "Related Content")
                description = result.get("text", "")[:300]
                
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
                    "id": f"expanded_{data.node_id}_{idx}",
                    "name": title,
                    "type": topic_type,
                    "description": description,
                    "references": [result]
                })
        
        # Convert NumPy arrays
        new_concepts = convert_numpy_to_native(new_concepts)
        
        context.logger.info("Extracted concepts", {
            "num_concepts": len(new_concepts),
            "concept_types": [c.get("type") for c in new_concepts]
        })
        
        # Add to graph
        new_nodes, new_edges = graph_service.expand_node(data.node_id, new_concepts)
        
        context.logger.info("Graph expanded successfully", {
            "new_nodes_count": len(new_nodes),
            "new_edges_count": len(new_edges)
        })
        
        # Deduplicate - check if new nodes are too similar to existing ones
        # Get embeddings for existing nodes
        existing_embeddings = await context.state.get(*StateKeys.existing_embeddings(flow_type))
        if isinstance(existing_embeddings, dict) and "data" in existing_embeddings:
            existing_embeddings = existing_embeddings.get("data", {})
        existing_embeddings = convert_numpy_to_native(existing_embeddings) if existing_embeddings else {}
        
        # Generate embeddings for new concepts
        from src.services import embedding_service
        new_concept_texts = [f"{c['name']} {c.get('description', '')}" for c in new_concepts]
        new_embeddings = await embedding_service.get_embeddings(new_concept_texts)
        
        # Create embeddings dict for all nodes (existing + new)
        all_embeddings = existing_embeddings.copy()
        for i, concept in enumerate(new_concepts):
            concept_id = concept.get("id")
            if concept_id and i < len(new_embeddings):
                embedding = new_embeddings[i]
                if hasattr(embedding, 'tolist'):
                    embedding = embedding.tolist()
                all_embeddings[concept_id] = embedding
        
        # Run deduplication
        merge_map = graph_service.deduplicate_nodes(all_embeddings, similarity_threshold=0.85)
        
        if merge_map:
            context.logger.info("Deduplicated similar expanded nodes", {
                "request_id": data.request_id,
                "merged_count": len(merge_map),
                "merge_map": merge_map
            })
            
            # Remove merged embeddings
            for old_id in merge_map.keys():
                if old_id in all_embeddings:
                    del all_embeddings[old_id]
            
            # Update new_nodes to reflect merges
            merged_ids = set(merge_map.keys())
            new_nodes = [n for n in new_nodes if n["id"] not in merged_ids]
            
            # Update new_edges to reflect merges
            updated_edges = []
            for edge in new_edges:
                source = merge_map.get(edge["source"], edge["source"])
                target = merge_map.get(edge["target"], edge["target"])
                if source != target:  # Don't create self-loops
                    updated_edges.append({
                        **edge,
                        "source": source,
                        "target": target,
                        "id": f"{source}-{target}"
                    })
            new_edges = updated_edges
        
        # Save embeddings
        await context.state.set(*StateKeys.existing_embeddings(flow_type), all_embeddings)
        
        # Save updated graph data back to state
        edges_list = []
        for u, v, edge_data in graph_service.graph.edges(data=True):
            edges_list.append({
                "id": f"{u}-{v}",
                "source": u,
                "target": v,
                "type": edge_data.get("type", "cluster"),
                "visual_type": "smoothstep",
                "weight": edge_data.get("weight", 1.0)
            })
        
        await context.state.set(*StateKeys.existing_graph(flow_type), graph_service.node_data)
        await context.state.set(*StateKeys.existing_graph_nodes(flow_type), list(graph_service.graph.nodes()))
        await context.state.set(*StateKeys.existing_graph_edges(flow_type), edges_list)
        
        # Store expansion result in request state
        expand_group_id, expand_key = StateKeys.graph(data.request_id)
        await context.state.set(expand_group_id, expand_key, {
            "newNodes": new_nodes,
            "newEdges": new_edges
        })
        
        # Update status
        status_group, status_key = StateKeys.status(data.request_id)
        await context.state.set(status_group, status_key, {
            "status": "completed",
            "new_nodes": len(new_nodes),
            "new_edges": len(new_edges)
        })
        
        # Emit graph-ready
        await context.emit({
            "topic": "graph-ready",
            "data": {
                "request_id": data.request_id,
                "mode": "default"
            }
        })
        
    except Exception as e:
        context.logger.error("Error expanding node", {
            "error": str(e),
            "request_id": input_data.get("request_id", "unknown")
        })
        # Update status to failed
        request_id = input_data.get("request_id", "unknown")
        status_group, status_key = StateKeys.status(request_id)
        await context.state.set(status_group, status_key, {
            "status": "failed",
            "error": str(e),
            "stage": "expand_node"
        })
        raise

