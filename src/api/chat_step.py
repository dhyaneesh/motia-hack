import os
from pydantic import BaseModel
from src.services import llm_service, exa_service, embedding_service, clustering_service
from src.services.graph_service import graph_service

# Request/Response schemas
class ChatRequest(BaseModel):
    question: str
    context: dict = {}

class ChatResponse(BaseModel):
    answer: str
    graph: dict
    clusters: list

class ErrorResponse(BaseModel):
    error: str

config = {
    "name": "ChatAPI",
    "type": "api",
    "path": "/api/chat",
    "method": "POST",
    "description": "Process a question using AI and return an answer with an interactive knowledge graph visualization. Extracts concepts, generates embeddings, clusters related concepts, and builds a graph structure.",
    "emits": [],
    "flows": ["knowledge-graph-flow"],
    "bodySchema": ChatRequest.model_json_schema(),
    "responseSchema": {
        200: ChatResponse.model_json_schema(),
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
        
        context.logger.info("Processing question", {"question": question})
        
        # 1. Generate answer using Gemini
        answer = await llm_service.generate_answer(question)
        context.logger.info("Generated answer", {"answer_length": len(answer)})
        
        # 2. Extract concepts from question and answer
        concepts = await llm_service.extract_concepts(question, answer)
        context.logger.info("Extracted concepts", {"concept_count": len(concepts)})
        
        # 3. Search Exa AI for each concept to get references
        for concept in concepts:
            try:
                search_results = await exa_service.search(concept["name"], num_results=3)
                concept["references"] = search_results
            except Exception as e:
                context.logger.info(f"Exa search failed for {concept['name']}", {"error": str(e)})
                concept["references"] = []
        
        # 4. Generate embeddings for all concepts
        embedding_texts = [f"{c['name']} {c.get('description', '')}" for c in concepts]
        embeddings = await embedding_service.get_embeddings(embedding_texts)
        context.logger.info("Generated embeddings", {"embedding_count": len(embeddings)})
        
        # 5. Cluster concepts by similarity
        clusters = await clustering_service.cluster_concepts(embeddings, concepts)
        context.logger.info("Clustered concepts", {"cluster_count": len(clusters)})
        
        # 6. Build graph from clusters and concepts
        graph = graph_service.build_graph(clusters, concepts)
        context.logger.info("Built graph", {"node_count": len(graph["nodes"]), "edge_count": len(graph["edges"])})
        
        # 7. Store graph data in Motia state for persistence across requests
        await context.state.set("knowledge_graph", "node_data", graph_service.node_data)
        await context.state.set("knowledge_graph", "graph_nodes", list(graph_service.graph.nodes()))
        
        return {
            "status": 200,
            "body": {
                "answer": answer,
                "graph": graph,
                "clusters": clusters
            }
        }
    except Exception as e:
        context.logger.error("Error processing chat request", {"error": str(e)})
        return {
            "status": 500,
            "body": {"error": f"Internal server error: {str(e)}"}
        }

