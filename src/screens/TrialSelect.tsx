import { useId, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Check, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getMarketingUrl } from "@/lib/site";
import {
  BILLING_CYCLES,
  PLANS,
  type BillingCycle,
  type PlanId,
} from "@billing-plans";

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const currencyCompactFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatProducts(value: number): string {
  return value.toLocaleString("pt-BR");
}

function formatExtraPrice(value: number): string {
  return currencyCompactFormatter.format(value);
}

/**
 * Escolha de trial — mesmo visual da seção Planos da landing.
 */
export default function TrialSelect() {
  const navigate = useNavigate();
  const billingGroupId = useId();
  const { user, loading: authLoading, signOut } = useAuth();
  const {
    loading: billingLoading,
    hasFullAccess,
    hasTrialAccess,
    startTrial,
  } = useBilling();

  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [activePlan, setActivePlan] = useState("Pro");
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState("");

  const activeCycle =
    BILLING_CYCLES.find((cycle) => cycle.id === billingCycle) ?? BILLING_CYCLES[0];

  if (authLoading || billingLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050506] text-zinc-400">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (hasFullAccess || hasTrialAccess) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleStartTrial = async (planId: PlanId, planName: string) => {
    setError("");
    setActivePlan(planName);
    setBusyPlan(planId);
    try {
      await startTrial(planId);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao iniciar avaliação.");
    } finally {
      setBusyPlan(null);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050506] text-white">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,117,26,0.14),transparent_55%)]"
      />

      <section className="relative scroll-mt-28 px-4 py-16 lg:py-24" aria-labelledby="trial-pricing-heading">
        <div className="mx-auto max-w-6xl">
          <div className="mb-2 flex flex-col items-center gap-3">
            <img src="/logo.png" alt="4SEO" className="h-12 w-auto" />
            <button
              type="button"
              className="text-sm text-zinc-500 underline-offset-4 transition-colors hover:text-zinc-300 hover:underline"
              onClick={() => {
                void (async () => {
                  await signOut();
                  navigate("/login", { replace: true });
                })();
              }}
            >
              Voltar ao login
            </button>
          </div>

          <h1
            id="trial-pricing-heading"
            className="mt-8 text-center text-[clamp(2rem,4vw,2.75rem)] font-bold leading-[1.1] tracking-[-0.02em] text-white"
          >
            <span className="block">Escolha o plano ideal</span>
            <span className="mt-1.5 block font-semibold tracking-[-0.015em] text-white/75">
              para a sua loja
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-lg text-center text-base leading-relaxed tracking-[-0.01em] text-white/65">
            Três planos por volume de produtos e pesquisas. Comece com 7 dias de
            avaliação gratuita — sem cartão. Dashboard e Análise de IA em modo
            demonstração.
          </p>

          {error ? (
            <div className="mx-auto mt-6 max-w-xl rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-center text-sm text-destructive">
              {error}
            </div>
          ) : null}

          <div
            role="radiogroup"
            aria-label="Ciclo de cobrança"
            className="mx-auto mt-10 flex w-full max-w-xl flex-wrap items-center justify-center gap-1 rounded-full border border-white/10 bg-white/[0.03] p-1"
          >
            {BILLING_CYCLES.map((cycle) => {
              const isActive = cycle.id === billingCycle;
              const optionId = `${billingGroupId}-${cycle.id}`;

              return (
                <button
                  key={cycle.id}
                  id={optionId}
                  type="button"
                  role="radio"
                  aria-checked={isActive}
                  onClick={() => setBillingCycle(cycle.id)}
                  className={cn(
                    "min-w-[5.5rem] flex-1 rounded-full px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-black",
                    isActive
                      ? "bg-primary text-white shadow-[0_0_20px_rgba(255,117,26,0.25)]"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-white",
                  )}
                >
                  {cycle.label}
                </button>
              );
            })}
          </div>

          <div
            className="mt-12 grid grid-cols-1 items-stretch gap-5 lg:grid-cols-3 lg:gap-4"
            role="list"
            aria-label="Planos disponíveis"
          >
            {PLANS.map((plan) => {
              const cyclePricing = plan.pricing[billingCycle];
              const monthlyEquivalent = cyclePricing.total / activeCycle.months;
              const isActive = activePlan === plan.name;
              const features = [
                `${formatProducts(plan.products)} produtos otimizados por IA`,
                `${formatProducts(plan.searches)} pesquisas`,
                `Produtos extras a ${formatExtraPrice(plan.extraProductPrice)} cada`,
                "7 dias de avaliação gratuita sem cartão",
                "Dashboard, Análise de IA e integração de loja no trial",
              ];

              if (cyclePricing.bonusProducts > 0) {
                features.push(
                  `+${formatProducts(cyclePricing.bonusProducts)} produtos extras no ciclo`,
                );
              }

              return (
                <div
                  key={plan.id}
                  className={cn(
                    "h-full transition-[margin] duration-500 ease-out",
                    isActive ? "lg:-mt-4 lg:mb-[-1rem]" : "",
                  )}
                >
                  <article
                    role="listitem"
                    tabIndex={0}
                    aria-current={isActive ? "true" : undefined}
                    onMouseEnter={() => setActivePlan(plan.name)}
                    onFocus={() => setActivePlan(plan.name)}
                    onClick={() => setActivePlan(plan.name)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setActivePlan(plan.name);
                      }
                    }}
                    className={cn(
                      "pricing-card relative flex h-full cursor-pointer flex-col rounded-3xl border p-6 sm:p-8",
                      isActive
                        ? "pricing-card--active border-primary/50 bg-gradient-to-b from-primary/12 via-[#121216] to-black shadow-[0_0_40px_rgba(255,117,26,0.15)]"
                        : "border-white/10 bg-white/[0.03] hover:border-white/20",
                    )}
                  >
                    {plan.popular ? (
                      <span
                        className={cn(
                          "absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border px-3 py-1 text-xs font-semibold transition-colors duration-500",
                          isActive
                            ? "border-primary/40 bg-primary text-white"
                            : "border-white/15 bg-white/10 text-white/80",
                        )}
                      >
                        Mais popular
                      </span>
                    ) : null}

                    <div className="mb-6">
                      <div className="flex items-center justify-between gap-3">
                        <h2 className="text-lg font-semibold text-white">{plan.name}</h2>
                        {cyclePricing.discountPercent > 0 ? (
                          <span className="rounded-full border border-primary/30 bg-primary/15 px-2.5 py-0.5 text-xs font-semibold text-[#ff8a3d]">
                            {cyclePricing.discountPercent}% OFF
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-zinc-400">{plan.tagline}</p>
                      <div className="mt-5 flex items-end gap-1">
                        <span className="text-sm font-medium text-zinc-400">R$</span>
                        <span className="text-5xl font-bold tracking-tight text-white">
                          {currencyFormatter.format(cyclePricing.total)}
                        </span>
                        <span className="mb-1 text-sm text-zinc-500">
                          {activeCycle.periodLabel}
                        </span>
                      </div>
                      <p
                        className={cn(
                          "mt-2 min-h-5 text-sm",
                          billingCycle !== "monthly" ? "text-zinc-500" : "text-transparent",
                        )}
                        aria-hidden={billingCycle === "monthly"}
                      >
                        {billingCycle !== "monthly"
                          ? `Equivale a R$ ${currencyFormatter.format(monthlyEquivalent)}/mês`
                          : "\u00a0"}
                      </p>
                    </div>

                    <ul className="mb-6 flex flex-1 flex-col gap-3">
                      {features.map((feature) => (
                        <li
                          key={feature}
                          className="flex items-start gap-2.5 text-sm text-zinc-300"
                        >
                          <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[#ff8a3d]">
                            <Check className="h-3 w-3" aria-hidden />
                          </span>
                          {feature}
                        </li>
                      ))}
                    </ul>

                    <Button
                      type="button"
                      disabled={!!busyPlan}
                      className={cn(
                        "btn-pricing-assine h-11 w-full rounded-full font-semibold",
                        isActive
                          ? "btn-pricing-assine--active btn-gradient text-primary-foreground"
                          : "border border-white/15 bg-white/[0.06] text-white hover:bg-white/10",
                      )}
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleStartTrial(plan.id, plan.name);
                      }}
                    >
                      {busyPlan === plan.id ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Iniciando…
                        </>
                      ) : (
                        "Avaliação grátis — 7 dias"
                      )}
                    </Button>

                    <button
                      type="button"
                      className="mt-3 text-center text-sm font-medium text-zinc-400 underline-offset-4 hover:text-white hover:underline"
                      onClick={(event) => {
                        event.stopPropagation();
                        setActivePlan(plan.name);
                        window.location.assign(
                          `${getMarketingUrl()}/checkout?plan=${plan.id}&cycle=${billingCycle}`,
                        );
                      }}
                    >
                      ou assine agora →
                    </button>
                  </article>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
