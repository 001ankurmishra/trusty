import axios from "axios";

export const API_BASE = "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("sova_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default client;
