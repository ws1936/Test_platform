import axios, { AxiosInstance } from "axios";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

// Request interceptor: inject bearer token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 → redirect to /login
api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
