import { supabase } from "@/lib/supabase";
import { getToken, setToken } from "@/lib/apiClient";

const BILLING_REF_KEY = "4seo_billing_ref";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export type ClaimCheckoutResult = {
  status: string;
  planId?: string | null;
  billingCycle?: string | null;
};

export function readPendingBillingRef(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("billingRef")?.trim() || "";
  if (fromQuery.startsWith("4seo_")) {
    return fromQuery;
  }

  try {
    const stored = sessionStorage.getItem(BILLING_REF_KEY)?.trim() || "";
    return stored.startsWith("4seo_") ? stored : null;
  } catch {
    return null;
  }
}

export function clearPendingBillingRef(): void {
  try {
    sessionStorage.removeItem(BILLING_REF_KEY);
  } catch {
    // ignore
  }
}

export function persistBillingRef(ref: string): void {
  if (!ref.startsWith("4seo_")) {
    return;
  }
  try {
    sessionStorage.setItem(BILLING_REF_KEY, ref);
  } catch {
    // ignore
  }
}

async function getFreshToken(): Promise<string | null> {
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error || !data?.session?.access_token) {
      return getToken();
    }
    const fresh = data.session.access_token;
    if (fresh !== getToken()) {
      setToken(fresh);
    }
    return fresh;
  } catch {
    return getToken();
  }
}

/**
 * Vincula checkout Asaas (ref da URL de sucesso) ao usuário autenticado.
 */
export async function claimPendingCheckout(): Promise<ClaimCheckoutResult | null> {
  const ref = readPendingBillingRef();
  if (!ref) {
    return null;
  }

  const token = await getFreshToken();
  if (!token) {
    return null;
  }

  const response = await fetch(`${API_BASE}/billing/claim-checkout`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ externalReference: ref }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      (body && typeof body === "object" && "message" in body
        ? String((body as { message?: string }).message || "")
        : "") || "Não foi possível vincular a assinatura.";
    throw new Error(message);
  }

  const result = (await response.json()) as ClaimCheckoutResult;
  clearPendingBillingRef();
  return result;
}
