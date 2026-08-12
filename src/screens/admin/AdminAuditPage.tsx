import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";

export default function AdminAuditPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.admin.audit(100);
        if (!cancelled) {
          setItems(res.items || []);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Audit log</h1>
        <p className="text-sm text-zinc-400">
          Ações do administrador da plataforma (sem níveis / RBAC)
        </p>
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
              <th className="px-4 py-3 font-medium">Quando</th>
              <th className="px-4 py-3 font-medium">Actor</th>
              <th className="px-4 py-3 font-medium">Ação</th>
              <th className="px-4 py-3 font-medium">Alvo</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-zinc-500">
                  Sem registros (verifique se a migration admin_audit_log foi aplicada).
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={String(row.id)} className="border-t border-white/5">
                  <td className="px-4 py-3 text-zinc-400">{formatDate(row.created_at)}</td>
                  <td className="px-4 py-3">{String(row.actor_email || row.actor_user_id || "—")}</td>
                  <td className="px-4 py-3">{String(row.action)}</td>
                  <td className="px-4 py-3 text-zinc-400">
                    {row.target_type
                      ? `${row.target_type}:${row.target_id || ""}`
                      : "—"}
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
