import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Upload, XCircle } from "lucide-react";
import {
  apiGet,
  apiSend,
  apiUpload,
  type JobOut,
  type PageOut,
  type Project,
} from "@/lib/api";
import { useJobStream } from "@/hooks/useJobStream";

type Mode = "sitemap" | "paste" | "excel";

function ProjectPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number) => void;
}) {
  const qc = useQueryClient();
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiGet<Project[]>("/projects"),
  });
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [competitors, setCompetitors] = useState("");

  const create = useMutation({
    mutationFn: () =>
      apiSend<Project>("POST", "/projects", {
        name,
        target_url: target,
        competitors: competitors
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean)
          .map((url) => ({ name: url, url })),
      }),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      if (p) onChange(p.id);
      setCreating(false);
      setName("");
      setTarget("");
      setCompetitors("");
    },
  });

  useEffect(() => {
    if (value == null && projects && projects.length) onChange(projects[0].id);
  }, [projects, value, onChange]);

  return (
    <div className="rounded-lg border border-navy-800 bg-navy-900 p-4">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Project
        </label>
        <button
          onClick={() => setCreating((c) => !c)}
          className="text-xs text-eclerx-red hover:underline"
        >
          {creating ? "Cancel" : "+ New project"}
        </button>
      </div>

      {!creating ? (
        <select
          value={value ?? ""}
          onChange={(e) => onChange(Number(e.target.value))}
          className="mt-2 w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
        >
          {(projects ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} — {p.target_url}
            </option>
          ))}
          {!projects?.length && <option>No projects yet — create one</option>}
        </select>
      ) : (
        <div className="mt-3 space-y-2">
          <input
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
          />
          <input
            placeholder="Target URL (https://client.com)"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
          />
          <input
            placeholder="Competitor URLs (comma separated, 3–5)"
            value={competitors}
            onChange={(e) => setCompetitors(e.target.value)}
            className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
          />
          <button
            onClick={() => create.mutate()}
            disabled={!name || !target || create.isPending}
            className="rounded-md bg-eclerx-red px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            Create project
          </button>
        </div>
      )}
    </div>
  );
}

const tabClass = (active: boolean) =>
  "rounded-md px-3 py-1.5 text-sm transition-colors " +
  (active ? "bg-eclerx-red text-white" : "text-slate-400 hover:bg-navy-800");

export function Ingestion() {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>("sitemap");
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [topN, setTopN] = useState(50);
  const [jobId, setJobId] = useState<number | null>(null);

  const start = useMutation({
    mutationFn: async (): Promise<JobOut> => {
      if (projectId == null) throw new Error("Pick a project first");
      if (mode === "sitemap") {
        return (await apiSend<JobOut>("POST", `/projects/${projectId}/ingest/sitemap`, {
          sitemap_url: sitemapUrl,
          top_n: topN,
        })) as JobOut;
      }
      if (mode === "paste") {
        return (await apiSend<JobOut>("POST", `/projects/${projectId}/ingest/paste`, {
          text: pasteText,
          top_n: topN,
        })) as JobOut;
      }
      const form = new FormData();
      form.append("file", file as File);
      form.append("top_n", String(topN));
      return apiUpload<JobOut>(`/projects/${projectId}/ingest/excel`, form);
    },
    onSuccess: (job) => setJobId(job.id),
  });

  const canSubmit =
    projectId != null &&
    ((mode === "sitemap" && sitemapUrl.trim()) ||
      (mode === "paste" && pasteText.trim()) ||
      (mode === "excel" && file));

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Ingestion</h1>
        <p className="text-sm text-slate-400">
          Pull the client's top-{topN} business-critical pages (and comparable competitor
          pages) via Firecrawl, falling back to Playwright-stealth on bot-gated pages.
        </p>
      </header>

      <ProjectPicker value={projectId} onChange={setProjectId} />

      <div className="rounded-lg border border-navy-800 bg-navy-900 p-4">
        <div className="flex gap-2">
          <button className={tabClass(mode === "sitemap")} onClick={() => setMode("sitemap")}>
            Sitemap URL
          </button>
          <button className={tabClass(mode === "paste")} onClick={() => setMode("paste")}>
            Paste URLs
          </button>
          <button className={tabClass(mode === "excel")} onClick={() => setMode("excel")}>
            Excel upload
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {mode === "sitemap" && (
            <input
              placeholder="https://client.com/sitemap.xml"
              value={sitemapUrl}
              onChange={(e) => setSitemapUrl(e.target.value)}
              className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100"
            />
          )}
          {mode === "paste" && (
            <textarea
              placeholder="Paste up to 50 URLs (one per line)…"
              rows={6}
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 font-mono text-xs text-slate-100"
            />
          )}
          {mode === "excel" && (
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-navy-700 bg-navy-950 px-3 py-4 text-sm text-slate-400">
              <Upload size={16} />
              {file ? file.name : "Choose an .xlsx file with a URL column"}
              <input
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          )}

          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500">Top N</label>
            <input
              type="number"
              min={1}
              max={200}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="w-20 rounded-md border border-navy-700 bg-navy-950 px-2 py-1 text-sm text-slate-100"
            />
            <button
              onClick={() => start.mutate()}
              disabled={!canSubmit || start.isPending}
              className="ml-auto rounded-md bg-eclerx-red px-4 py-2 text-sm font-medium text-white hover:bg-eclerx-red-dark disabled:opacity-40"
            >
              {start.isPending ? "Starting…" : "Start ingestion"}
            </button>
          </div>
          {start.isError && (
            <div className="text-sm text-eclerx-red">{(start.error as Error).message}</div>
          )}
        </div>
      </div>

      {jobId != null && <JobProgress jobId={jobId} />}
    </div>
  );
}

