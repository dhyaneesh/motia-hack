import axios from 'axios';
import { GraphData, SelectedNodeDetails } from '@/types';

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'
});

export const api = {
  async chat(question: string, mode?: string, image?: string): Promise<{ answer: string; graph: GraphData }> {
    const response = await client.post('/api/chat', { question, mode, image });
    // Motia returns { status, body }, extract body
    return response.data.body || response.data;
  },
  
  async shopping(query: string, numResults: number = 10): Promise<{ products: any[]; graph: GraphData; clusters: any[] }> {
    const response = await client.post('/api/shopping', { query, num_results: numResults });
    return response.data.body || response.data;
  },
  
  async study(question: string): Promise<{ answer: string; graph: GraphData; clusters: any[]; learning_path: any[] }> {
    const response = await client.post('/api/study', { question });
    return response.data.body || response.data;
  },
  
  async searchWithImage(imageBase64: string, mode: string): Promise<any> {
    // Image search can use the chat endpoint with image parameter
    const response = await client.post('/api/chat', { question: '', mode, image: imageBase64 });
    return response.data.body || response.data;
  },
  
  async getNodeDetails(nodeId: string): Promise<SelectedNodeDetails> {
    try {
      const response = await client.get(`/api/nodes/${nodeId}`);
      console.log('Raw API response:', response);
      console.log('Response data:', response.data);
      // Motia HTTP layer extracts body automatically, so response.data should be the body
      const data = response.data.body || response.data;
      console.log('Extracted data:', data);
      return data;
    } catch (error: any) {
      console.error('API error:', error);
      console.error('Error response:', error.response?.data);
      throw error;
    }
  },
  
  async expandNode(nodeId: string): Promise<{ newNodes: any[]; newEdges: any[] }> {
    const response = await client.post(`/api/nodes/${nodeId}/expand`);
    // Motia returns { status, body }, extract body
    return response.data.body || response.data;
  }
};

