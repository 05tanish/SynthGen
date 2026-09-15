import axios from 'axios';

/**
 * Centralized API configuration.
 * Set VITE_API_URL in your .env file (or Vercel/Railway env vars) to override.
 *
 * IMPORTANT: the value must be a full URL, e.g.:

 */
const _raw = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api').trim();

// Normalize: ensure protocol prefix so the URL is never treated as a relative path
const _withProtocol = _raw.startsWith('http://') || _raw.startsWith('https://')
  ? _raw
  : `https://${_raw}`;

// Strip trailing slash for consistent endpoint concatenation
export const API_BASE = _withProtocol.replace(/\/$/, '');

// Set up global axios interceptor
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect if unauthorized
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
