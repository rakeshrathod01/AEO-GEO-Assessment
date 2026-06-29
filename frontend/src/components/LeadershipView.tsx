import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileText, Info, Presentation } from "lucide-react";
import {
  apiGet,
  apiSend,
  deckUrl,
  leadershipExportUrl,
  type LeadershipReport,
  type Project,
  type ProjectPage,
} from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  pass: "text-emerald-400",
  warn: "text-amber-400",
  fail: "text-eclerx-red",
};
const PHASE_LABEL: Record<string, string> = {
  SEO: "1 · Foundational SEO",
  AEO: "2 · AEO",
  GEO: "3 · GEO",
};
const PRIORITY_COLOR: Record<string, string> = {
  high: "bg-eclerx-red/20 text-eclerx-red",
  med: "bg-amber-400/20 text-amber-300",
  low: "bg-slate-500/20 text-slate-300",
};

function LayerBar({ label, score }: { label: string; score: number | null }) {
  return (
    <div className="rounded-lg border border-navy-800 bg-navy-900 p-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-semibold text-slate-100">{score ?? "—"}</span>
      </div>
      <div className="relative mt-2 h-2 rounded-full bg-navy-800">
        <div
          className="h-full rounded-full bg-eclerx-red"
          style={{ width: `${score ?? 0}%` }}
        />
        {/* Benchmark target marker at 80, with sourced tooltip */}
        <span
          title="Target readiness — eClerx AEO/GEO methodology"
          className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-slate-300"
          style={{ left: "80%" }}
        />
      </div>
    </div>
  );
}

