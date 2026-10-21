import axios from "axios";

const API_BASE = (import.meta.env.VITE_API_BASE as string) || "";
const api = axios.create({ baseURL: API_BASE });

export const getBooks = () => api.get("/api/demo/books").then((r) => r.data);
export const getOpportunities = () => api.get("/api/demo/opportunities").then((r) => r.data);
export const getTriangular = (profitable: boolean) =>
  api.get("/api/demo/triangular", { params: { profitable } }).then((r) => r.data);
export const getLatency = () => api.get("/api/demo/latency").then((r) => r.data);
export const getHistory = () => api.get("/api/demo/history").then((r) => r.data);
