import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[Gridlock API]', err.config?.method?.toUpperCase(), err.config?.url, err.message);
    return Promise.reject(err);
  },
);
