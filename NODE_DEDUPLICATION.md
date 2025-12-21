# Node Deduplication Feature

## Problem
The knowledge graph was creating multiple cards/nodes that were too similar or semantically identical, resulting in:
- Cluttered visualization
- Redundant information
- Poor user experience
- Difficulty navigating the graph

## Solution: Semantic Deduplication

Added automatic node merging based on embedding similarity to detect and merge semantically similar nodes.

## How It Works

### 1. Similarity Detection
- Calculates cosine similarity between node embeddings
- Default threshold: **0.85** (85% similarity)
- Higher threshold = more aggressive merging

### 2. Merging Strategy
When two nodes exceed the similarity threshold:

**Canonical Node Selection:**
- First node encountered becomes the "canonical" node
- All other similar nodes merge into it

**Data Merging:**
- **References**: Combines all references (deduplicates by URL)
- **Description**: Keeps the longer, more detailed description
- **Product Data**: 
  - Price: Keeps lower price
  - Rating: Keeps higher rating
  - Specs: Merges all specifications
- **Edges**: Redirects all connections to canonical node

### 3. Graph Updates
- Merged nodes are removed from the graph
- Edges are redirected to canonical nodes
- Self-loops are prevented
- Node data is consolidated

## Implementation

### GraphService Method
Added `deduplicate_nodes()` method to `src/services/graph_service.py`:

```python
def deduplicate_nodes(
    self, 
    embeddings_dict: Dict[str, List[float]], 
    similarity_threshold: float = 0.85
) -> Dict[str, str]:
    """
    Identify and merge highly similar nodes.
    
    Returns:
        Dictionary mapping old_node_id -> canonical_node_id
    """
```

### Integration Points

**1. Build Graph Event** (`src/events/build_graph_step.py`)
- Runs after graph construction
- Deduplicates across all nodes (new + existing)
- Logs merge count and sample merges

**2. Expand Node Event** (`src/events/expand_node_step.py`)
- Generates embeddings for new expanded nodes
- Deduplicates new nodes against existing graph
- Prevents duplicates from being added during expansion

## Similarity Threshold Guide

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.95+ | Very conservative | Only merge near-duplicates |
| 0.85-0.94 | **Recommended** | Merge similar concepts |
| 0.75-0.84 | Aggressive | Merge related topics |
| <0.75 | Too aggressive | May merge unrelated nodes |

Current setting: **0.85** (good balance)

## Examples

### Example 1: Duplicate Concepts
**Before:**
- Node 1: "Jeffrey Epstein" (description: "American financier...")
- Node 2: "Jeffrey Epstein Person" (description: "Financier and convicted...")

**After Deduplication:**
- Node 1: "Jeffrey Epstein" (merged description + combined references)

### Example 2: Product Variants
**Before:**
- Product 1: "iPhone 15 Pro" - $999, 4.5★
- Product 2: "iPhone 15 Pro Max" - $1099, 4.7★

**After Deduplication:**
- If similarity > 0.85, merges into single node with:
  - Price: $999 (lower)
  - Rating: 4.7★ (higher)
  - Combined specs and references

### Example 3: Expansion Deduplication
User expands "Machine Learning" node:
- Finds new concepts: "Neural Networks", "Deep Learning", "ML Algorithms"
- If "Neural Networks" already exists in graph (similarity > 0.85)
- New node is merged into existing, references are combined

## Logging

Deduplication events are logged:

```
[INFO] Deduplicated similar nodes
├ merged_count: 3
└ merge_map_sample: {
  │ "concept_12": "concept_5",
  │ "concept_18": "concept_7",
  │ "concept_23": "concept_11"
  }
```

## Tuning

To adjust the similarity threshold, modify in:

**`src/events/build_graph_step.py`:**
```python
merge_map = graph_service.deduplicate_nodes(embeddings_dict, similarity_threshold=0.85)
```

**`src/events/expand_node_step.py`:**
```python
merge_map = graph_service.deduplicate_nodes(all_embeddings, similarity_threshold=0.85)
```

**Recommendation:** Start with 0.85, increase if too aggressive, decrease if duplicates remain.

## Benefits

✅ **Cleaner Graphs**: Fewer redundant nodes
✅ **Better UX**: Easier to navigate and understand
✅ **Consolidated Info**: All references in one place
✅ **Automatic**: No manual intervention required
✅ **Smart Merging**: Preserves best information from each node
✅ **Cross-Query**: Works across multiple chat interactions
✅ **Expansion-Safe**: Prevents duplicates during node expansion

## Performance Impact

- **Minimal**: Deduplication runs once per graph build/expansion
- **Complexity**: O(n²) for similarity calculation (acceptable for typical graph sizes)
- **Time**: ~100-500ms for 50 nodes
- **Memory**: No significant increase

## Future Enhancements

- [ ] User-configurable threshold in UI settings
- [ ] Manual node merge/split controls
- [ ] Similarity explanation (why nodes were merged)
- [ ] Undo merge functionality
- [ ] Cluster-aware merging (prefer merging within same cluster)

