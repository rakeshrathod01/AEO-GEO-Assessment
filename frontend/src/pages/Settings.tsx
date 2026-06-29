import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend, type ApiKeyOut } from "@/lib/api";

const PROVIDERS = [
  { key: "anthropic", label: "Anthropic (Claude)" },
  { key: "firecrawl", label: "Firecrawl" },
  { key: "ahrefs", label: "Ahrefs" },
];

export function Settings() {
  const qc = useQueryClient();
  const { data: keys } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiGet<ApiKeyOut[]>("/settings/keys"),
  });

  const [values, setValues] = useState<Record<string, string>>({});

  const saveKey = useMutation({
    mutationFn: (provider: string) =>
      apiSend("PUT", "/settings/keys", { provider, value: values[provider] }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-keys"] });
      setValues({});
    },
  });

  const masked = (provider: string) =>
    keys?.find((k) => k.provider === provider)?.masked_value ?? "not set";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">
          Bring your own keys. Stored encrypted at rest (Fernet); only a masked preview is
          ever returned.
        </p>
      </header>

      <div className="space-y-4">
        {PROVIDERS.map((p) => (
          <div key={p.key} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-800">{p.label}</div>
                <div className="font-mono text-xs text-slate-400">{masked(p.key)}</div>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <input
                type="password"
                placeholder={`Enter ${p.label} API key`}
                value={values[p.key] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [p.key]: e.target.value }))}
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand focus:outline-none"
              />
              <button
                onClick={() => saveKey.mutate(p.key)}
                disabled={!values[p.key] || saveKey.isPending}
                className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
