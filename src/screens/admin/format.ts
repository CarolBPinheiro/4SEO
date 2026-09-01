export const PLAN_LABELS: Record<string, string> = {
  start: "Start",
  pro: "Pro",
  scale: "Scale",
};

export const CYCLE_LABELS: Record<string, string> = {
  monthly: "Mensal",
  quarterly: "Trimestral",
  semiannual: "Semestral",
  annual: "Anual",
};

export const STATUS_LABELS: Record<string, string> = {
  active: "Ativa",
  trialing: "Trial",
  past_due: "Inadimplente",
  canceled: "Cancelada",
  cancelled: "Cancelada",
  inactive: "Inativa",
  expired: "Expirada",
  pending: "Pendente",
  none: "Sem plano",
};

export const TICKET_STATUS_LABELS: Record<string, string> = {
  new: "Novo",
  in_progress: "Em atendimento",
  waiting_customer: "Aguardando cliente",
  resolved: "Resolvido",
};

export const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  urgent: "Urgente",
};

export function formatMoney(value: unknown): string {
  const amount = typeof value === "number" ? value : Number(value || 0);
  return amount.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatDate(value: unknown): string {
  if (!value || typeof value !== "string") return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR");
}

export function formatDateShort(value: unknown): string {
  if (!value || typeof value !== "string") return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("pt-BR");
}

export function planLabel(planId: unknown): string {
  const key = String(planId || "");
  return PLAN_LABELS[key] || key || "—";
}

export function statusLabel(status: unknown): string {
  const key = String(status || "none");
  return STATUS_LABELS[key] || key;
}

export function num(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function str(value: unknown): string {
  return value == null ? "" : String(value);
}
