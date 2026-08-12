import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AdminUsersPage() {
  const [q, setQ] = useState("");
  const [subscription, setSubscription] = useState("all");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.admin.users({ page, perPage: 50, q: q || undefined, subscription });
      setItems(res.items || []);
      setTotal(res.total || 0);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao listar");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, subscription]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Usuários</h1>
        <p className="text-sm text-zinc-400">Auth Supabase + status de assinatura local</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Buscar e-mail"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs border-white/10 bg-white/5"
        />
        <Button variant="outline" className="border-white/15 bg-transparent" onClick={() => { setPage(1); void load(); }}>
          Buscar
        </Button>
        <select
          value={subscription}
          onChange={(e) => {
            setPage(1);
            setSubscription(e.target.value);
          }}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="all">Todas assinaturas</option>
          <option value="active">Ativas (elegíveis)</option>
          <option value="none">Sem assinatura</option>
          <option value="canceled">Canceladas</option>
          <option value="past_due">Inadimplentes</option>
          <option value="pending">Pendentes</option>
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
              <th className="px-4 py-3 font-medium">E-mail</th>
              <th className="px-4 py-3 font-medium">Criado</th>
              <th className="px-4 py-3 font-medium">Último acesso</th>
              <th className="px-4 py-3 font-medium">Assinatura</th>
              <th className="px-4 py-3 font-medium">Plano</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-zinc-500">
                  Carregando…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-zinc-500">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            ) : (
              items.map((u) => (
                <tr key={String(u.id)} className="border-t border-white/5 hover:bg-white/[0.03]">
                  <td className="px-4 py-3">
                    <Link className="text-[#ff8a3d] hover:underline" to={`/admin/users/${u.id}`}>
                      {String(u.email || u.id)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{formatDate(u.createdAt)}</td>
                  <td className="px-4 py-3 text-zinc-400">{formatDate(u.lastSignInAt)}</td>
                  <td className="px-4 py-3">{String(u.subscriptionStatus || "none")}</td>
                  <td className="px-4 py-3 text-zinc-400">{String(u.planId || "—")}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-zinc-400">
        <span>
          Página {page} · {total} no Auth (filtro local pode reduzir a lista)
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="border-white/15 bg-transparent"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-white/15 bg-transparent"
            onClick={() => setPage((p) => p + 1)}
          >
            Próxima
          </Button>
        </div>
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
