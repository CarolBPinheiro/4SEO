import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/apiClient";

export default function AdminSubscriptionsPage() {
  const [status, setStatus] = useState("all");
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void (async () => {
      try {
        const res = await api.admin.subscriptions({ status, page: 1, perPage: 50 });
        if (!cancelled) {
          setItems(res.items || []);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Falha");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Assinaturas</h1>
          <p className="text-sm text-zinc-400">
            Estado local sincronizado pelos webhooks Asaas (somente leitura)
          </p>
        </div>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="all">Todas</option>
          <option value="active">Ativas</option>
          <option value="pending">Pendentes</option>
          <option value="past_due">Inadimplentes</option>
          <option value="canceled">Canceladas</option>
          <option value="inactive">Inativas</option>
        </select>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/[0.04] text-zinc-400">
            <tr>
              <th className="px-4 py-3 font-medium">Usuário</th>
              <th className="px-4 py-3 font-medium">Plano</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Valor</th>
              <th className="px-4 py-3 font-medium">Criada</th>
              <th className="px-4 py-3 font-medium">Asaas ID</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-zinc-500">
                  Carregando…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-zinc-500">
                  Nenhuma assinatura.
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={String(s.id)} className="border-t border-white/5">
                  <td className="px-4 py-3">
                    {s.user_id ? (
                      <Link
                        className="text-[#ff8a3d] hover:underline"
                        to={`/admin/users/${s.user_id}`}
                      >
                        {String(s.user_id).slice(0, 8)}…
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3">{String(s.plan_id)}</td>
                  <td className="px-4 py-3">{String(s.status)}</td>
                  <td className="px-4 py-3">{String(s.amount ?? "—")}</td>
                  <td className="px-4 py-3 text-zinc-400">{formatDate(s.created_at)}</td>
                  <td className="px-4 py-3 text-zinc-400">
                    {String(s.asaas_subscription_id || "—")}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
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