export function LeadershipView({ projectId: fixedId }: { projectId?: number }) {
  const [projectId, setProjectId] = useState<number | null>(fixedId ?? null);
  const [scope, setScope] = useState<"site" | "page">("site");
  const [pageId, setPageId] = useState<number | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiGet<Project[]>("/projects"),
    enabled: fixedId == null,
  });
  useEffect(() => {
    if (projectId == null && projects?.length) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: pages } = useQuery({
    queryKey: ["project-pages", projectId],
    queryFn: () => apiGet<ProjectPage[]>(`/projects/${projectId}/pages`),
    enabled: projectId != null,
  });

  const run = useMutation({
    mutationFn: () => {
      const q = scope === "page" && pageId ? `&page_id=${pageId}` : "";
      return apiSend<LeadershipReport>(
        "POST",
        `/projects/${projectId}/leadership?scope=${scope}${q}`,
      );
    },
  });

  const report = run.data;

  return (
    <div className="space-y-6">
      <header>
        <div className="text-xs uppercase tracking-wider text-eclerx-red">Leadership</div>
        <h1 className="text-2xl font-semibold text-white">Leadership Dashboard</h1>
        <p className="text-sm text-slate-400">
          Cross-module synthesis → one prioritized roadmap (foundational SEO → AEO → GEO).
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-navy-800 bg-navy-900 p-4">
        {fixedId == null && (
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
        )}

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

        {/* Page-selector — re-scopes the whole dashboard to a single page */}
        {scope === "page" && (
          <select
            value={pageId ?? ""}
            onChange={(e) => setPageId(Number(e.target.value))}
            className="max-w-md flex-1 rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
          >
            <option value="">Top-ranked page</option>
            {(pages ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.title || p.url}
              </option>
            ))}
          </select>
        )}

        <button
          onClick={() => run.mutate()}
          disabled={projectId == null || run.isPending}
          className="ml-auto rounded-md bg-eclerx-red px-4 py-2 text-sm font-medium text-white hover:bg-eclerx-red-dark disabled:opacity-40"
        >
          {run.isPending ? "Synthesizing…" : "Run synthesis"}
        </button>
      </div>

      {run.isError && (
        <div className="rounded-lg border border-eclerx-red/40 bg-eclerx-red/10 p-3 text-sm text-eclerx-red">
          {(run.error as Error).message.includes("409")
            ? "No completed crawl/modules yet — run Ingestion and module analyses first."
            : (run.error as Error).message}
        </div>
      )}

      {report && (
        <div className="space-y-6">
          {/* Scores + exports */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-4 rounded-lg border border-navy-800 bg-navy-900 p-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-navy-700">
                <span className={"text-2xl font-bold " + (STATUS_COLOR[report.status] ?? "")}>
                  {report.overall_score}
                </span>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-slate-500">Overall</div>
                <div className={"text-lg font-semibold capitalize " + STATUS_COLOR[report.status]}>
                  {report.status}
                </div>
                <div className="text-[11px] text-slate-500">
                  synthesis: {report.synthesis_source}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <a
                href={leadershipExportUrl(projectId!, "xlsx", report.scope)}
                className="flex items-center gap-2 rounded-md border border-navy-700 px-3 py-2 text-sm text-slate-200 hover:bg-navy-800"
              >
                <Download size={16} /> Master Excel
              </a>
              <a
                href={leadershipExportUrl(projectId!, "pdf", report.scope)}
                className="flex items-center gap-2 rounded-md border border-navy-700 px-3 py-2 text-sm text-slate-200 hover:bg-navy-800"
              >
                <FileText size={16} /> Leadership PDF
              </a>
              <a
                href={deckUrl(projectId!, report.scope)}
                className="flex items-center gap-2 rounded-md bg-eclerx-red px-3 py-2 text-sm font-medium text-white hover:bg-eclerx-red-dark"
              >
                <Presentation size={16} /> Download Pitch Deck
              </a>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <LayerBar label="Foundational SEO" score={report.layer_scores.SEO} />
            <LayerBar label="AEO" score={report.layer_scores.AEO} />
            <LayerBar label="GEO" score={report.layer_scores.GEO} />
          </div>

          <div className="rounded-lg border border-navy-800 bg-navy-900 p-4 text-sm text-slate-300">
            {report.executive_summary}
          </div>

          {/* Module score cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {report.modules.map((m) => (
              <div key={m.key} className="rounded-lg border border-navy-800 bg-navy-900 p-3">
                <div className="text-xs text-slate-400">{m.title}</div>
                <div className={"text-xl font-bold " + (STATUS_COLOR[m.status] ?? "")}>
                  {m.score}
                </div>
                <div className="text-[10px] uppercase text-slate-500">{m.layer}</div>
              </div>
            ))}
          </div>

          {/* Roadmap grouped by phase */}
          <div className="space-y-4">
            {(["SEO", "AEO", "GEO"] as const).map((phase) => {
              const items = report.roadmap.filter((i) => i.phase === phase);
              if (!items.length) return null;
              return (
                <div key={phase}>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                    {PHASE_LABEL[phase]}
                  </h3>
                  <div className="space-y-2">
                    {items.map((i) => (
                      <div
                        key={i.order}
                        className="rounded-lg border border-navy-800 bg-navy-900 p-3"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-500">#{i.order}</span>
                          <span
                            className={
                              "rounded px-2 py-0.5 text-[10px] uppercase " +
                              (PRIORITY_COLOR[i.priority] ?? "")
                            }
                          >
                            {i.priority}
                          </span>
                          <span className="font-medium text-slate-100">{i.action}</span>
                          <span className="ml-auto text-[10px] uppercase text-slate-600">
                            {i.module}
                          </span>
                        </div>
                        {i.how_to && <div className="mt-1 text-sm text-slate-400">{i.how_to}</div>}
                        {i.rationale && (
                          <div className="mt-1 text-xs italic text-slate-500">{i.rationale}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Benchmarks with sourced hover tooltips */}
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Benchmark markers (hover for source)
            </h3>
            <div className="flex flex-wrap gap-2">
              {report.benchmarks.map((b) => (
                <span
                  key={b.metric}
                  title={b.source + (b.source_url ? ` — ${b.source_url}` : "")}
                  className="flex items-center gap-1 rounded-md border border-navy-700 bg-navy-900 px-2 py-1 text-xs text-slate-300"
                >
                  <Info size={12} className="text-eclerx-red" />
                  {b.metric}: {b.value ?? "—"}
                  {b.unit ? ` ${b.unit}` : ""}
                </span>
              ))}
            </div>
          </div>

          {report.competitor_summary.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Top competitor gaps
              </h3>
              <div className="overflow-x-auto rounded-lg border border-navy-800">
                <table className="w-full text-left text-sm">
                  <thead className="bg-navy-900 text-slate-400">
                    <tr>
                      <th className="px-3 py-2">Competitor</th>
                      <th className="px-3 py-2">Signal</th>
                      <th className="px-3 py-2">Us</th>
                      <th className="px-3 py-2">Them</th>
                      <th className="px-3 py-2">Gap</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    {report.competitor_summary.map((d, i) => (
                      <tr key={i} className="border-t border-navy-800">
                        <td className="px-3 py-2">{d.competitor}</td>
                        <td className="px-3 py-2">{d.signal.replace(/_/g, " ")}</td>
                        <td className="px-3 py-2">{String(d.us)}</td>
                        <td className="px-3 py-2">{String(d.them)}</td>
                        <td className="px-3 py-2 text-eclerx-red">{String(d.gap)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
