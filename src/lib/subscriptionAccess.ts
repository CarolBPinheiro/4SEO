/**
 * Fonte única (frontend) para interpretar status / nível de acesso.
 * APIs de produto exigem accessLevel === "full" (backend).
 * Trial libera só UI limitada (Dashboard + Análise demo).
 */

export type AccessLevel = "none" | "trial" | "full";

export const PLAN_DISPLAY_NAMES: Record<string, string> = {
  start: "Start",
  pro: "Pro",
  scale: "Scale",
};

export function isFullAccess(level: AccessLevel | string | null | undefined): boolean {
  return level === "full";
}

export function isTrialAccess(level: AccessLevel | string | null | undefined): boolean {
  return level === "trial";
}

/** Dashboard, Análise ou Integrações liberados (pago ou trial). */
export function canAccessTrialSurfaces(
  level: AccessLevel | string | null | undefined,
): boolean {
  return level === "full" || level === "trial";
}

export function isEntitledSubscriptionStatus(
  status: string | null | undefined,
): boolean {
  return status === "active" || status === "trialing" || status === "past_due";
}

export function isPendingSubscriptionStatus(
  status: string | null | undefined,
): boolean {
  return status === "pending";
}

export function planDisplayName(planId: string | null | undefined): string {
  if (!planId) {
    return "—";
  }
  return PLAN_DISPLAY_NAMES[planId] || planId;
}

export function daysRemaining(trialEndsAt: string | null | undefined): number | null {
  if (!trialEndsAt) {
    return null;
  }
  const ends = new Date(trialEndsAt).getTime();
  if (Number.isNaN(ends)) {
    return null;
  }
  const ms = ends - Date.now();
  if (ms <= 0) {
    return 0;
  }
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
}

/**
 * Destino pós-login:
 * - full → dashboard
 * - trial → dashboard (app real; menus pagos ficam bloqueados)
 * - none → /trial (escolher avaliação)
 */
export function resolvePostAuthPath(accessLevel?: AccessLevel | string | null): string {
  if (accessLevel === "full" || accessLevel === "trial") {
    return "/dashboard";
  }
  return "/trial";
}
