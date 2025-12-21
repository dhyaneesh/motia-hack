import axios from 'axios';
import { GraphData, SelectedNodeDetails } from '@/types';

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'
});

export interface ChatStatusResponse {
  status: 'processing' | 'completed' | 'failed';
  graph?: GraphData;
  clusters?: any[];
  error?: string;
}

export const api = {
  async chat(question: string, mode?: string, image?: string, previousQuery?: string | null): Promise<{ requestId: string; answer: string; status: string }> {
    const response = await client.post('/api/chat', { question, mode, image, previousQuery });
    // Motia returns { status, body }, extract body
    return response.data.body || response.data;
  },
  
  async getChatStatus(requestId: string): Promise<ChatStatusResponse> {
    const response = await client.get(`/api/chat/status/${requestId}`);
    return response.data.body || response.data;
  },
  
  async shopping(query: string, numResults: number = 10): Promise<{ requestId: string; status: string }> {
    const response = await client.post('/api/shopping', { query, num_results: numResults });
    return response.data.body || response.data;
  },
  
  async getShoppingStatus(requestId: string): Promise<ChatStatusResponse> {
    // Reuse chat status endpoint pattern (or create shopping-specific one)
    const response = await client.get(`/api/chat/status/${requestId}`);
    return response.data.body || response.data;
  },
  
  async study(question: string): Promise<{ requestId: string; answer: string; status: string }> {
    const response = await client.post('/api/study', { question });
    return response.data.body || response.data;
  },
  
  async getStudyStatus(requestId: string): Promise<ChatStatusResponse> {
    // Reuse chat status endpoint pattern (or create study-specific one)
    const response = await client.get(`/api/chat/status/${requestId}`);
    return response.data.body || response.data;
  },
  
  async searchWithImage(imageBase64: string, mode: string): Promise<{ requestId: string; answer: string; status: string }> {
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
  
  /**
   * Expand a node - returns requestId for polling
   */
  async expandNode(nodeId: string): Promise<{ requestId: string; status: string }> {
    const response = await client.post(`/api/nodes/${nodeId}/expand`);
    // Motia returns { status, body }, extract body
    return response.data.body || response.data;
  },
  
  /**
   * Get expand status (same as chat status, reuses endpoint)
   */
  async getExpandStatus(requestId: string): Promise<{ status: string; graph?: { newNodes?: any[]; newEdges?: any[] }; error?: string }> {
    const response = await client.get(`/api/chat/status/${requestId}`);
    return response.data.body || response.data;
  },
  
  /**
   * Poll for expand status with exponential backoff
   */
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
  },
  
  /**
   * Poll for chat status until completed or failed
   */
  async pollChatStatus(requestId: string, onUpdate?: (status: ChatStatusResponse) => void, maxAttempts: number = 30, intervalMs: number = 2000): Promise<ChatStatusResponse> {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      const status = await this.getChatStatus(requestId);
      
      if (onUpdate) {
        onUpdate(status);
      }
      
      if (status.status === 'completed' || status.status === 'failed') {
        return status;
      }
      
      attempts++;
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
    
    throw new Error('Polling timeout: request did not complete within expected time');
  }
};

