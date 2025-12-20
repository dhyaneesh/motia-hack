export interface Reference {
  id: string;
  url: string;
  title: string;
  text: string;
  publishedDate?: string;
  author?: string;
}

export interface NodeData {
  name: string;
  description: string;
  nodeType: 'concept' | 'entity' | 'event' | 'person';
  clusterId: string;
  references: Reference[];
}

export interface GraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: NodeData;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  weight?: number;
}

export interface Cluster {
  id: string;
  label: string;
  conceptIds: string[];
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters?: Cluster[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SelectedNodeDetails {
  id: string;
  name: string;
  description: string;
  type: string;
  references: Reference[];
  relatedNodes: { id: string; name: string }[];
}

