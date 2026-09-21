import axios from "axios";

export const API_BASE = "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("sova_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      // Only force logout if it's an authentication error (not validate credentials)
      if (error.response.data?.detail === "Could not validate credentials") {
        localStorage.removeItem("sova_token");
        localStorage.removeItem("sova_user");
        localStorage.removeItem("sova_project");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default client;
