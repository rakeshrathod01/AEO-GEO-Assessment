// Mirror of backend app/modules_registry.py — keep in sync.
export interface ModuleMeta {
  key: string;
  order: number;
  title: string;
  layer: "SEO" | "AEO" | "GEO" | "Leadership";
  phase: number;
}

export const MODULES: ModuleMeta[] = [
  { key: "technical_seo", order: 1, title: "Technical SEO", layer: "SEO", phase: 2 },
  { key: "on_page", order: 2, title: "On-Page SEO", layer: "SEO", phase: 2 },
  { key: "internal_linking", order: 3, title: "Internal Linking", layer: "SEO", phase: 3 },
  { key: "backlinks", order: 4, title: "Backlinks", layer: "SEO", phase: 3 },
  { key: "keyword_universe", order: 5, title: "Keyword Universe", layer: "SEO", phase: 3 },
  { key: "aeo_audit", order: 6, title: "AEO Audit", layer: "AEO", phase: 4 },
  { key: "prompt_identification", order: 7, title: "Prompt Identification", layer: "GEO", phase: 5 },
  { key: "geo_audit", order: 8, title: "GEO Audit", layer: "GEO", phase: 5 },
  { key: "leadership", order: 9, title: "Leadership Dashboard", layer: "Leadership", phase: 6 },
];
