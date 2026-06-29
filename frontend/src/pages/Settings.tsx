import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle } from "lucide-react";
import { apiGet, apiSend, type ApiKeyOut, type ProviderOut } from "@/lib/api";

function ProviderRow({
  provider,
  current,
  onSaved,
}: {
  provider: ProviderOut;
  current?: ApiKeyOut;
  onSaved: () => void;
}) {
  const [value, setValue] = useState("");
  const save = useMutation({
    mutationFn: () =>
      apiSend("PUT", "/settings/keys", { provider: provider.key, value }),
    onSuccess: () => {
      setValue("");
      onSaved();
    },
  });

  const display =
    provider.kind === "url"
      ? (current?.value ?? "not set")
      : (current?.masked_value ?? "not set");

  return (
    <div className="rounded-lg border border-navy-800 bg-navy-900 p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-100">{provider.label}</span>
            {provider.required ? (
              <span className="rounded bg-eclerx-red/15 px-1.5 py-0.5 text-[10px] uppercase text-eclerx-red">
                required
              </span>
            ) : (
              <span className="rounded bg-navy-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">
                optional
              </span>
            )}
          </div>
          {provider.help && <div className="mt-0.5 text-xs text-slate-500">{provider.help}</div>}
          <div className="mt-1 font-mono text-xs text-slate-400">{display}</div>
        </div>
        {provider.configured ? (
          <CheckCircle2 size={18} className="text-emerald-400" />
        ) : (
          <Circle size={18} className="text-slate-600" />
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          type={provider.kind === "url" ? "text" : "password"}
          placeholder={provider.kind === "url" ? "https://…" : `Enter ${provider.label}`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="flex-1 rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-eclerx-red focus:outline-none"
        />
        <button
          onClick={() => save.mutate()}
          disabled={!value.trim() || save.isPending}
          className="rounded-md bg-eclerx-red px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-eclerx-red-dark disabled:opacity-40"
        >
          {save.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}

export function Settings() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["api-keys"] });
    qc.invalidateQueries({ queryKey: ["providers"] });
  };

  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: () => apiGet<ProviderOut[]>("/settings/providers"),
  });
  const { data: keys } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiGet<ApiKeyOut[]>("/settings/keys"),
  });

  const byProvider = (k: string) => keys?.find((x) => x.provider === k);
  const core = providers?.filter((p) => p.group === "core") ?? [];
  const optional = providers?.filter((p) => p.group === "optional_llm") ?? [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-slate-400">
          Bring your own keys. Secrets are stored encrypted at rest (Fernet); only a masked
          preview is ever returned.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Core integrations
        </h2>
        {core.map((p) => (
          <ProviderRow key={p.key} provider={p} current={byProvider(p.key)} onSaved={invalidate} />
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Optional LLM providers (GEO audit)
        </h2>
        {optional.map((p) => (
          <ProviderRow key={p.key} provider={p} current={byProvider(p.key)} onSaved={invalidate} />
        ))}
      </section>
    </div>
  );
}
