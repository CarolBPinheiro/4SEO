import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type CheckoutShellProps = {
  title: string;
  description: string;
  children?: ReactNode;
  actions?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
};

const toneBorder: Record<NonNullable<CheckoutShellProps["tone"]>, string> = {
  default: "border-white/10",
  success: "border-emerald-500/30",
  warning: "border-amber-500/30",
  danger: "border-red-500/30",
};

export function CheckoutShell({
  title,
  description,
  children,
  actions,
  tone = "default",
}: CheckoutShellProps) {
  return (
    <main className="relative flex min-h-full flex-col px-4 py-16 sm:py-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,117,26,0.12),transparent_55%)]"
      />
      <div className="relative mx-auto w-full max-w-lg">
        <p className="mb-8 text-center text-sm font-semibold tracking-[0.18em] text-brand-light uppercase">
          4SEO
        </p>
        <section
          className={cn(
            "rounded-3xl border bg-white/[0.03] p-8 sm:p-10",
            toneBorder[tone],
          )}
        >
          <h1 className="text-2xl font-bold tracking-[-0.02em] text-white sm:text-3xl">
            {title}
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-zinc-400 sm:text-base">
            {description}
          </p>
          {children ? <div className="mt-6">{children}</div> : null}
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            {actions}
            <Button href="/#planos" variant="ghost" className="rounded-full">
              Ver planos
            </Button>
            <Button href="/" variant="secondary" className="rounded-full">
              Voltar ao início
            </Button>
          </div>
        </section>
        <p className="mt-6 text-center text-xs text-zinc-600">
          Pagamentos processados com segurança via Asaas.{" "}
          <Link href="/privacidade" className="underline-offset-2 hover:underline">
            Privacidade
          </Link>
        </p>
      </div>
    </main>
  );
}
