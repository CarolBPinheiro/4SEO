import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { ErrorBanner, PageHeader, Panel, StatusBadge } from "./ui";
import { CYCLE_LABELS, formatDate, formatMoney, planLabel, str } from "./format";

export default function AdminUserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [planId, setPlanId] = useState("pro");
  const [cycle, setCycle] = useState("monthly");
  const [reason, setReason] = useState("");

  const load = async () => {
    if (!userId) return;
    try {
      const detail = await api.admin.user(userId);
      setData(detail);
      const first = ((detail.subscriptions || []) as Array<Record<string, unknown>>)[0];
      if (first) {
        setPlanId(str(first.plan_id || "pro"));
        setCycle(str(first.billing_cycle || "monthly"));
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar");
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const subscriptions = (data?.subscriptions || []) as Array<Record<string, unknown>>;
  const timeline = (data?.timeline || []) as Array<Record<string, unknown>>;
  const tickets = (data?.tickets || []) as Array<Record<string, unknown>>;
  const current = subscriptions[0];

  const changePlan = async () => {
    if (!current?.id) return;
    try {
      await api.admin.changePlan(str(current.id), { planId, billingCycle: cycle, reason: reason || undefined });
      toast.success("Plano atualizado");
      setReason("");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao alterar plano");
    }
  };

  const cancel = async () => {
    if (!current?.id) return;
    if (reason.trim().length < 3) {
      toast.error("Informe o motivo do cancelamento");
      return;
    }
    try {
      await api.admin.cancelSubscription(str(current.id), reason.trim());
      toast.success("Assinatura cancelada");
      setReason("");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao cancelar");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Assinante"
        title={str(data?.email || userId)}
        subtitle="Conta, plano, histórico e chamados deste usuário."
        actions={
          <Link to="/admin/users" className="text-sm text-zinc-400 hover:text-white">
            ← Assinantes
          </Link>
        }
      />
      <ErrorBanner message={error} />
      {!data && !error ? <p className="text-sm text-zinc-400">Carregando…</p> : null}

      {data ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Conta">
              <Row label="ID" value={str(data.id)} />
              <Row label="E-mail" value={str(data.email || "—")} />
              <Row label="Criado" value={formatDate(data.createdAt)} />
              <Row label="Último acesso" value={formatDate(data.lastSignInAt)} />
            </Panel>
            <Panel title="Plano atual">
              {current ? (
                <>
                  <Row label="Status" value={<StatusBadge status={current.status} />} />
                  <Row label="Plano" value={`${planLabel(current.plan_id)} · ${CYCLE_LABELS[str(current.billing_cycle)] || str(current.billing_cycle)}`} />
                  <Row label="Valor" value={formatMoney(current.amount)} />
                  <Row label="Vencimento" value={formatDate(current.current_period_end)} />
                  <div className="mt-4 grid gap-2">
                    <select value={planId} onChange={(e) => setPlanId(e.target.value)} className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm">
                      <option value="start">Start</option>
                      <option value="pro">Pro</option>
                      <option value="scale">Scale</option>
                    </select>
                    <select value={cycle} onChange={(e) => setCycle(e.target.value)} className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm">
                      <option value="monthly">Mensal</option>
                      <option value="quarterly">Trimestral</option>
                      <option value="semiannual">Semestral</option>
                      <option value="annual">Anual</option>
                    </select>
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Motivo da alteração ou cancelamento"
                      className="min-h-20 rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
                    />
                    <div className="flex gap-2">
                      <Button className="btn-gradient" onClick={() => void changePlan()}>
                        Aplicar plano
                      </Button>
                      <Button variant="outline" className="border-red-500/30 bg-transparent text-red-300" onClick={() => void cancel()}>
                        Cancelar assinatura
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-zinc-500">Sem assinatura vinculada.</p>
              )}
            </Panel>
          </div>

          <Panel title="Linha do tempo">
            {timeline.length === 0 ? (
              <p className="text-sm text-zinc-500">Sem eventos.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {timeline.map((event, index) => (
                  <li key={`${event.at}-${index}`} className="flex justify-between gap-4 border-b border-white/5 py-2">
                    <span>{str(event.label)}</span>
                    <span className="shrink-0 text-zinc-500">{formatDate(event.at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Chamados deste usuário">
            {tickets.length === 0 ? (
              <p className="text-sm text-zinc-500">Nenhum chamado Typebot.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {tickets.map((ticket) => (
                  <li key={str(ticket.id)} className="border-b border-white/5 py-2">
                    {str(ticket.subject)} · {str(ticket.status)} · {formatDate(ticket.opened_at)}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/5 py-2 text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="break-all text-right">{value}</span>
    </div>
  );
}
