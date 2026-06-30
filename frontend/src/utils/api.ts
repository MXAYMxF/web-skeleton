import axios from 'axios';
import { useAuthStore } from '@/stores/useAuthStore';

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
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
    formData.append('username', email); // OAuth2 expects 'username' not 'email'
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

// User endpoints (current user)
export const users = {
  getMe: async () => (await api.get('/users/me')).data,
  updateMe: async (data: {
    full_name?: string | null;
    email?: string;
    password?: string;
    preferences?: Record<string, unknown>;
  }) => (await api.patch('/users/me', data)).data,
};

// Shape of a user as returned by the admin endpoints.
export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login?: string | null;
  login_count?: number | null;
  preferences?: Record<string, unknown> | null;
}

// A paginated list response from the admin user-listing endpoint.
export interface AdminUserList {
  items: AdminUser[];
  total: number;
  skip: number;
  limit: number;
}

// Admin (superuser-only) user-management endpoints.
export const admin = {
  listUsers: async (params: {
    skip?: number;
    limit?: number;
    q?: string;
  }): Promise<AdminUserList> => (await api.get('/admin/users', { params })).data,

  getUser: async (id: number): Promise<AdminUser> =>
    (await api.get(`/admin/users/${id}`)).data,

  createUser: async (data: {
    email: string;
    password: string;
    full_name?: string;
    is_active?: boolean;
    is_superuser?: boolean;
  }): Promise<AdminUser> => (await api.post('/admin/users', data)).data,

  updateUser: async (
    id: number,
    data: {
      email?: string;
      full_name?: string | null;
      password?: string;
      is_active?: boolean;
      is_superuser?: boolean;
    }
  ): Promise<AdminUser> => (await api.patch(`/admin/users/${id}`, data)).data,
};

export default api;
