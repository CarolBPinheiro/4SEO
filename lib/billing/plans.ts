export type BillingCycle = "monthly" | "quarterly" | "semiannual" | "annual";

export type PlanId = "start" | "pro" | "scale";

/** Ciclos de assinatura aceitos pela API Asaas (Subscriptions / Checkout). */
export type AsaasSubscriptionCycle =
  | "MONTHLY"
  | "QUARTERLY"
  | "SEMIANNUALLY"
  | "YEARLY";

export type CyclePricing = {
  total: number;
  discountPercent: number;
  bonusProducts: number;
};

export type Plan = {
  id: PlanId;
  name: string;
  tagline: string;
  products: number;
  searches: number;
  extraProductPrice: number;
  popular?: boolean;
  pricing: Record<BillingCycle, CyclePricing>;
};

export type BillingCycleOption = {
  id: BillingCycle;
  label: string;
  months: number;
  periodLabel: string;
  asaasCycle: AsaasSubscriptionCycle;
};

export const BILLING_CYCLES: readonly BillingCycleOption[] = [
  {
    id: "monthly",
    label: "Mensal",
    months: 1,
    periodLabel: "/mês",
    asaasCycle: "MONTHLY",
  },
  {
    id: "quarterly",
    label: "Trimestral",
    months: 3,
    periodLabel: "/trimestre",
    asaasCycle: "QUARTERLY",
  },
  {
    id: "semiannual",
    label: "Semestral",
    months: 6,
    periodLabel: "/semestre",
    asaasCycle: "SEMIANNUALLY",
  },
  {
    id: "annual",
    label: "Anual",
    months: 12,
    periodLabel: "/ano",
    asaasCycle: "YEARLY",
  },
] as const;

export const PLANS: readonly Plan[] = [
  {
    id: "start",
    name: "Start",
    tagline: "Para pequenos e-commerces",
    products: 250,
    searches: 100,
    extraProductPrice: 0.25,
    pricing: {
      monthly: { total: 89, discountPercent: 0, bonusProducts: 0 },
      quarterly: { total: 267, discountPercent: 0, bonusProducts: 20 },
      semiannual: { total: 507.3, discountPercent: 5, bonusProducts: 50 },
      annual: { total: 961.2, discountPercent: 10, bonusProducts: 75 },
    },
  },
  {
    id: "pro",
    name: "Pro",
    tagline: "O equilíbrio ideal para crescer",
    products: 700,
    searches: 300,
    extraProductPrice: 0.22,
    popular: true,
    pricing: {
      monthly: { total: 199, discountPercent: 0, bonusProducts: 0 },
      quarterly: { total: 579.09, discountPercent: 3, bonusProducts: 50 },
      semiannual: { total: 1110.42, discountPercent: 7, bonusProducts: 100 },
      annual: { total: 2149.2, discountPercent: 10, bonusProducts: 150 },
    },
  },
  {
    id: "scale",
    name: "Scale",
    tagline: "Melhor custo-benefício",
    products: 1500,
    searches: 700,
    extraProductPrice: 0.18,
    pricing: {
      monthly: { total: 299, discountPercent: 0, bonusProducts: 0 },
      quarterly: { total: 852.15, discountPercent: 5, bonusProducts: 50 },
      semiannual: { total: 1614.6, discountPercent: 10, bonusProducts: 100 },
      annual: { total: 3049.8, discountPercent: 15, bonusProducts: 150 },
    },
  },
] as const;

const PLAN_IDS = new Set<string>(PLANS.map((plan) => plan.id));
const BILLING_CYCLE_IDS = new Set<string>(
  BILLING_CYCLES.map((cycle) => cycle.id),
);

export function isPlanId(value: string): value is PlanId {
  return PLAN_IDS.has(value);
}

export function isBillingCycle(value: string): value is BillingCycle {
  return BILLING_CYCLE_IDS.has(value);
}

export function getPlanById(planId: PlanId): Plan {
  const plan = PLANS.find((item) => item.id === planId);
  if (!plan) {
    throw new Error(`Plano desconhecido: ${planId}`);
  }
  return plan;
}

export function getBillingCycle(cycleId: BillingCycle): BillingCycleOption {
  const cycle = BILLING_CYCLES.find((item) => item.id === cycleId);
  if (!cycle) {
    throw new Error(`Ciclo de cobrança desconhecido: ${cycleId}`);
  }
  return cycle;
}

export function toAsaasCycle(billingCycle: BillingCycle): AsaasSubscriptionCycle {
  return getBillingCycle(billingCycle).asaasCycle;
}

export function getPlanPrice(
  planId: PlanId,
  billingCycle: BillingCycle,
): CyclePricing {
  return getPlanById(planId).pricing[billingCycle];
}

export function buildCheckoutPath(
  planId: PlanId,
  billingCycle: BillingCycle,
): string {
  const params = new URLSearchParams({
    plan: planId,
    cycle: billingCycle,
  });
  return `/checkout?${params.toString()}`;
}
