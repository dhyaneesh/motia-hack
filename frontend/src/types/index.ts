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
  // Product-specific fields
  imageUrl?: string;
  price?: number;
  rating?: number;
  retailer?: string;
  url?: string;
  specs?: Record<string, any>;
  reviewSummary?: string;
  // Study-specific fields
  level?: number | string; // 1=Beginner, 2=Intermediate, 3=Advanced, "Concept"=placeholder
  prerequisites?: string[];
  learningPathPosition?: number;
}

export type Mode = 'default' | 'shopping' | 'study';

export interface ProductNodeData extends NodeData {
  imageUrl?: string;
  price?: number;
  rating?: number;
  retailer?: string;
  url?: string;
  specs?: Record<string, any>;
  reviewSummary?: string;
}

export interface StudyNodeData extends NodeData {
  level?: number | string; // 1=Beginner, 2=Intermediate, 3=Advanced, "Concept"=placeholder
  prerequisites?: string[];
  learningPathPosition?: number;
}

