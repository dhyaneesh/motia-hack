'use client';
import { createContext, useContext, useState, ReactNode } from 'react';
import { GraphData, SelectedNodeDetails, GraphNode, GraphEdge } from '@/types';

interface GraphContextType {
  graph: GraphData | null;
  selectedNode: SelectedNodeDetails | null;
  isSidebarOpen: boolean;
  setGraph: (graph: GraphData) => void;
  selectNode: (node: SelectedNodeDetails | null) => void;
  addToGraph: (newNodes: GraphNode[], newEdges: GraphEdge[]) => void;
  clearGraph: () => void;
}

const GraphContext = createContext<GraphContextType | undefined>(undefined);

export function GraphProvider({ children }: { children: ReactNode }) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<SelectedNodeDetails | null>(null);
  
  const selectNode = (node: SelectedNodeDetails | null) => {
    console.log('Setting selected node:', node);
    setSelectedNode(node);
  };
  
  const addToGraph = (newNodes: GraphNode[], newEdges: GraphEdge[]) => {
    if (!graph) return;
    setGraph({
      ...graph,
      nodes: [...graph.nodes, ...newNodes],
      edges: [...graph.edges, ...newEdges]
    });
  };
  
  const clearGraph = () => {
    setGraph(null);
    setSelectedNode(null);
  };
  
  return (
    <GraphContext.Provider value={{
      graph,
      selectedNode,
      isSidebarOpen: selectedNode !== null,
      setGraph,
      selectNode,
      addToGraph,
      clearGraph
    }}>
      {children}
    </GraphContext.Provider>
  );
}

export const useGraph = () => {
  const context = useContext(GraphContext);
  if (!context) throw new Error('useGraph must be used within GraphProvider');
  return context;
};

