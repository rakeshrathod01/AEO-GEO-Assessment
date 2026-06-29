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

export interface Finding {
  signal: string;
  status: "pass" | "warn" | "fail";
  value: string | number | boolean | null;
  benchmark: string | number | null;
  source: string | null;
  evidence: string | null;
}

export interface Recommendation {
  priority: "high" | "med" | "low";
  layer: "SEO" | "AEO" | "GEO";
  action: string;
  how_to: string | null;
  effort: string | null;
  impact: string | null;
}

export interface CompetitorDelta {
  competitor: string;
  signal: string;
  them: string | number | null;
  us: string | number | null;
  gap: string | number | null;
}

export interface ModuleResult {
  scope: "site" | "page";
  target_url: string;
  score: number;
  status: "pass" | "warn" | "fail";
  findings: Finding[];
  recommendations: Recommendation[];
  competitor_delta: CompetitorDelta[];
  module: string | null;
  generated_at: string | null;
}

const API_PREFIX = "/api/v1";
export const exportUrl = (
  projectId: number,
  moduleKey: string,
  kind: "xlsx" | "pdf",
  scope: string,
) => {
  const file = kind === "xlsx" ? "export.xlsx" : "report.pdf";
  return `${API_PREFIX}/projects/${projectId}/modules/${moduleKey}/${file}?scope=${scope}`;
};

export const leadershipExportUrl = (projectId: number, kind: "xlsx" | "pdf", scope: string) => {
  const file = kind === "xlsx" ? "export.xlsx" : "report.pdf";
  return `${API_PREFIX}/projects/${projectId}/leadership/${file}?scope=${scope}`;
};

export const deckUrl = (projectId: number, scope: string) =>
  `${API_PREFIX}/projects/${projectId}/leadership/deck.pptx?scope=${scope}`;

export interface ModuleScore {
  key: string;
  title: string;
  layer: "SEO" | "AEO" | "GEO";
  score: number;
  status: "pass" | "warn" | "fail";
}

export interface RoadmapItem {
  phase: "SEO" | "AEO" | "GEO";
  order: number;
  priority: "high" | "med" | "low";
  layer: string;
  module: string;
  action: string;
  how_to: string | null;
  effort: string | null;
  impact: string | null;
  rationale: string | null;
}

export interface BenchmarkMarker {
  metric: string;
  value: number | null;
  unit: string | null;
  source: string;
  source_url: string | null;
}

export interface LeadershipReport {
  scope: "site" | "page";
  target_url: string;
  generated_at: string | null;
  overall_score: number;
  status: "pass" | "warn" | "fail";
  layer_scores: { SEO: number | null; AEO: number | null; GEO: number | null };
  modules: ModuleScore[];
  executive_summary: string;
  roadmap: RoadmapItem[];
  benchmarks: BenchmarkMarker[];
  competitor_summary: CompetitorDelta[];
  synthesis_source: string;
}

export interface ProjectPage {
  id: number;
  url: string;
  title: string | null;
}
