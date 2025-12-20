'use client';
import { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  NodeMouseHandler
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useGraph } from '@/contexts/GraphContext';
import { ConceptNode } from './ConceptNode';
import { api } from '@/services/api';

const nodeTypes = {
  conceptNode: ConceptNode
};

export function KnowledgeGraph() {
  const { graph, selectNode } = useGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState(graph?.nodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph?.edges || []);
  
  // Update nodes/edges when graph changes
  useEffect(() => {
    if (graph) {
      setNodes(graph.nodes);
      setEdges(graph.edges);
    }
  }, [graph, setNodes, setEdges]);
  
  // Handle node click - fetch details and open sidebar
  const onNodeClick: NodeMouseHandler = useCallback(async (event, node) => {
    try {
      console.log('Fetching node details for:', node.id);
      const details = await api.getNodeDetails(node.id);
      console.log('Received node details:', details);
      selectNode(details);
    } catch (error) {
      console.error('Failed to fetch node details:', error);
    }
  }, [selectNode]);
  
  if (!graph || graph.nodes.length === 0) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        color: '#666'
      }}>
        Ask a question to generate a knowledge graph
      </div>
    );
  }
  
  // Default edge styles
  const defaultEdgeOptions = {
    style: { strokeWidth: 2, stroke: '#94a3b8' },
    type: 'smoothstep',
    animated: false
  };

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={onNodeClick}
      nodeTypes={nodeTypes}
      defaultEdgeOptions={defaultEdgeOptions}
      fitView
      minZoom={0.1}
      maxZoom={2}
    >
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
}

