import { useQuery } from "@tanstack/react-query";
import { apiGet, type HealthOut } from "@/lib/api";
import { MODULES } from "@/lib/modules";

export function Dashboard() {
  const { data: health, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthOut>("/health"),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Leadership Dashboard</h1>
        <p className="text-sm text-slate-400">
          Enterprise SEO / AEO / GEO assessment — cross-module synthesis lands in Phase 6.
        </p>
      </header>

      <div className="rounded-lg border border-navy-800 bg-navy-900 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <span
            className={
              "inline-block h-2 w-2 rounded-full " +
              (health ? "bg-emerald-400" : isError ? "bg-eclerx-red" : "bg-amber-400")
            }
          />
          Backend status
        </div>
        <div className="mt-1 text-sm text-slate-400">
          {health
            ? `${health.app} v${health.version} · ${health.env} · ${health.database}`
            : isError
              ? "API unreachable — is the backend running on :8000?"
              : "Connecting to API…"}
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Modules
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => (
            <div
              key={m.key}
              className="rounded-lg border border-navy-800 bg-navy-900 p-4 transition-colors hover:border-navy-700"
            >
              <div className="flex items-center justify-between">
                <div className="font-medium text-slate-100">{m.title}</div>
                <span className="rounded bg-navy-800 px-2 py-0.5 text-[10px] uppercase text-slate-400">
                  {m.layer}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-500">Implemented in Phase {m.phase}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
