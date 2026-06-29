import { useQuery } from "@tanstack/react-query";
import { apiGet, type HealthOut } from "@/lib/api";
import { MODULES } from "@/lib/modules";

export function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthOut>("/health"),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Leadership Dashboard</h1>
        <p className="text-sm text-slate-500">
          Enterprise SEO / AEO / GEO assessment — cross-module synthesis lands in Phase 6.
        </p>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="text-sm font-medium text-slate-700">Backend status</div>
        <div className="mt-1 text-sm text-slate-500">
          {health
            ? `${health.app} v${health.version} · ${health.env} · ${health.database}`
            : "Connecting to API…"}
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Modules
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => (
            <div key={m.key} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div className="font-medium text-slate-800">{m.title}</div>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] uppercase text-slate-500">
                  {m.layer}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-400">Implemented in Phase {m.phase}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
