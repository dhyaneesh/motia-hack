"""Study mode API endpoint for concept learning with hierarchy and learning paths."""
from pydantic import BaseModel
from typing import List, Dict
from src.services import llm_service, tavily_service, embedding_service, clustering_service
from src.services.study_service import assign_concept_level, build_learning_path, identify_prerequisites
from src.services.graph_service import graph_service
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

# Request/Response schemas
class StudyRequest(BaseModel):
    question: str

class StudyResponse(BaseModel):
    answer: str
    graph: Dict
    clusters: List[Dict]
    learning_path: List[Dict]

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "StudyAPI",
    "type": "api",
    "path": "/api/study",
    "method": "POST",
    "description": "Process a study question and return concepts organized by hierarchy levels with learning paths and prerequisites.",
    "emits": [],
    "flows": ["study-flow"],
    "middleware": [create_timing_middleware("StudyAPI")],
    "bodySchema": StudyRequest.model_json_schema(),
    "responseSchema": {
        200: StudyResponse.model_json_schema(),
        400: ErrorResponse.model_json_schema(),
        500: ErrorResponse.model_json_schema()
    }
}

async def handler(req, context):
    try:
        body = req.get("body", {})
        question = body.get("question", "")
        
        if not question:
            return {
                "status": 400,
                "body": {"error": "Question is required"}
            }
        
        context.logger.info("Processing study question", {"question": question})
        
        # 1. Generate answer using Gemini
        answer = await llm_service.generate_answer(question)
        context.logger.info("Generated answer", {"answer_length": len(answer)})
        
        # 2. Extract concepts from question and answer
        concepts = await llm_service.extract_concepts(question, answer)
        context.logger.info("Extracted concepts", {"concept_count": len(concepts)})
        
        # 3. Search Tavily for each concept to get references
        for concept in concepts:
            try:
                search_results = await tavily_service.search(concept["name"], num_results=3)
                concept["references"] = search_results
            except Exception as e:
                context.logger.info(f"Tavily search failed for {concept['name']}", {"error": str(e)})
                concept["references"] = []
        
        # 4. Assign hierarchy levels to concepts
        for concept in concepts:
            try:
                level = await assign_concept_level(concept)
                concept["level"] = level
            except Exception as e:
                context.logger.info(f"Failed to assign level for {concept['name']}", {"error": str(e)})
                concept["level"] = 2  # Default to intermediate
        
        context.logger.info("Assigned concept levels", {
            "beginner": sum(1 for c in concepts if c.get("level") == 1),
            "intermediate": sum(1 for c in concepts if c.get("level") == 2),
            "advanced": sum(1 for c in concepts if c.get("level") == 3)
        })
        
        # 5. Identify prerequisites for each concept
        for concept in concepts:
            try:
                prerequisites = await identify_prerequisites(concept, concepts)
                concept["prerequisites"] = prerequisites
            except Exception as e:
                context.logger.info(f"Failed to identify prerequisites for {concept['name']}", {"error": str(e)})
                concept["prerequisites"] = []
        
        # 6. Build learning path
        learning_path = await build_learning_path(concepts)
        context.logger.info("Built learning path", {"path_length": len(learning_path)})
        
        # 7. Generate embeddings for clustering
        embedding_texts = [f"{c['name']} {c.get('description', '')}" for c in concepts]
        embeddings = await embedding_service.get_embeddings(embedding_texts)
        context.logger.info("Generated embeddings", {"embedding_count": len(embeddings)})
        
        # 8. Cluster concepts by similarity
        clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        context.logger.info("Clustered concepts", {"cluster_count": len(clusters)})
        
        # 9. Build graph with level information using KNN edges
        graph = graph_service.build_study_graph(clusters, concepts, embeddings=embeddings, k=2)
        context.logger.info("Built study graph", {
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"])
        })
        
        # 10. Store graph data in Motia state for persistence
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
        
        await context.state.set("study_graph", "node_data", graph_service.node_data)
        await context.state.set("study_graph", "graph_nodes", node_ids_list)
        await context.state.set("study_graph", "graph_edges", edges_list)
        
        return {
            "status": 200,
            "body": {
                "answer": answer,
                "graph": graph,
                "clusters": clusters,
                "learning_path": learning_path
            }
        }
    except Exception as e:
        context.logger.error("Error processing study request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }
