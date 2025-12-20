import axios from 'axios';
import { GraphData, SelectedNodeDetails } from '@/types';

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'
});

export const api = {
  async chat(question: string): Promise<{ answer: string; graph: GraphData }> {
    const response = await client.post('/api/chat', { question });
    return response.data;
  },
  
  async getNodeDetails(nodeId: string): Promise<SelectedNodeDetails> {
    const response = await client.get(`/api/nodes/${nodeId}`);
    return response.data;
  },
  
  async expandNode(nodeId: string): Promise<{ newNodes: any[]; newEdges: any[] }> {
    const response = await client.post(`/api/nodes/${nodeId}/expand`);
    return response.data;
  }
};

