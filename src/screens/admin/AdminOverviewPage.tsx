import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { ErrorBanner, KpiCard, PageHeader, Panel } from "./ui";
import { formatMoney, num, planLabel, str } from "./format";

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
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Falha ao carregar");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const series = (data?.series || []) as Array<Record<string, unknown>>;
  const plans = (data?.plans || []) as Array<Record<string, unknown>>;
  const alerts = (data?.alerts || []) as Array<Record<string, string>>;
  const expiring = (data?.expiringSoon || []) as Array<Record<string, unknown>>;
  const ticketsByStatus = (data?.ticketsByStatus || {}) as Record<string, number>;

  const chartData = useMemo(
    () =>
      series.map((row) => ({
        date: String(row.date || "").slice(5),
        novas: num(row.newSubscriptions),
        canceladas: num(row.canceled),
        base: num(row.subscriberBase),
        mrrIn: num(row.revenueNew),
        mrrOut: num(row.revenueLost),
      })),
    [series]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Centro de controle"
        title="Operação da plataforma"
        subtitle="Assinantes, receita, chamados e saúde em um só lugar."
        actions={
          <div className="flex gap-2">
            {(["7d", "30d", "90d", "12m"] as Period[]).map((item) => (
              <Button
                key={item}
                size="sm"
                variant={period === item ? "default" : "outline"}
                className={period === item ? "btn-gradient" : "border-white/15 bg-transparent"}
                onClick={() => setPeriod(item)}
              >
                {item}
              </Button>
            ))}
          </div>
        }
      />

      <ErrorBanner message={error} />

      {loading && !data ? (
        <p className="text-sm text-zinc-400">Carregando o painel…</p>
      ) : (
        <>
          {alerts.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {alerts.map((alert) => (
                <Link
                  key={alert.code}
                  to={alert.href || "/admin"}
                  className={`rounded-xl border p-4 text-sm ${
                    alert.severity === "critical"
                      ? "border-red-500/30 bg-red-500/10 text-red-100"
                      : alert.severity === "warning"
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
                        : "border-white/10 bg-white/5 text-zinc-300"
                  }`}
                >
                  {alert.message}
                </Link>
              ))}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Assinantes ativos" value={num(data?.subscribersActive).toLocaleString("pt-BR")} hint={`${num(data?.subscribersTotal)} com histórico de plano`} tone="ok" />
            <KpiCard label="Inativos" value={num(data?.subscribersInactive).toLocaleString("pt-BR")} />
            <KpiCard label="Cancelados" value={num(data?.subscribersCanceled).toLocaleString("pt-BR")} tone="warn" />
            <KpiCard label="Novos no período" value={num(data?.subscriptionsNewInPeriod).toLocaleString("pt-BR")} hint={`Contas novas: ${num(data?.usersNewInPeriod)}`} />
            <KpiCard label="MRR estimado" value={formatMoney(data?.estimatedMrr)} hint={`Ticket médio ${formatMoney(data?.arpu)}`} />
            <KpiCard label="Churn no período" value={`${num(data?.churnRate).toLocaleString("pt-BR")}%`} tone={num(data?.churnRate) > 8 ? "danger" : "default"} />
            <KpiCard label="Chamados abertos" value={num(data?.ticketsOpen).toLocaleString("pt-BR")} hint={`${num(ticketsByStatus.new)} novos`} tone={num(data?.ticketsOpen) > 0 ? "warn" : "ok"} />
            <KpiCard label="Webhooks pendentes" value={num(data?.unprocessedWebhooks).toLocaleString("pt-BR")} tone={num(data?.unprocessedWebhooks) > 0 ? "danger" : "ok"} />
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Evolução da base" className="xl:col-span-2">
              {chartData.length === 0 ? (
                <p className="text-sm text-zinc-500">Sem movimento no período.</p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                      <YAxis stroke="#71717a" fontSize={11} />
                      <Tooltip contentStyle={{ background: "#111", border: "1px solid #333" }} />
                      <Area type="monotone" dataKey="base" stroke="#ff8a3d" fill="rgba(255,138,61,0.2)" name="Base" />
                      <Area type="monotone" dataKey="novas" stroke="#34d399" fill="rgba(52,211,153,0.12)" name="Novas" />
                      <Area type="monotone" dataKey="canceladas" stroke="#f87171" fill="rgba(248,113,113,0.12)" name="Canceladas" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>
            <Panel title="Receita por plano" action={<Link to="/admin/subscriptions" className="text-xs text-[#ff8a3d]">Ver planos</Link>}>
              {plans.length === 0 ? (
                <p className="text-sm text-zinc-500">Sem planos ativos.</p>
              ) : (
                <div className="space-y-3">
                  {plans.map((plan) => (
                    <div key={str(plan.id)} className="flex items-center justify-between text-sm">
                      <div>
                        <p className="font-medium">{planLabel(plan.id)}</p>
                        <p className="text-xs text-zinc-500">{num(plan.users)} assinantes</p>
                      </div>
                      <p className="font-semibold">{formatMoney(plan.mrr)}</p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Receita nova vs. perdida" className="xl:col-span-2">
              {chartData.length === 0 ? (
                <p className="text-sm text-zinc-500">Sem eventos financeiros no período.</p>
              ) : (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                      <YAxis stroke="#71717a" fontSize={11} />
                      <Tooltip contentStyle={{ background: "#111", border: "1px solid #333" }} />
                      <Bar dataKey="mrrIn" fill="#34d399" name="MRR novo" radius={4} />
                      <Bar dataKey="mrrOut" fill="#f87171" name="MRR perdido" radius={4} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>
            <Panel title="Chamados" action={<Link to="/admin/tickets" className="text-xs text-[#ff8a3d]">Kanban</Link>}>
              <div className="space-y-3 text-sm">
                {[
                  ["new", "Novos"],
                  ["in_progress", "Em atendimento"],
                  ["waiting_customer", "Aguardando cliente"],
                  ["resolved", "Resolvidos"],
                ].map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-zinc-400">{label}</span>
                    <span className="font-semibold">{num(ticketsByStatus[key])}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <Panel title="Assinaturas próximas do vencimento" action={<Link to="/admin/subscriptions?expiring=1" className="text-xs text-[#ff8a3d]">Ver lista</Link>}>
            {expiring.length === 0 ? (
              <p className="text-sm text-zinc-500">Nenhuma renovação crítica nos próximos 14 dias.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-zinc-500">
                    <tr>
                      <th className="pb-2 font-medium">Usuário</th>
                      <th className="pb-2 font-medium">Plano</th>
                      <th className="pb-2 font-medium">Vencimento</th>
                      <th className="pb-2 font-medium">MRR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expiring.map((row) => (
                      <tr key={str(row.subscriptionId)} className="border-t border-white/5">
                        <td className="py-2">
                          <Link className="text-[#ff8a3d] hover:underline" to={`/admin/users/${row.userId}`}>
                            {str(row.userId).slice(0, 8)}…
                          </Link>
                        </td>
                        <td>{planLabel(row.planId)}</td>
                        <td className="text-zinc-400">{str(row.currentPeriodEnd).slice(0, 10)}</td>
                        <td>{formatMoney(row.amountMonthly)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
