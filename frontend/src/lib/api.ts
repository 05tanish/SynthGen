import axios from 'axios';

/**
 * Centralized API configuration.
 * Set VITE_API_BASE_URL in your .env file (or Vercel/Railway env vars) to override.
 *
 * IMPORTANT: the value must be a full URL, e.g.:
 * - Development: http://localhost:8000
 * - Production: https://your-backend.railway.app
 */

// Try multiple env variable names for compatibility
const _raw = (
  import.meta.env.VITE_API_BASE_URL ?? 
  import.meta.env.VITE_API_URL ?? 
  'http://localhost:8000'
).trim();

// Normalize: ensure protocol prefix so the URL is never treated as a relative path
const _withProtocol = _raw.startsWith('http://') || _raw.startsWith('https://')
  ? _raw
  : `https://${_raw}`;

// Strip trailing slash for consistent endpoint concatenation
export const API_BASE = _withProtocol.replace(/\/$/, '');

// Log API base URL in development for debugging
if (import.meta.env.DEV) {
  console.log('API Base URL:', API_BASE);
}

// Set up global axios interceptor for authentication
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect if unauthorized
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
      
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Set up request interceptor to add auth token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
