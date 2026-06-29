import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiGet, apiSend, type ModuleResult, type Project } from "@/lib/api";
import { MODULES } from "@/lib/modules";
import { ModuleResultView } from "@/components/ModuleResultView";

// Modules with a real analyzer (Phases 2–4). Others remain scaffolded.
const IMPLEMENTED = new Set([
  "technical_seo",
  "on_page",
  "internal_linking",
  "backlinks",
  "keyword_universe",
  "aeo_audit",
]);

export function ModulePage() {
  const { moduleKey } = useParams();
  const meta = MODULES.find((m) => m.key === moduleKey);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [scope, setScope] = useState<"site" | "page">("site");

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiGet<Project[]>("/projects"),
    enabled: !!meta && IMPLEMENTED.has(meta.key),
  });

  useEffect(() => {
    if (projectId == null && projects?.length) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const analyze = useMutation({
    mutationFn: () =>
      apiSend<ModuleResult>(
        "POST",
        `/projects/${projectId}/modules/${meta!.key}/analyze?scope=${scope}`,
      ),
  });

  if (!meta) return <div className="text-slate-400">Unknown module: {moduleKey}</div>;

  if (!IMPLEMENTED.has(meta.key)) {
    return (
      <div className="space-y-4">
        <header>
          <div className="text-xs uppercase tracking-wider text-eclerx-red">{meta.layer}</div>
          <h1 className="text-2xl font-semibold text-white">{meta.title}</h1>
        </header>
        <div className="rounded-lg border border-dashed border-navy-700 bg-navy-900 p-8 text-center">
          <p className="text-sm text-slate-400">
            This module is scaffolded. Its analyzer is implemented in{" "}
            <span className="font-medium text-slate-200">Phase {meta.phase}</span>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <div className="text-xs uppercase tracking-wider text-eclerx-red">{meta.layer}</div>
        <h1 className="text-2xl font-semibold text-white">{meta.title}</h1>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-navy-800 bg-navy-900 p-4">
        <select
          value={projectId ?? ""}
          onChange={(e) => setProjectId(Number(e.target.value))}
          className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
        >
          {(projects ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
          {!projects?.length && <option>No projects — ingest first</option>}
        </select>

        <div className="flex overflow-hidden rounded-md border border-navy-700">
          {(["site", "page"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={
                "px-3 py-2 text-sm capitalize " +
                (scope === s ? "bg-eclerx-red text-white" : "text-slate-400 hover:bg-navy-800")
              }
            >
              {s}
            </button>
          ))}
        </div>

        <button
          onClick={() => analyze.mutate()}
          disabled={projectId == null || analyze.isPending}
          className="ml-auto rounded-md bg-eclerx-red px-4 py-2 text-sm font-medium text-white hover:bg-eclerx-red-dark disabled:opacity-40"
        >
          {analyze.isPending ? "Analyzing…" : "Run analysis"}
        </button>
      </div>

      {analyze.isError && (
        <div className="rounded-lg border border-eclerx-red/40 bg-eclerx-red/10 p-3 text-sm text-eclerx-red">
          {(analyze.error as Error).message.includes("409")
            ? "No completed crawl for this project yet — run Ingestion first."
            : (analyze.error as Error).message}
        </div>
      )}

      {analyze.data && projectId != null && (
        <ModuleResultView result={analyze.data} projectId={projectId} moduleKey={meta.key} />
      )}
    </div>
  );
}
