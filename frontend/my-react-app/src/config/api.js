export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");
