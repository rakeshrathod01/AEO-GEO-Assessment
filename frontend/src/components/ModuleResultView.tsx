import { Download, FileText } from "lucide-react";
import { exportUrl, type ModuleResult } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  pass: "text-emerald-400",
  warn: "text-amber-400",
  fail: "text-eclerx-red",
};

const PRIORITY_COLOR: Record<string, string> = {
  high: "bg-eclerx-red/20 text-eclerx-red",
  med: "bg-amber-400/20 text-amber-300",
  low: "bg-slate-500/20 text-slate-300",
};

function ScoreDial({ score, status }: { score: number; status: string }) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-navy-800 bg-navy-900 p-4">
      <div className="relative flex h-20 w-20 items-center justify-center rounded-full border-4 border-navy-700">
        <span className={"text-2xl font-bold " + (STATUS_COLOR[status] ?? "text-slate-200")}>
          {score}
        </span>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wider text-slate-500">Overall score</div>
        <div className={"text-lg font-semibold capitalize " + (STATUS_COLOR[status] ?? "")}>
          {status}
        </div>
      </div>
    </div>
  );
}

export function ModuleResultView({
  result,
  projectId,
  moduleKey,
}: {
  result: ModuleResult;
  projectId: number;
  moduleKey: string;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ScoreDial score={result.score} status={result.status} />
        <div className="flex gap-2">
          <a
            href={exportUrl(projectId, moduleKey, "xlsx", result.scope)}
            className="flex items-center gap-2 rounded-md border border-navy-700 px-3 py-2 text-sm text-slate-200 hover:bg-navy-800"
          >
            <Download size={16} /> Export Excel
          </a>
          <a
            href={exportUrl(projectId, moduleKey, "pdf", result.scope)}
            className="flex items-center gap-2 rounded-md bg-eclerx-red px-3 py-2 text-sm font-medium text-white hover:bg-eclerx-red-dark"
          >
            <FileText size={16} /> Generate PDF
          </a>
        </div>
      </div>

      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Findings
        </h3>
        <div className="overflow-x-auto rounded-lg border border-navy-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-navy-900 text-slate-400">
              <tr>
                <th className="px-3 py-2">Signal</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">Benchmark</th>
                <th className="px-3 py-2">Source</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {result.findings.map((f, i) => (
                <tr key={i} className="border-t border-navy-800">
                  <td className="px-3 py-2">{f.signal.replace(/_/g, " ")}</td>
                  <td className={"px-3 py-2 capitalize " + (STATUS_COLOR[f.status] ?? "")}>
                    {f.status}
                  </td>
                  <td className="px-3 py-2">{String(f.value)}</td>
                  <td className="px-3 py-2">{f.benchmark ?? "—"}</td>
                  <td className="px-3 py-2 text-xs text-slate-500">{f.source ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Recommendations
        </h3>
        <div className="space-y-2">
          {result.recommendations.length === 0 && (
            <div className="text-sm text-slate-500">No issues — everything passes. 🎉</div>
          )}
          {result.recommendations.map((r, i) => (
            <div key={i} className="rounded-lg border border-navy-800 bg-navy-900 p-3">
              <div className="flex items-center gap-2">
                <span
                  className={
                    "rounded px-2 py-0.5 text-[10px] uppercase " +
                    (PRIORITY_COLOR[r.priority] ?? "")
                  }
                >
                  {r.priority}
                </span>
                <span className="rounded bg-navy-800 px-2 py-0.5 text-[10px] uppercase text-slate-400">
                  {r.layer}
                </span>
                <span className="font-medium text-slate-100">{r.action}</span>
              </div>
              {r.how_to && <div className="mt-1 text-sm text-slate-400">{r.how_to}</div>}
              <div className="mt-1 text-xs text-slate-500">
                Effort: {r.effort ?? "—"} · Impact: {r.impact ?? "—"}
              </div>
            </div>
          ))}
        </div>
      </section>

      {result.competitor_delta.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Competitor delta
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
                {result.competitor_delta.map((d, i) => (
                  <tr key={i} className="border-t border-navy-800">
                    <td className="px-3 py-2">{d.competitor}</td>
                    <td className="px-3 py-2">{d.signal.replace(/_/g, " ")}</td>
                    <td className="px-3 py-2">{String(d.us)}</td>
                    <td className="px-3 py-2">{String(d.them)}</td>
                    <td
                      className={
                        "px-3 py-2 " +
                        (typeof d.gap === "number"
                          ? d.gap >= 0
                            ? "text-emerald-400"
                            : "text-eclerx-red"
                          : "")
                      }
                    >
                      {String(d.gap)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
