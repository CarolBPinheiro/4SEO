import { BillingError, mapHttpStatusToBillingError } from "@/lib/billing/errors";
import type {
  ApiErrorBody,
  CreateCheckoutSessionRequest,
  CreateCheckoutSessionResponse,
} from "@/lib/billing/types";
import { isBillingCycle, isPlanId } from "@/lib/billing/plans";

const CHECKOUT_PATH = "/billing/checkout";
const DEFAULT_TIMEOUT_MS = 15_000;

function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) {
    throw new BillingError(
      "API_NOT_CONFIGURED",
      "O checkout ainda não está disponível. Configure NEXT_PUBLIC_API_URL quando o backend de billing estiver online.",
    );
  }

  return raw.replace(/\/+$/, "");
}

function isAbsoluteHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function parseErrorMessage(body: unknown): string | undefined {
  if (!body || typeof body !== "object") {
    return undefined;
  }

  const { message, error } = body as ApiErrorBody;
  if (typeof message === "string" && message.trim()) {
    return message.trim();
  }
  if (typeof error === "string" && error.trim()) {
    return error.trim();
  }

  return undefined;
}

function assertCheckoutResponse(
  body: unknown,
): CreateCheckoutSessionResponse {
  if (!body || typeof body !== "object") {
    throw new BillingError(
      "INVALID_RESPONSE",
      "Resposta inválida do serviço de cobrança.",
    );
  }

  const { checkoutUrl, checkoutId, expiresAt } =
    body as Partial<CreateCheckoutSessionResponse>;

  if (
    typeof checkoutUrl !== "string" ||
    !isAbsoluteHttpUrl(checkoutUrl) ||
    typeof checkoutId !== "string" ||
    !checkoutId.trim() ||
    typeof expiresAt !== "string" ||
    !expiresAt.trim()
  ) {
    throw new BillingError(
      "INVALID_RESPONSE",
      "Resposta incompleta do serviço de cobrança.",
    );
  }

  return {
    checkoutUrl,
    checkoutId: checkoutId.trim(),
    expiresAt: expiresAt.trim(),
  };
}

function validateRequest(
  request: CreateCheckoutSessionRequest,
): CreateCheckoutSessionRequest {
  if (!isPlanId(request.planId) || !isBillingCycle(request.billingCycle)) {
    throw new BillingError(
      "INVALID_REQUEST",
      "Plano ou ciclo de cobrança inválido.",
    );
  }

  return {
    planId: request.planId,
    billingCycle: request.billingCycle,
  };
}

export async function createCheckoutSession(
  request: CreateCheckoutSessionRequest,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<CreateCheckoutSessionResponse> {
  const payload = validateRequest(request);
  const baseUrl = getApiBaseUrl();
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  options?.signal?.addEventListener("abort", onExternalAbort, { once: true });

  try {
    const response = await fetch(`${baseUrl}${CHECKOUT_PATH}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: "no-store",
    });

    let body: unknown = null;
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        body = await response.json();
      } catch {
        body = null;
      }
    }

    if (!response.ok) {
      throw mapHttpStatusToBillingError(
        response.status,
        parseErrorMessage(body),
      );
    }

    return assertCheckoutResponse(body);
  } catch (error) {
    if (error instanceof BillingError) {
      throw error;
    }

    const isAbort =
      (error instanceof DOMException || error instanceof Error) &&
      error.name === "AbortError";

    if (isAbort) {
      if (options?.signal?.aborted) {
        throw new BillingError(
          "NETWORK",
          "A solicitação de checkout foi cancelada.",
        );
      }

      throw new BillingError(
        "TIMEOUT",
        "O serviço de cobrança demorou demais para responder.",
      );
    }

    throw new BillingError(
      "NETWORK",
      "Não foi possível conectar ao serviço de cobrança. Verifique se o backend está online.",
    );
  } finally {
    clearTimeout(timeoutId);
    options?.signal?.removeEventListener("abort", onExternalAbort);
  }
}
