const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  get: async (endpoint) => {
    const res = await fetch(`${API_URL}${endpoint}`);
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
    return res.json();
  },
  post: async (endpoint, body = {}) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`); 
    return res.json(); // Some endpoints might return empty body, handle with care? 
    // Actually scans return empty usually, but let's see. 
    // If response is empty text, return null or check res.headers.
  },
  put: async (endpoint, body = {}) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
    return res.json();
  },
  delete: async (endpoint) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
    return res.json();
  },
  url: (path) => `${API_URL}${path}`
};
