# Knowledge Graph Chatbot Refactoring - Complete

## Summary
Successfully refactored monolithic API steps into event-driven Motia flows.

## Files Renamed (Python Naming Convention)
All Python steps must use `_step.py` extension (not `.step.py`, `.event.py`, or `.cron.py`):

### Event Steps (src/events/)
- `extract_concepts_step.py` - Extracts concepts from Q&A using LLM
- `search_references_step.py` - Parallel Tavily searches for references
- `generate_embeddings_step.py` - Gemini embeddings generation
- `cluster_concepts_step.py` - HDBSCAN clustering
- `build_graph_step.py` - Graph construction with NetworkX
- `connect_cross_query_step.py` - Connect nodes across queries
- `graph_ready_step.py` - Mark graph completion
- `expand_node_step.py` - Node expansion logic
- `assign_levels_step.py` - Concept level assignment (study mode)
- `identify_prerequisites_step.py` - Prerequisite identification (study mode)
- `build_learning_path_step.py` - Learning path generation (study mode)
- `search_products_step.py` - Product search (shopping mode)
- `extract_specs_step.py` - Product spec extraction (shopping mode)

### API Steps (src/api/)
- `chat_status_step.py` - Polling endpoint for async status

### Cron Steps (src/cron/)
- `cleanup_state_step.py` - Cleanup old state every 6 hours

## Event Flow Architecture

### Knowledge Graph Flow
```
ChatAPI (POST /api/chat)
  ↓ emit: extract-concepts
ExtractConcepts
  ↓ emit: search-references
SearchReferences
  ↓ emit: generate-embeddings
GenerateEmbeddings
  ↓ emit: cluster-concepts
ClusterConcepts
  ↓ emit: build-graph
BuildGraph
  ↓ emit: connect-cross-query (conditional) OR graph-ready
ConnectCrossQuery (if follow-up query)
  ↓ emit: graph-ready
GraphReady
```

### Study Flow
```
StudyAPI (POST /api/study)
  ↓ emit: extract-concepts
ExtractConcepts
  ↓ emit: assign-levels
AssignLevels
  ↓ emit: identify-prerequisites
IdentifyPrerequisites
  ↓ emit: build-learning-path
BuildLearningPath
  ↓ emit: generate-embeddings
GenerateEmbeddings
  ↓ emit: cluster-concepts
ClusterConcepts
  ↓ emit: build-graph
BuildGraph
  ↓ emit: graph-ready
GraphReady
```

### Shopping Flow
```
ShoppingAPI (POST /api/shopping)
  ↓ emit: search-products
SearchProducts
  ↓ emit: extract-specs
ExtractSpecs
  ↓ emit: generate-embeddings
GenerateEmbeddings
  ↓ emit: cluster-concepts
ClusterConcepts
  ↓ emit: build-graph
BuildGraph
  ↓ emit: graph-ready
GraphReady
```

### Expand Node Flow
```
ExpandNodeAPI (POST /api/nodes/:nodeId/expand)
  ↓ emit: expand-node
ExpandNodeEvent
  ↓ emit: graph-ready
GraphReady
```

## State Management
Created `src/utils/state_keys.py` for consistent state key naming:
- `request_data:{request_id}` - Stores question, answer, mode
- `request_status:{request_id}` - Stores processing status
- `concepts:{request_id}` - Extracted concepts
- `embeddings:{request_id}` - Concept embeddings
- `clusters:{request_id}` - Clustering results
- `graph:{request_id}` - Final graph data
- `learning_path:{request_id}` - Study mode path
- `products:{request_id}` - Shopping mode products
- `{flow_name}_graph_state:current` - Persistent graph state for merging

## Polling API
Frontend polls `GET /api/chat/status/:requestId` for:
- `status`: "processing" | "completed" | "failed"
- `stage`: Current processing stage
- `graph`: Graph data (when complete)
- `answer`: LLM answer (immediate)
- `learningPath`: Study mode path (when complete)
- `products`: Shopping mode products (when complete)

## Frontend Updates
- `frontend/src/services/api.ts` - Added `pollChatStatus()` with exponential backoff
- `frontend/src/components/ChatInterface.tsx` - Uses polling for progressive loading

## Benefits
1. **Performance**: API responds in ~1-2s, graph builds in background
2. **Resilience**: Each step can fail/retry independently
3. **Observability**: Each step logs independently
4. **Scalability**: Event steps scale independently
5. **Maintainability**: Steps are 50-100 lines vs 200-300 monolithic
6. **Reusability**: Core events shared across flows

## Testing
1. Start dev server: `npm run dev`
2. Server should register all event steps (check for warnings)
3. Test chat endpoint: `POST http://localhost:3000/api/chat`
4. Poll status: `GET http://localhost:3000/api/chat/status/{requestId}`
5. View in Workbench: `http://localhost:3000`

## Troubleshooting
- **"No subscriber defined" warnings**: Check that event steps are registered
- **Event steps not loading**: Verify `_step.py` naming convention
- **Import errors**: Check Python path and module imports
- **State not persisting**: Check Redis memory server is running

