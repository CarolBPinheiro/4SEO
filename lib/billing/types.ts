import type { BillingCycle, PlanId } from "@/lib/billing/plans";

export type CreateCheckoutSessionRequest = {
  planId: PlanId;
  billingCycle: BillingCycle;
};

export type CreateCheckoutSessionResponse = {
  checkoutUrl: string;
  checkoutId: string;
  expiresAt: string;
};

export type ApiErrorBody = {
  message?: string;
  error?: string;
  statusCode?: number;
};
