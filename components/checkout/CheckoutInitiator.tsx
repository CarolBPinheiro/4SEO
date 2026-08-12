"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";
import { Button } from "@/components/ui/Button";
import {
  BillingError,
  createCheckoutSession,
  getBillingCycle,
  getBillingErrorMessage,
  getPlanById,
  getPlanPrice,
  isBillingCycle,
  isPlanId,
  type BillingCycle,
  type PlanId,
} from "@/lib/billing";

type RequestState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "redirecting" }
  | { status: "error"; message: string; code?: string };

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function parseCheckoutParams(
  planParam: string | null,
  cycleParam: string | null,
):
  | { ok: true; planId: PlanId; billingCycle: BillingCycle }
  | { ok: false; message: string } {
  if (!planParam || !cycleParam) {
    return {
      ok: false,
      message: "Selecione um plano e um ciclo de cobrança para continuar.",
    };
  }

  if (!isPlanId(planParam) || !isBillingCycle(cycleParam)) {
    return {
      ok: false,
      message:
        "Plano ou ciclo de cobrança inválido. Escolha novamente na página de planos.",
    };
  }

  return { ok: true, planId: planParam, billingCycle: cycleParam };
}

export function CheckoutInitiator() {
  const searchParams = useSearchParams();
  const planParam = searchParams.get("plan");
  const cycleParam = searchParams.get("cycle");

  const parsed = useMemo(
    () => parseCheckoutParams(planParam, cycleParam),
    [planParam, cycleParam],
  );

  const [retryToken, setRetryToken] = useState(0);
  const [requestState, setRequestState] = useState<RequestState>({
    status: "idle",
  });
  const redirectStartedRef = useRef(false);

  useEffect(() => {
    if (!parsed.ok) {
      return;
    }

    const { planId, billingCycle } = parsed;
    const controller = new AbortController();
    redirectStartedRef.current = false;

    queueMicrotask(() => {
      if (!controller.signal.aborted) {
        setRequestState({ status: "loading" });
      }
    });

    void (async () => {
      try {
        const session = await createCheckoutSession(
          { planId, billingCycle },
          { signal: controller.signal },
        );

        if (controller.signal.aborted || redirectStartedRef.current) {
          return;
        }

        redirectStartedRef.current = true;
        setRequestState({ status: "redirecting" });
        window.location.assign(session.checkoutUrl);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setRequestState({
          status: "error",
          message: getBillingErrorMessage(error),
          code: error instanceof BillingError ? error.code : undefined,
        });
      }
    })();

    return () => {
      controller.abort();
    };
  }, [parsed, retryToken]);

  if (!parsed.ok) {
    return (
      <CheckoutShell
        title="Checkout indisponível"
        description={parsed.message}
        tone="warning"
      />
    );
  }

  const plan = getPlanById(parsed.planId);
  const cycle = getBillingCycle(parsed.billingCycle);
  const price = getPlanPrice(parsed.planId, parsed.billingCycle);

  const summary = (
    <dl className="space-y-3 rounded-2xl border border-white/8 bg-black/30 p-4 text-sm">
      <div className="flex items-center justify-between gap-4">
        <dt className="text-zinc-500">Plano</dt>
        <dd className="font-medium text-white">{plan.name}</dd>
      </div>
      <div className="flex items-center justify-between gap-4">
        <dt className="text-zinc-500">Ciclo</dt>
        <dd className="font-medium text-white">{cycle.label}</dd>
      </div>
      <div className="flex items-center justify-between gap-4">
        <dt className="text-zinc-500">Total</dt>
        <dd className="font-semibold text-brand-light">
          {currencyFormatter.format(price.total)}
          <span className="ml-1 text-xs font-normal text-zinc-500">
            {cycle.periodLabel}
          </span>
        </dd>
      </div>
    </dl>
  );

  if (requestState.status === "error") {
    const isConfigError = requestState.code === "API_NOT_CONFIGURED";

    return (
      <CheckoutShell
        title={isConfigError ? "Checkout em preparação" : "Não foi possível continuar"}
        description={requestState.message}
        tone={isConfigError ? "warning" : "danger"}
        actions={
          !isConfigError ? (
            <Button
              type="button"
              variant="primary"
              className="rounded-full"
              onClick={() => {
                setRequestState({ status: "loading" });
                setRetryToken((value) => value + 1);
              }}
            >
              Tentar novamente
            </Button>
          ) : undefined
        }
      >
        {summary}
      </CheckoutShell>
    );
  }

  const isRedirecting = requestState.status === "redirecting";

  return (
    <CheckoutShell
      title={
        isRedirecting
          ? "Redirecionando ao pagamento"
          : "Preparando seu checkout"
      }
      description={
        isRedirecting
          ? "Você será enviado à página segura do Asaas em instantes."
          : "Estamos criando sua sessão de pagamento. Não feche esta página."
      }
    >
      {summary}
      <p className="mt-4 flex items-center gap-2 text-sm text-zinc-500" role="status">
        <span
          aria-hidden
          className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand/30 border-t-brand"
        />
        {isRedirecting
          ? "Abrindo checkout Asaas…"
          : "Conectando ao serviço de cobrança…"}
      </p>
    </CheckoutShell>
  );
}
