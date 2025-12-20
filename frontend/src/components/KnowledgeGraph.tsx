'use client';
import { useCallback, useEffect, useMemo } from 'react';
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
import { Box } from '@chakra-ui/react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
import { ConceptNode } from './ConceptNode';
import { ProductNode } from './ProductNode';
import { ConceptCard } from './ConceptCard';
import { ExpandableFilters } from './ExpandableFilters';
import { ExpandableProgress } from './ExpandableProgress';
import { ExpandableLearningPath } from './ExpandableLearningPath';
import { ExpandableQuiz } from './ExpandableQuiz';
import { api } from '@/services/api';

export function KnowledgeGraph() {
  const { graph, selectNode } = useGraph();
  const { currentMode } = useMode();
  const [nodes, setNodes, onNodesChange] = useNodesState(graph?.nodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph?.edges || []);
  
  // Determine node types based on mode
  const nodeTypes = useMemo(() => {
    if (currentMode === 'shopping') {
      return {
        productNode: ProductNode,
        conceptNode: ConceptNode // Fallback
      };
    } else if (currentMode === 'study') {
      return {
        conceptCard: ConceptCard,
        conceptNode: ConceptNode // Fallback
      };
    } else {
      return {
        conceptNode: ConceptNode
      };
    }
  }, [currentMode]);
  
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
    <Box position="relative" w="100%" h="100%">
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
      
      {/* Expandable mode-specific panels */}
      <ExpandableFilters />
      <ExpandableProgress />
      <ExpandableLearningPath />
      <ExpandableQuiz />
    </Box>
  );
}

