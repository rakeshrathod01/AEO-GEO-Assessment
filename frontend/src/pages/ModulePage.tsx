import { useParams } from "react-router-dom";
import { MODULES } from "@/lib/modules";

export function ModulePage() {
  const { moduleKey } = useParams();
  const meta = MODULES.find((m) => m.key === moduleKey);

  if (!meta) {
    return <div className="text-slate-500">Unknown module: {moduleKey}</div>;
  }

  return (
    <div className="space-y-4">
      <header>
        <div className="text-xs uppercase tracking-wide text-slate-400">{meta.layer}</div>
        <h1 className="text-2xl font-semibold text-slate-900">{meta.title}</h1>
      </header>

      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm text-slate-500">
          This module is scaffolded. Its analyzer (whole-site top-50 pages + single page,
          with competitor comparison, Excel export, and PDF report) is implemented in{" "}
          <span className="font-medium text-slate-700">Phase {meta.phase}</span>.
        </p>
      </div>
    </div>
  );
}
