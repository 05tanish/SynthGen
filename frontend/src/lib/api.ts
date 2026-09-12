import axios from 'axios';

/**
 * Centralized API configuration.
 * Set VITE_API_URL in your .env file to override the default.
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

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
