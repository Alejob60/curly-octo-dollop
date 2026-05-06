import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para inyectar JWT si existe
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const dashboardApi = {
  getQueueStats: async () => {
    const response = await api.get('/dashboard/queues/counts');
    return response.data;
  },
  
  getCases: async (params: { 
    page?: number; 
    limit?: number; 
    status?: string; 
    dependency_id?: string;
    min_confidence?: number;
  }) => {
    const response = await api.get('/dashboard/cases', { params });
    return response.data;
  },

  approveBatch: async (caseIds: string[]) => {
    const response = await api.post('/dashboard/batch-approve', { case_ids: caseIds });
    return response.data;
  },

  askCopilot: async (sessionId: string, query: string) => {
    const response = await api.post('/dashboard/copilot/query', { session_id: sessionId, query });
    return response.data;
  }
};

export default api;
