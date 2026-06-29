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

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`upload ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const apiStreamUrl = (path: string) => `${API_BASE}${path}`;

export interface ProviderOut {
  key: string;
  label: string;
  kind: "secret" | "url";
  required: boolean;
  group: "core" | "optional_llm";
  help: string | null;
  configured: boolean;
}

export interface ApiKeyOut {
  id: number;
  provider: string;
  kind: "secret" | "url";
  label: string | null;
  masked_value: string;
  value: string | null;
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

export interface Competitor {
  id?: number;
  name: string;
  url: string;
}

export interface Project {
  id: number;
  name: string;
  target_url: string;
  industry: string | null;
  notes: string | null;
  competitors: Competitor[];
}

export interface JobOut {
  id: number;
  project_id: number;
  source_type: string;
  status: string;
  total: number;
  processed: number;
  percent: number;
  message: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageOut {
  id: number;
  url: string;
  is_competitor: boolean;
  competitor_id: number | null;
  matched_page_id: number | null;
  rank_score: number | null;
  selected: boolean;
  fetch_method: string | null;
  http_status: number | null;
  fetch_ok: boolean;
  title: string | null;
  meta_description: string | null;
  word_count: number | null;
}

export interface ProgressEvent {
  message: string;
  processed: number;
  total: number;
  percent: number;
  status: string;
}
