import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/apiClient";

export default function AdminUserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    void (async () => {
      try {
        const detail = await api.admin.user(userId);
        if (!cancelled) {
          setData(detail);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Falha");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const subscriptions = (data?.subscriptions || []) as Array<Record<string, unknown>>;
  const checkouts = (data?.checkouts || []) as Array<Record<string, unknown>>;
  const timeline = (data?.timeline || []) as Array<Record<string, unknown>>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/admin/users" className="text-sm text-zinc-400 hover:text-white">
          ← Usuários
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">
          {String(data?.email || userId || "Usuário")}
        </h1>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!data && !error ? (
        <p className="text-sm text-zinc-400">Carregando…</p>
      ) : data ? (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            <Card title="Conta">
              <Row label="ID" value={String(data.id)} />
              <Row label="E-mail" value={String(data.email || "—")} />
              <Row label="Criado" value={formatDate(data.createdAt)} />
              <Row label="Último acesso" value={formatDate(data.lastSignInAt)} />
              <Row label="E-mail confirmado" value={formatDate(data.emailConfirmedAt)} />
            </Card>
            <Card title="Assinatura (mais recente)">
              {subscriptions[0] ? (
                <>
                  <Row label="Status" value={String(subscriptions[0].status)} />
                  <Row label="Plano" value={String(subscriptions[0].plan_id || "—")} />
                  <Row label="Ciclo" value={String(subscriptions[0].billing_cycle || "—")} />
                  <Row label="Valor" value={String(subscriptions[0].amount ?? "—")} />
                  <Row
                    label="Asaas subscription"
                    value={String(subscriptions[0].asaas_subscription_id || "—")}
                  />
                  <Row
                    label="Asaas customer"
                    value={String(subscriptions[0].asaas_customer_id || "—")}
                  />
                  <Row
                    label="Próxima cobrança"
                    value={formatDate(subscriptions[0].current_period_end)}
                  />
                </>
              ) : (
                <p className="text-sm text-zinc-500">Sem assinatura vinculada.</p>
              )}
            </Card>
          </section>

          <Card title="Histórico">
            {timeline.length === 0 ? (
              <p className="text-sm text-zinc-500">Sem eventos.</p>
            ) : (
              <ul className="space-y-2">
                {timeline.map((ev, idx) => (
                  <li
                    key={`${ev.at}-${idx}`}
                    className="flex justify-between gap-4 border-b border-white/5 py-2 text-sm"
                  >
                    <span>{String(ev.label)}</span>
                    <span className="shrink-0 text-zinc-500">{formatDate(ev.at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Checkouts">
            {checkouts.length === 0 ? (
              <p className="text-sm text-zinc-500">Nenhum checkout.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {checkouts.map((c) => (
                  <li key={String(c.id)} className="border-b border-white/5 py-2">
                    {String(c.status)} · {String(c.plan_id)} · {String(c.external_reference)}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
      <h2 className="mb-3 text-sm font-semibold text-zinc-300">{title}</h2>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/5 py-2 text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="break-all text-right">{value}</span>
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
