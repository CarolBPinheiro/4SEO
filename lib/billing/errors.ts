export type BillingErrorCode =
  | "API_NOT_CONFIGURED"
  | "INVALID_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "RATE_LIMITED"
  | "TIMEOUT"
  | "NETWORK"
  | "INVALID_RESPONSE"
  | "SERVER_ERROR"
  | "UNKNOWN";

export class BillingError extends Error {
  readonly code: BillingErrorCode;
  readonly status?: number;

  constructor(code: BillingErrorCode, message: string, status?: number) {
    super(message);
    this.name = "BillingError";
    this.code = code;
    this.status = status;
  }
}

const STATUS_MESSAGES: Record<number, { code: BillingErrorCode; message: string }> =
  {
    400: {
      code: "INVALID_REQUEST",
      message: "Não foi possível iniciar o checkout com os dados informados.",
    },
    401: {
      code: "UNAUTHORIZED",
      message: "Faça login para continuar com a assinatura.",
    },
    403: {
      code: "FORBIDDEN",
      message: "Você não tem permissão para iniciar este checkout.",
    },
    404: {
      code: "NOT_FOUND",
      message: "Serviço de cobrança indisponível no momento.",
    },
    429: {
      code: "RATE_LIMITED",
      message: "Muitas tentativas. Aguarde um instante e tente novamente.",
    },
  };

export function mapHttpStatusToBillingError(
  status: number,
  fallbackMessage?: string,
): BillingError {
  const mapped = STATUS_MESSAGES[status];
  if (mapped) {
    return new BillingError(
      mapped.code,
      fallbackMessage?.trim() || mapped.message,
      status,
    );
  }

  if (status >= 500) {
    return new BillingError(
      "SERVER_ERROR",
      fallbackMessage?.trim() ||
        "O servidor de cobrança está temporariamente indisponível.",
      status,
    );
  }

  return new BillingError(
    "UNKNOWN",
    fallbackMessage?.trim() || "Não foi possível iniciar o checkout.",
    status,
  );
}

export function getBillingErrorMessage(error: unknown): string {
  if (error instanceof BillingError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Não foi possível iniciar o checkout.";
}
