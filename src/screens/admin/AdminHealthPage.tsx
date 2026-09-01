import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";

export default function AdminHealthPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const health = await api.admin.health();
        if (!cancelled) {
          setData(health);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Falha");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const webhooks = (data?.recentWebhooks || []) as Array<Record<string, unknown>>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Saúde da plataforma</h1>
        <p className="text-sm text-zinc-400">
          Checagens leves no backend. Para APM/alertas use Sentry ou o painel Render.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {data && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatusCard label="Aplicação" value={String(data.app)} ok={data.app === "ok"} />
          <StatusCard label="Banco (subscriptions)" value={String(data.database)} ok={data.database === "ok"} />
          <StatusCard
            label="Asaas API key"
            value={data.asaasConfigured ? "configurada" : "ausente"}
            ok={Boolean(data.asaasConfigured)}
          />
          <StatusCard
            label="Asaas base URL"
            value={String(data.asaasBaseUrl || "—")}
            ok={!String(data.asaasBaseUrl || "").includes("sandbox")}
          />
          <StatusCard
            label="Webhook token"
            value={data.webhookTokenConfigured ? "configurado" : "ausente"}
            ok={Boolean(data.webhookTokenConfigured)}
          />
          <StatusCard
            label="Allowlist admin"
            value={data.adminAllowlistConfigured ? "configurada" : "ausente"}
            ok={Boolean(data.adminAllowlistConfigured)}
          />
          <StatusCard
            label="Docs API expostos"
            value={data.docsExposed ? "sim (risco)" : "não"}
            ok={!data.docsExposed}
          />
          <StatusCard
            label="Webhooks não processados"
            value={String(data.unprocessedWebhooks ?? 0)}
            ok={Number(data.unprocessedWebhooks ?? 0) === 0}
          />
          <StatusCard
            label="Webhook Typebot"
            value={data.typebotWebhookConfigured ? "configurado" : "ausente"}
            ok={Boolean(data.typebotWebhookConfigured)}
          />
          <StatusCard
            label="Chamados abertos"
            value={String(data.ticketsOpen ?? 0)}
            ok={Number(data.ticketsOpen ?? 0) === 0}
          />
          <StatusCard
            label="Assinaturas inadimplentes"
            value={String(data.pastDueSubscriptions ?? 0)}
            ok={Number(data.pastDueSubscriptions ?? 0) === 0}
          />
          <StatusCard
            label="Sites conectados"
            value={String(data.sitesTotal ?? 0)}
            ok={Number(data.sitesTotal ?? 0) >= 0}
          />
        </div>
      )}

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
        <h2 className="mb-3 text-sm font-semibold text-zinc-300">Últimos webhooks Asaas</h2>
        {webhooks.length === 0 ? (
          <p className="text-sm text-zinc-500">Nenhum evento registrado.</p>
        ) : (
          <ul className="max-h-80 space-y-2 overflow-auto text-sm">
            {webhooks.map((w) => (
              <li
                key={String(w.event_id)}
                className="flex flex-wrap justify-between gap-2 border-b border-white/5 py-2"
              >
                <span>{String(w.event_type)}</span>
                <span className="text-zinc-500">
                  {w.processed_at ? "processado" : "pendente"} ·{" "}
                  {formatDate(w.received_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function StatusCard({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`mt-2 text-sm font-semibold ${ok ? "text-green-400" : "text-amber-400"}`}>
        {value}
      </p>
    </div>
  );
}

function formatDate(value: unknown): string {
  if (!value || typeof value !== "string") return "—";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch {
    return value;
  }
}
