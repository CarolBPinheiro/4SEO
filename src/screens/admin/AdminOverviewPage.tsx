import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";

type Period = "7d" | "30d" | "90d" | "12m";

export default function AdminOverviewPage() {
  const [period, setPeriod] = useState<Period>("30d");
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void (async () => {
      try {
        const overview = await api.admin.overview(period);
        if (!cancelled) {
          setData(overview);
          setError("");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Falha ao carregar");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const byStatus = (data?.subscriptionsByStatus || {}) as Record<string, number>;
  const series = (data?.series || []) as Array<{
    date: string;
    newSubscriptions?: number;
    canceled?: number;
  }>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Visão geral</h1>
          <p className="text-sm text-zinc-400">Métricas da plataforma (dados locais + Auth)</p>
        </div>
        <div className="flex gap-2">
          {(["7d", "30d", "90d", "12m"] as Period[]).map((p) => (
            <Button
              key={p}
              size="sm"
              variant={period === p ? "default" : "outline"}
              className={period === p ? "btn-gradient" : "border-white/15 bg-transparent"}
              onClick={() => setPeriod(p)}
            >
              {p}
            </Button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading && !data ? (
        <p className="text-sm text-zinc-400">Carregando…</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric title="Usuários (total)" value={Number(data?.usersTotal ?? 0)} />
            <Metric title="Novos no período" value={Number(data?.usersNewInPeriod ?? 0)} />
            <Metric title="Com assinatura ativa" value={Number(data?.usersWithActiveSubscription ?? 0)} />
            <Metric title="Sem assinatura" value={Number(data?.usersWithoutSubscription ?? 0)} />
            <Metric title="Novas assinaturas" value={Number(data?.subscriptionsNewInPeriod ?? 0)} />
            <Metric title="MRR estimado (R$)" value={Number(data?.estimatedMrr ?? 0)} format="currency" />
            <Metric title="Sites conectados" value={Number(data?.sitesTotal ?? 0)} />
            <Metric title="Webhooks pendentes" value={Number(data?.unprocessedWebhooks ?? 0)} />
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="mb-3 text-sm font-semibold text-zinc-300">Assinaturas por status</h2>
            <div className="flex flex-wrap gap-3">
              {Object.keys(byStatus).length === 0 ? (
                <p className="text-sm text-zinc-500">Sem dados de assinatura ainda.</p>
              ) : (
                Object.entries(byStatus).map(([status, count]) => (
                  <div
                    key={status}
                    className="rounded-lg border border-white/10 px-3 py-2 text-sm"
                  >
                    <span className="text-zinc-400">{status}</span>{" "}
                    <span className="font-semibold">{count}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="mb-3 text-sm font-semibold text-zinc-300">
              Novas assinaturas no período
            </h2>
            {series.length === 0 ? (
              <p className="text-sm text-zinc-500">Sem eventos no período.</p>
            ) : (
              <div className="max-h-64 space-y-2 overflow-auto">
                {series.map((row) => (
                  <div
                    key={row.date}
                    className="flex items-center justify-between border-b border-white/5 py-2 text-sm"
                  >
                    <span className="text-zinc-400">{row.date}</span>
                    <span>
                      +{row.newSubscriptions ?? 0}
                      {(row.canceled ?? 0) > 0 ? (
                        <span className="ml-3 text-red-400">cancel {row.canceled}</span>
                      ) : null}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Metric({
  title,
  value,
  format,
}: {
  title: string;
  value: number;
  format?: "currency";
}) {
  const display =
    format === "currency"
      ? value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
      : value.toLocaleString("pt-BR");
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <p className="text-xs text-zinc-500">{title}</p>
      <p className="mt-2 text-2xl font-bold">{display}</p>
    </div>
  );
}
