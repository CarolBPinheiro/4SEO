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
import { getMarketingUrl } from "@/lib/site";

export type SubscriptionStatus =
  | "none"
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "expired"
  | string;

export interface SubscriptionInfo {
  status: SubscriptionStatus;
  planId?: string | null;
  billingCycle?: string | null;
  asaasSubscriptionId?: string | null;
  asaasCustomerId?: string | null;
  currentPeriodEnd?: string | null;
  updatedAt?: string | null;
}

interface BillingContextType {
  subscription: SubscriptionInfo | null;
  loading: boolean;
  hasActiveSubscription: boolean;
  refreshSubscription: () => Promise<SubscriptionInfo | null>;
  subscribeUrl: string;
}

const BillingContext = createContext<BillingContextType | null>(null);

const ENTITLED = new Set(["active", "trialing", "past_due"]);

function isEntitled(status: string | undefined | null): boolean {
  return !!status && ENTITLED.has(status);
}

async function fetchSubscription(): Promise<SubscriptionInfo> {
  const token = getToken();
  if (!token) {
    return { status: "none" };
  }
  const base = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${base}/billing/subscription`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    return { status: "none" };
  }
  const data = (await res.json()) as SubscriptionInfo;
  return {
    status: data?.status || "none",
    planId: data?.planId ?? null,
    billingCycle: data?.billingCycle ?? null,
    asaasSubscriptionId: data?.asaasSubscriptionId ?? null,
    asaasCustomerId: data?.asaasCustomerId ?? null,
    currentPeriodEnd: data?.currentPeriodEnd ?? null,
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
      setSubscription({ status: "none" });
      return { status: "none" };
    } finally {
      setLoading(false);
    }
  }, [user]);

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

  const hasActiveSubscription = isEntitled(subscription?.status);

  const value: BillingContextType = {
    subscription,
    loading: authLoading || loading,
    hasActiveSubscription,
    refreshSubscription,
    subscribeUrl: `${getMarketingUrl()}/#planos`,
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
