import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/apiClient";
import { Input } from "@/components/ui/input";
import { ErrorBanner, PageHeader } from "./ui";
import { PRIORITY_LABELS, TICKET_STATUS_LABELS, formatDate, planLabel, str } from "./format";

const COLUMNS = ["new", "in_progress", "waiting_customer", "resolved"] as const;

type Ticket = Record<string, unknown>;

export default function AdminTicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [plan, setPlan] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.admin.tickets();
      setItems(res.items || []);
      setCounts(res.counts || {});
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar chamados");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      if (priority !== "all" && str(item.priority) !== priority) return false;
      if (plan !== "all" && str(item.plan_id) !== plan) return false;
      if (!q) return true;
      return [item.subject, item.user_email, item.user_name, item.message]
        .map((value) => str(value).toLowerCase())
        .some((value) => value.includes(q));
    });
  }, [items, search, priority, plan]);

  const move = async (ticketId: string, status: string) => {
    try {
      await api.admin.patchTicket(ticketId, { status });
      toast.success("Chamado atualizado");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao mover chamado");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Suporte"
        title="Chamados Typebot"
        subtitle="Novos atendimentos entram automaticamente pelo webhook do Typebot."
        actions={
          <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-zinc-400">
            Abertos: {numSafe(counts.new) + numSafe(counts.in_progress) + numSafe(counts.waiting_customer)}
          </div>
        }
      />
      <ErrorBanner message={error} />

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Buscar e-mail, assunto ou mensagem"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm border-white/10 bg-white/5"
        />
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="all">Todas as prioridades</option>
          {Object.entries(PRIORITY_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
          className="rounded-md border border-white/15 bg-black/40 px-3 py-2 text-sm"
        >
          <option value="all">Todos os planos</option>
          <option value="start">Start</option>
          <option value="pro">Pro</option>
          <option value="scale">Scale</option>
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-zinc-400">Carregando chamados…</p>
      ) : (
        <div className="grid gap-4 xl:grid-cols-4">
          {COLUMNS.map((column) => {
            const cards = filtered.filter((item) => str(item.status) === column);
            return (
              <div key={column} className="rounded-2xl border border-white/10 bg-black/30 p-3">
                <div className="mb-3 flex items-center justify-between px-1">
                  <p className="text-sm font-semibold">{TICKET_STATUS_LABELS[column]}</p>
                  <span className="text-xs text-zinc-500">{cards.length}</span>
                </div>
                <div className="space-y-3">
                  {cards.length === 0 ? (
                    <p className="px-1 text-xs text-zinc-600">Vazio</p>
                  ) : (
                    cards.map((ticket) => (
                      <article key={str(ticket.id)} className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
                        <p className="text-sm font-medium">{str(ticket.subject)}</p>
                        <p className="mt-1 text-xs text-zinc-400">
                          {str(ticket.user_email || ticket.user_name || "Visitante")}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-500">
                          <span>{planLabel(ticket.plan_id)}</span>
                          <span>{PRIORITY_LABELS[str(ticket.priority)] || str(ticket.priority)}</span>
                          <span>{formatDate(ticket.opened_at || ticket.created_at)}</span>
                        </div>
                        {ticket.user_id ? (
                          <Link to={`/admin/users/${ticket.user_id}`} className="mt-2 inline-block text-[11px] text-[#ff8a3d]">
                            Ver assinante
                          </Link>
                        ) : null}
                        <div className="mt-3 flex flex-wrap gap-1">
                          {COLUMNS.filter((item) => item !== column).map((next) => (
                            <button
                              key={next}
                              type="button"
                              onClick={() => void move(str(ticket.id), next)}
                              className="rounded-md border border-white/10 px-2 py-1 text-[10px] text-zinc-400 hover:bg-white/5 hover:text-white"
                            >
                              {TICKET_STATUS_LABELS[next]}
                            </button>
                          ))}
                        </div>
                      </article>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-xs leading-relaxed text-zinc-400">
        Configure no Typebot um HTTP Request para <code className="text-zinc-200">POST /api/webhooks/typebot</code> com o header{" "}
        <code className="text-zinc-200">X-Typebot-Secret</code> igual a <code className="text-zinc-200">TYPEBOT_WEBHOOK_SECRET</code>.
        Envie e-mail, assunto, mensagem, prioridade e plano nas variáveis do bot.
      </div>
    </div>
  );
}

function numSafe(value: unknown): number {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}
