import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { statusLabel } from "./format";

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#ff8a3d]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="mt-1 text-2xl font-bold tracking-tight">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-zinc-400">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "ok" | "warn" | "danger";
}) {
  const ring =
    tone === "ok"
      ? "border-emerald-500/20"
      : tone === "warn"
        ? "border-amber-500/25"
        : tone === "danger"
          ? "border-red-500/25"
          : "border-white/10";
  return (
    <div className={cn("rounded-2xl border bg-white/[0.03] p-4", ring)}>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      {hint ? <p className="mt-1 text-xs text-zinc-500">{hint}</p> : null}
    </div>
  );
}

export function StatusBadge({ status }: { status: unknown }) {
  const key = String(status || "none").toLowerCase();
  const tone =
    key === "active" || key === "trialing"
      ? "bg-emerald-500/15 text-emerald-300"
      : key === "past_due" || key === "urgent" || key === "high"
        ? "bg-red-500/15 text-red-300"
        : key === "canceled" || key === "cancelled" || key === "inactive"
          ? "bg-zinc-500/20 text-zinc-300"
          : "bg-amber-500/15 text-amber-200";
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium", tone)}>
      {statusLabel(key)}
    </span>
  );
}

export function Panel({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-2xl border border-white/10 bg-white/[0.03] p-5", className)}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-zinc-200">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
      {message}
    </div>
  );
}
