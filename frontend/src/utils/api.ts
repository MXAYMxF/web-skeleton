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

// On 401 (expired/invalid token), clear the persisted session so the UI stops
// showing a logged-in state backed by a dead token. Gated pages react to the
// store change and fall back to their signed-out view.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }
    return Promise.reject(error);
  }
);

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
  deleteMe: async () => (await api.delete('/users/me')).data,
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

  deleteUser: async (id: number) => (await api.delete(`/admin/users/${id}`)).data,
};

// Application-level settings (the safe, publicly-readable subset).
export interface AppSettings {
  site_name: string;
  registration_open: boolean;
  maintenance_mode: boolean;
}

// App settings endpoints. GET is public; PATCH is superuser-only.
export const settings = {
  getSettings: async (): Promise<AppSettings> => (await api.get('/settings')).data,
  updateSettings: async (data: Partial<AppSettings>): Promise<AppSettings> =>
    (await api.patch('/settings', data)).data,
};

// A single message in a chat exchange.
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// A non-streaming chat response from the AI backend.
export interface ChatResponse {
  content: string;
  model: string;
  provider: string;
  usage: { input_tokens: number; output_tokens: number };
  stop_reason: string | null;
  conversation_id: number | null;
}

// Request body shared by the chat and streaming-chat endpoints.
export interface ChatRequest {
  messages: ChatMessage[];
  conversation_id?: number | null;
  system?: string;
}

// Callbacks driven while consuming an SSE stream from /ai/chat/stream.
// `onDone` receives the conversation_id if the backend included one on the
// stream (best-effort; the core contract only guarantees delta/done).
export interface StreamHandlers {
  onDelta: (delta: string) => void;
  onDone: (conversationId: number | null) => void;
  onError: (message: string) => void;
}

// Shape of a single decoded SSE `data:` payload.
interface StreamEvent {
  delta?: string;
  done?: boolean;
  error?: unknown;
  status_code?: number;
  conversation_id?: number | null;
}

// Pull a human-readable message out of an SSE error payload.
function streamErrorMessage(event: StreamEvent, fallback: string): string {
  const err = event.error;
  if (typeof err === 'string') return err;
  if (err && typeof err === 'object') {
    const detail = (err as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

// AI endpoints. `chat` is a normal JSON call through the shared axios instance.
export const ai = {
  chat: async (body: ChatRequest): Promise<ChatResponse> =>
    (await api.post('/ai/chat', body)).data,

  // Streaming chat. Browser SSE can't ride the axios instance cleanly, so this
  // uses native fetch against the SAME proxied path and reuses the auth token
  // from the store. Kept here so all API access stays in one module.
  streamChat: async (body: ChatRequest, handlers: StreamHandlers): Promise<void> => {
    const token = useAuthStore.getState().token;
    let response: Response;
    try {
      response = await fetch('/api/v1/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });
    } catch {
      handlers.onError('Failed to reach the chat service.');
      return;
    }

    if (response.status === 401) {
      useAuthStore.getState().clearAuth();
    }

    if (!response.ok || !response.body) {
      let message = `Request failed (${response.status}).`;
      try {
        const data = (await response.json()) as {
          detail?: unknown;
          error?: { detail?: unknown };
        };
        const detail = data?.error?.detail ?? data?.detail;
        if (typeof detail === 'string') message = detail;
      } catch {
        // Non-JSON body; keep the generic message.
      }
      handlers.onError(message);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let conversationId: number | null = null;
    let errored = false;

    // Parse one SSE `data:` line. Returns true if the stream is finished.
    const handleLine = (line: string): boolean => {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:')) return false;
      const payload = trimmed.slice(5).trim();
      if (!payload) return false;
      let event: StreamEvent;
      try {
        event = JSON.parse(payload) as StreamEvent;
      } catch {
        return false;
      }
      if (typeof event.conversation_id === 'number') {
        conversationId = event.conversation_id;
      }
      if (event.error !== undefined) {
        errored = true;
        handlers.onError(streamErrorMessage(event, 'The chat stream errored.'));
        return true;
      }
      if (typeof event.delta === 'string' && event.delta) {
        handlers.onDelta(event.delta);
      }
      return event.done === true;
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let newlineIndex = buffer.indexOf('\n');
        while (newlineIndex !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (handleLine(line)) {
            await reader.cancel();
            if (!errored) handlers.onDone(conversationId);
            return;
          }
          newlineIndex = buffer.indexOf('\n');
        }
      }
      // Flush any trailing buffered line once the stream closes.
      if (buffer.trim() && handleLine(buffer) && errored) {
        return;
      }
      handlers.onDone(conversationId);
    } catch {
      handlers.onError('The chat stream was interrupted.');
    }
  },
};

export default api;
