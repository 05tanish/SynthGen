/**
 * Centralized API configuration.
 * Set VITE_API_URL in your .env file to override the default.
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';
