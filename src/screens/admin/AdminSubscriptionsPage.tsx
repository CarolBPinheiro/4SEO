import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { ErrorBanner, PageHeader, Panel, StatusBadge } from "./ui";
import { CYCLE_LABELS, formatDate, formatMoney, planLabel, str } from "./format";

export default function AdminSubscriptionsPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "all";
  const plan = params.get("plan") || "";
  const expiring = params.get("expiring") === "1";
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState<Record<string, unknown> | null>(null);
  const [planId, setPlanId] = useState("pro");
  const [cycle, setCycle] = useState("monthly");
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"change" | "cancel" | null>(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.admin.subscriptions({
        status,
        plan: plan || undefined,
        expiringDays: expiring ? 14 : undefined,
        page: 1,
        perPage: 100,
      });
      setItems(res.items || []);
      setTotal(res.total || 0);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao listar assinaturas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, plan, expiring]);

  const submit = async () => {
    if (!target?.id) return;
    setSaving(true);
    try {
      if (mode === "cancel") {
        if (reason.trim().length < 3) {
          toast.error("Informe o motivo do cancelamento");
          return;
        }
        await api.admin.cancelSubscription(str(target.id), reason.trim());
        toast.success("Assinatura cancelada");
      } else {
        await api.admin.changePlan(str(target.id), {
          planId,
          billingCycle: cycle,
          reason: reason.trim() || undefined,
        });
        toast.success("Plano atualizado");
      }
      setMode(null);
      setTarget(null);
      setReason("");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Comercial"
        title="Planos e assinaturas"
        subtitle="Upgrade, downgrade, vencimentos e cancelamentos com motivo."
      />
      <div className="flex flex-wrap gap-3">
        <select
          value={status}
          onChange={(e) => {
            params.set("status", e.target.value);
            setParams(params);
          }}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="all">Todos os status</option>
          <option value="active">Ativas</option>
          <option value="trialing">Trial</option>
          <option value="past_due">Inadimplentes</option>
          <option value="canceled">Canceladas</option>
          <option value="inactive">Inativas</option>
        </select>
        <select
          value={plan}
          onChange={(e) => {
            if (e.target.value) params.set("plan", e.target.value);
            else params.delete("plan");
            setParams(params);
          }}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="">Todos os planos</option>
          <option value="start">Start</option>
          <option value="pro">Pro</option>
          <option value="scale">Scale</option>
        </select>
        <Button
          variant={expiring ? "default" : "outline"}
          className={expiring ? "btn-gradient" : "border-white/15 bg-transparent"}
          onClick={() => {
            if (expiring) params.delete("expiring");
            else params.set("expiring", "1");
            setParams(params);
          }}
        >
          Vencem em 14 dias
        </Button>
      </div>
      <ErrorBanner message={error} />
      <Panel title={`${total} assinatura(s)`}>
        {loading ? (
          <p className="text-sm text-zinc-400">Carregando…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-zinc-500">Nenhuma assinatura neste filtro.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-zinc-500">
                <tr>
                  <th className="pb-2 font-medium">Assinante</th>
                  <th className="pb-2 font-medium">Plano</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Valor</th>
                  <th className="pb-2 font-medium">Vencimento</th>
                  <th className="pb-2 font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((sub) => (
                  <tr key={str(sub.id)} className="border-t border-white/5">
                    <td className="py-3">
                      {sub.user_id ? (
                        <Link className="text-[#ff8a3d] hover:underline" to={`/admin/users/${sub.user_id}`}>
                          {str(sub.user_email || sub.user_id)}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      {planLabel(sub.plan_id)} · {CYCLE_LABELS[str(sub.billing_cycle)] || str(sub.billing_cycle)}
                    </td>
                    <td>
                      <StatusBadge status={sub.status} />
                    </td>
                    <td>{formatMoney(sub.amount)}</td>
                    <td className="text-zinc-400">{formatDate(sub.current_period_end)}</td>
                    <td className="space-x-2">
                      <button
                        type="button"
                        className="text-xs text-[#ff8a3d]"
                        onClick={() => {
                          setTarget(sub);
                          setPlanId(str(sub.plan_id || "pro"));
                          setCycle(str(sub.billing_cycle || "monthly"));
                          setMode("change");
                        }}
                      >
                        Alterar
                      </button>
                      <button
                        type="button"
                        className="text-xs text-red-300"
                        onClick={() => {
                          setTarget(sub);
                          setMode("cancel");
                        }}
                      >
                        Cancelar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {mode && target ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#111] p-5">
            <h3 className="text-lg font-semibold">
              {mode === "cancel" ? "Cancelar assinatura" : "Alterar plano"}
            </h3>
            <p className="mt-1 text-sm text-zinc-400">{str(target.user_email || target.user_id)}</p>
            {mode === "change" ? (
              <div className="mt-4 grid gap-3">
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
              </div>
            ) : null}
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={mode === "cancel" ? "Motivo do cancelamento" : "Motivo da alteração (opcional)"}
              className="mt-3 min-h-24 w-full rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" className="border-white/15 bg-transparent" onClick={() => setMode(null)}>
                Fechar
              </Button>
              <Button className="btn-gradient" disabled={saving} onClick={() => void submit()}>
                Confirmar
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
