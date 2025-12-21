# Expand Node Fix - Complete

## Problem
Frontend showed error: **"newNodes is not iterable"** when expanding nodes.

## Root Cause
The frontend was calling `api.expandNode()` expecting it to return `{ newNodes, newEdges }` directly, but the refactored backend now uses async event-driven processing:

1. `POST /api/nodes/:nodeId/expand` → Returns `{ requestId, status: "processing" }`
2. Event step processes expansion asynchronously
3. Frontend must poll `GET /api/chat/status/:requestId` to get results

## Backend Flow (Already Working)
```
ExpandNodeAPI
  ↓ emit: expand-node
ExpandNodeEvent (searches, extracts concepts, updates graph)
  ↓ stores: graph:{requestId} = { newNodes: [...], newEdges: [...] }
  ↓ emit: graph-ready
GraphReady (sets status to "completed")
```

Terminal logs confirmed this is working:
```
[1:39:26 pm] ExpandNodeEvent Graph expanded successfully
├ new_nodes_count: 4
└ new_edges_count: 4
[1:39:26 pm] GraphReady Status updated to completed
```

## Frontend Fixes Applied

### 1. Updated `frontend/src/services/api.ts`
Added `pollExpandStatus()` function to poll until completion:

```typescript
async pollExpandStatus(requestId: string, onUpdate?: (status: any) => void, maxAttempts: number = 20, intervalMs: number = 1000): Promise<{ newNodes: any[]; newEdges: any[] }> {
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const status = await this.getExpandStatus(requestId);
    
    if (onUpdate) {
      onUpdate(status);
    }
    
    if (status.status === 'completed') {
      // Extract newNodes and newEdges from graph
      const newNodes = status.graph?.newNodes || [];
      const newEdges = status.graph?.newEdges || [];
      return { newNodes, newEdges };
    }
    
    if (status.status === 'failed') {
      throw new Error(status.error || 'Node expansion failed');
    }
    
    attempts++;
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  
  throw new Error('Polling timeout - node expansion taking too long');
}
```

### 2. Updated `frontend/src/components/NodeDetailSidebar.tsx`
Changed `handleExpand()` to use polling:

```typescript
const handleExpand = async () => {
  setIsExpanding(true);
  try {
    // Initiate expansion
    const { requestId } = await api.expandNode(selectedNode.id);
    
    toast({
      title: 'Expanding node...',
      description: 'Searching for related knowledge',
      status: 'info',
      duration: 2000,
      isClosable: true
    });
    
    // Poll for completion
    const { newNodes, newEdges } = await api.pollExpandStatus(requestId, (status) => {
      // Optional: Update UI with progress
    });
    
    if (newNodes && newEdges) {
      addToGraph(newNodes, newEdges);
      toast({
        title: 'Success',
        description: `Added ${newNodes.length} new nodes`,
        status: 'success',
        duration: 3000,
        isClosable: true
      });
    }
  } catch (error: any) {
    toast({
      title: 'Error',
      description: error.message || 'Failed to expand node',
      status: 'error',
      duration: 5000,
      isClosable: true
    });
  } finally {
    setIsExpanding(false);
  }
};
```

## Status API Response Format
`GET /api/chat/status/:requestId` returns:

```json
{
  "status": "completed",
  "graph": {
    "newNodes": [
      { "id": "...", "name": "...", "type": "...", ... }
    ],
    "newEdges": [
      { "id": "...", "source": "...", "target": "..." }
    ]
  }
}
```

For regular chat flow:
```json
{
  "status": "completed",
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "clusters": [...]
}
```

## Testing
1. Open frontend and ask a question
2. Click on a node to view details
3. Click "Expand & Find More" button
4. Should show "Expanding node..." toast
5. After ~30s, should show "Success: Added N new nodes"
6. Graph should update with new nodes

## Benefits
- **Non-blocking UI**: Frontend remains responsive during expansion
- **Progress indication**: Can show "Expanding..." state
- **Error handling**: Proper error messages if expansion fails
- **Consistent pattern**: Same polling pattern as chat flow

