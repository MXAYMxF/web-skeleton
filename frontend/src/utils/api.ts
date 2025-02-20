import axios from 'axios';
import { useAuthStore } from '@/stores/useAuthStore';

const api = axios.create({
  baseURL: 'http://localhost:3000/api/v1',
});

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth endpoints
export const auth = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },
  
  testToken: async () => {
    const response = await api.post('/auth/test-token');
    return response.data;
  },
};

export default api;
