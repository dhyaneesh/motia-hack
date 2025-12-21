'use client';
import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { GraphData, SelectedNodeDetails, GraphNode, GraphEdge } from '@/types';
import { Mode } from './ModeContext';

interface GraphContextType {
  graph: GraphData | null;
  selectedNode: SelectedNodeDetails | null;
  isSidebarOpen: boolean;
  currentRequestId: string | null;
  setGraph: (graph: GraphData) => void;
  selectNode: (node: SelectedNodeDetails | null) => void;
  addToGraph: (newNodes: GraphNode[], newEdges: GraphEdge[]) => void;
  clearGraph: () => void;
  setRequestId: (requestId: string | null) => void;
  // Mode-specific state preservation
  savedGraphs: Record<Mode, GraphData | null>;
  saveGraphForMode: (mode: Mode) => void;
  restoreGraphForMode: (mode: Mode) => void;
}

const GraphContext = createContext<GraphContextType | undefined>(undefined);

export function GraphProvider({ children }: { children: ReactNode }) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<SelectedNodeDetails | null>(null);
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);
  const [savedGraphs, setSavedGraphs] = useState<Record<Mode, GraphData | null>>({
    default: null,
    shopping: null,
    study: null
  });
  
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
    setCurrentRequestId(null);
  };
  
  const setRequestId = (requestId: string | null) => {
    setCurrentRequestId(requestId);
  };
  
  const saveGraphForMode = useCallback((mode: Mode) => {
    if (graph) {
      setSavedGraphs(prev => ({ ...prev, [mode]: graph }));
    }
  }, [graph]);
  
  const restoreGraphForMode = useCallback((mode: Mode) => {
    const savedGraph = savedGraphs[mode];
    if (savedGraph) {
      setGraph(savedGraph);
    } else {
      setGraph(null);
    }
    setSelectedNode(null);
  }, [savedGraphs]);
  
  return (
    <GraphContext.Provider value={{
      graph,
      selectedNode,
      isSidebarOpen: selectedNode !== null,
      currentRequestId,
      setGraph,
      selectNode,
      addToGraph,
      clearGraph,
      setRequestId,
      savedGraphs,
      saveGraphForMode,
      restoreGraphForMode
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

