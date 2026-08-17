import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "@/contexts/AuthContext";
import { getToken } from "@/lib/apiClient";
import { claimPendingCheckout } from "@/lib/billingClaim";
import { getPlansUrl } from "@/lib/site";
import {
  type AccessLevel,
  canAccessTrialSurfaces,
  isFullAccess,
  isPendingSubscriptionStatus,
  isTrialAccess,
} from "@/lib/subscriptionAccess";

export type SubscriptionStatus =
  | "none"
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "expired"
  | "pending"
  | "inactive"
  | string;

export interface SubscriptionInfo {
  status: SubscriptionStatus;
  planId?: string | null;
  billingCycle?: string | null;
  asaasSubscriptionId?: string | null;
  asaasCustomerId?: string | null;
  currentPeriodEnd?: string | null;
  trialEndsAt?: string | null;
  accessLevel?: AccessLevel | string;
  updatedAt?: string | null;
}

interface BillingContextType {
  subscription: SubscriptionInfo | null;
  loading: boolean;
  /** Assinatura paga (APIs reais). */
  hasFullAccess: boolean;
  /** Trial UI (Dashboard + Análise limitados). */
  hasTrialAccess: boolean;
  /** full || trial — navegar em Dashboard, Análise e Integrações. */
  canUseAppPreview: boolean;
  /** @deprecated use hasFullAccess — mantido para telas que bloqueiam recursos pagos */
  hasActiveSubscription: boolean;
  isPendingPayment: boolean;
  refreshSubscription: () => Promise<SubscriptionInfo | null>;
  subscribeUrl: string;
  startTrial: (planId: string) => Promise<SubscriptionInfo>;
}

const BillingContext = createContext<BillingContextType | null>(null);

export async function fetchSubscription(): Promise<SubscriptionInfo> {
  const token = getToken();
  if (!token) {
    return { status: "none", accessLevel: "none" };
  }
  const base = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${base}/billing/subscription`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    return { status: "none", accessLevel: "none" };
  }
  const data = (await res.json()) as SubscriptionInfo;
  return {
    status: data?.status || "none",
    planId: data?.planId ?? null,
    billingCycle: data?.billingCycle ?? null,
    asaasSubscriptionId: data?.asaasSubscriptionId ?? null,
    asaasCustomerId: data?.asaasCustomerId ?? null,
    currentPeriodEnd: data?.currentPeriodEnd ?? null,
    trialEndsAt: data?.trialEndsAt ?? null,
    accessLevel: (data?.accessLevel as AccessLevel) || "none",
    updatedAt: data?.updatedAt ?? null,
  };
}

export function BillingProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshSubscription = useCallback(async () => {
    if (!user || !getToken()) {
      setSubscription(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      try {
        await claimPendingCheckout();
      } catch {
        // claim best-effort
      }
      const info = await fetchSubscription();
      setSubscription(info);
      return info;
    } catch {
      setSubscription({ status: "none", accessLevel: "none" });
      return { status: "none", accessLevel: "none" };
    } finally {
      setLoading(false);
    }
  }, [user]);

  const startTrial = useCallback(
    async (planId: string) => {
      const token = getToken();
      if (!token) {
        throw new Error("Faça login para iniciar a avaliação.");
      }
      const base = import.meta.env.VITE_API_BASE_URL || "/api";
      const res = await fetch(`${base}/billing/start-trial`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ planId }),
      });
      const body = (await res.json().catch(() => null)) as
        | SubscriptionInfo
        | { message?: string }
        | null;
      if (!res.ok) {
        const message =
          body && typeof body === "object" && "message" in body
            ? String(body.message || "")
            : "";
        throw new Error(message || "Não foi possível iniciar a avaliação.");
      }
      const info = body as SubscriptionInfo;
      setSubscription(info);
      return info;
    },
    [],
  );

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!user) {
      setSubscription(null);
      setLoading(false);
      return;
    }
    void refreshSubscription();
  }, [user, authLoading, refreshSubscription]);

  const level = subscription?.accessLevel || "none";
  const hasFullAccess = isFullAccess(level);
  const hasTrialAccess = isTrialAccess(level);
  const canUseAppPreview = canAccessTrialSurfaces(level);
  const isPendingPayment = isPendingSubscriptionStatus(subscription?.status);

  const value: BillingContextType = {
    subscription,
    loading: authLoading || loading,
    hasFullAccess,
    hasTrialAccess,
    canUseAppPreview,
    hasActiveSubscription: hasFullAccess,
    isPendingPayment,
    refreshSubscription,
    subscribeUrl: getPlansUrl(),
    startTrial,
  };

  return (
    <BillingContext.Provider value={value}>{children}</BillingContext.Provider>
  );
}

export function useBilling() {
  const ctx = useContext(BillingContext);
  if (!ctx) {
    throw new Error("useBilling must be used within BillingProvider");
  }
  return ctx;
}