function JobProgress({ jobId }: { jobId: number }) {
  const { events, latest, done } = useJobStream(jobId);
  const { data: pages } = useQuery({
    queryKey: ["job-pages", jobId, done],
    queryFn: () => apiGet<PageOut[]>(`/crawl/jobs/${jobId}/pages`),
    enabled: done,
  });

  const percent = latest?.percent ?? 0;
  const failed = latest?.status === "failed";
  const clientPages = useMemo(() => (pages ?? []).filter((p) => !p.is_competitor), [pages]);
  const compPages = useMemo(() => (pages ?? []).filter((p) => p.is_competitor), [pages]);

  return (
    <div className="space-y-4 rounded-lg border border-navy-800 bg-navy-900 p-4">
      <div className="flex items-center gap-3">
        {done && !failed ? (
          <CheckCircle2 className="text-emerald-400" size={18} />
        ) : failed ? (
          <XCircle className="text-eclerx-red" size={18} />
        ) : (
          <Loader2 className="animate-spin text-amber-400" size={18} />
        )}
        <div className="flex-1">
          <div className="h-2 overflow-hidden rounded-full bg-navy-800">
            <div
              className={"h-full transition-all " + (failed ? "bg-eclerx-red" : "bg-emerald-500")}
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
        <span className="w-12 text-right text-sm text-slate-300">{percent}%</span>
      </div>

      <div className="max-h-40 overflow-y-auto rounded bg-navy-950 p-2 font-mono text-xs text-slate-400">
        {events.length === 0 ? (
          <div>Waiting for progress…</div>
        ) : (
          events.map((e, i) => <div key={i}>{e.message}</div>)
        )}
      </div>

      {done && pages && (
        <div className="space-y-2">
          <div className="text-sm text-slate-300">
            {clientPages.length} client pages · {compPages.length} competitor pages
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr>
                  <th className="px-2 py-1">URL</th>
                  <th className="px-2 py-1">Type</th>
                  <th className="px-2 py-1">Method</th>
                  <th className="px-2 py-1">Status</th>
                  <th className="px-2 py-1">Words</th>
                </tr>
              </thead>
              <tbody className="text-slate-300">
                {pages.map((p) => (
                  <tr key={p.id} className="border-t border-navy-800">
                    <td className="max-w-md truncate px-2 py-1">{p.url}</td>
                    <td className="px-2 py-1">{p.is_competitor ? "competitor" : "client"}</td>
                    <td className="px-2 py-1">{p.fetch_method ?? "—"}</td>
                    <td className="px-2 py-1">
                      {p.fetch_ok ? (
                        <span className="text-emerald-400">{p.http_status ?? "ok"}</span>
                      ) : (
                        <span className="text-eclerx-red">fail</span>
                      )}
                    </td>
                    <td className="px-2 py-1">{p.word_count ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
