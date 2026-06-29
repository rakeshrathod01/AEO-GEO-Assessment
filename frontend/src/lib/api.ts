// Thin API client. Base path is proxied to the FastAPI backend (see vite.config.ts).
const API_BASE = "/api/v1";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiSend<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status}`);
  if (res.status === 204) return null;
  return res.json() as Promise<T>;
}

export interface ApiKeyOut {
  id: number;
  provider: string;
  label: string | null;
  masked_value: string;
  created_at: string;
  updated_at: string;
}

export interface HealthOut {
  status: string;
  app: string;
  version: string;
  env: string;
  database: string;
}
