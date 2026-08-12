import { useCallback, useState } from "react";

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
}

export interface UseApiErrorResult {
  error: ApiError | null;
  isError: boolean;
  handleError: (error: unknown) => ApiError;
  clearError: () => void;
  getErrorMessage: (error: unknown) => string;
}

// Mensagens amigáveis para erros comuns
const ERROR_MESSAGES: Record<string, string> = {
  // Erros de rede
  "Failed to fetch": "Não foi possível conectar ao servidor. Verifique sua conexão com a internet.",
  "Network Error": "Erro de conexão. Verifique sua internet e tente novamente.",
  "NetworkError": "Erro de conexão. Verifique sua internet e tente novamente.",
  
  // Erros HTTP
  "400": "Requisição inválida. Verifique os dados enviados.",
  "401": "Sessão expirada. Por favor, reconecte sua loja.",
  "403": "Você não tem permissão para realizar esta ação.",
  "404": "Recurso não encontrado.",
  "422": "Dados inválidos. Verifique as informações e tente novamente.",
  "429": "Muitas requisições. Aguarde alguns segundos e tente novamente.",
  "500": "Erro interno do servidor. Tente novamente mais tarde.",
  "502": "Servidor temporariamente indisponível. Tente novamente.",
  "503": "Serviço indisponível. O servidor está em manutenção.",
  "504": "Tempo de resposta esgotado. Tente novamente.",
  
  // Erros de OAuth
  "invalid_grant": "Autorização expirada. Por favor, reconecte sua loja.",
  "invalid_token": "Token inválido. Por favor, reconecte sua loja.",
  "unauthorized": "Não autorizado. Por favor, reconecte sua loja.",
  
  // Erros de API Nuvemshop/Shopify
  "Not Found": "Recurso não encontrado na loja.",
  "Bad Request": "Requisição inválida para a API da loja.",
  "Unauthorized": "Acesso não autorizado. Reconecte sua loja.",
  
  // Erros de timeout
  "timeout": "A operação demorou muito. Tente novamente.",
  "AbortError": "A operação foi cancelada.",
  
  // Fallback
  "default": "Ocorreu um erro inesperado. Tente novamente.",
};

// Extrai código de erro de diferentes formatos
function extractErrorCode(error: unknown): string | null {
  if (error instanceof Response) {
    return String(error.status);
  }
  
  if (error instanceof Error) {
    // Verifica se tem status no message
    const statusMatch = error.message.match(/(\d{3})/);
    if (statusMatch) {
      return statusMatch[1];
    }
    
    // Verifica keywords conhecidas
    for (const key of Object.keys(ERROR_MESSAGES)) {
      if (error.message.toLowerCase().includes(key.toLowerCase())) {
        return key;
      }
    }
  }
  
  if (typeof error === "object" && error !== null) {
    const obj = error as Record<string, unknown>;
    if (obj.status) return String(obj.status);
    if (obj.code) return String(obj.code);
    if (obj.statusCode) return String(obj.statusCode);
  }
  
  return null;
}

// Extrai mensagem de erro de diferentes formatos
function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  
  if (typeof error === "string") {
    return error;
  }
  
  if (typeof error === "object" && error !== null) {
    const obj = error as Record<string, unknown>;
    if (obj.message && typeof obj.message === "string") return obj.message;
    if (obj.detail && typeof obj.detail === "string") return obj.detail;
    if (obj.error && typeof obj.error === "string") return obj.error;
    if (obj.description && typeof obj.description === "string") return obj.description;
  }
  
  return "Erro desconhecido";
}

// Retorna mensagem amigável para o usuário
export function getErrorMessage(error: unknown): string {
  const code = extractErrorCode(error);
  const originalMessage = extractErrorMessage(error);
  
  // Verifica se tem mensagem específica para o código
  if (code && ERROR_MESSAGES[code]) {
    return ERROR_MESSAGES[code];
  }
  
  // Verifica se a mensagem original contém alguma keyword
  for (const [key, friendlyMessage] of Object.entries(ERROR_MESSAGES)) {
    if (originalMessage.toLowerCase().includes(key.toLowerCase())) {
      return friendlyMessage;
    }
  }
  
  // Se a mensagem original parece técnica demais, usa fallback
  if (
    originalMessage.includes("Exception") ||
    originalMessage.includes("Error:") ||
    originalMessage.includes("undefined") ||
    originalMessage.includes("null") ||
    originalMessage.length > 200
  ) {
    return ERROR_MESSAGES.default;
  }
  
  // Retorna a mensagem original se parecer amigável
  return originalMessage;
}

export function useApiError(): UseApiErrorResult {
  const [error, setError] = useState<ApiError | null>(null);

  const handleError = useCallback((err: unknown): ApiError => {
    const code = extractErrorCode(err);
    const message = getErrorMessage(err);
    
    const apiError: ApiError = {
      message,
      code: code || undefined,
      status: code && /^\d+$/.test(code) ? parseInt(code, 10) : undefined,
    };
    
    setError(apiError);
    return apiError;
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    error,
    isError: error !== null,
    handleError,
    clearError,
    getErrorMessage,
  };
}

// Wrapper para operações async com tratamento de erro automático
export async function withErrorHandling<T>(
  operation: () => Promise<T>,
  onError?: (error: ApiError) => void
): Promise<T | null> {
  try {
    return await operation();
  } catch (err) {
    const message = getErrorMessage(err);
    const code = extractErrorCode(err);
    
    const apiError: ApiError = {
      message,
      code: code || undefined,
      status: code && /^\d+$/.test(code) ? parseInt(code, 10) : undefined,
    };
    
    if (onError) {
      onError(apiError);
    }
    
    console.error("API Error:", apiError);
    return null;
  }
}

export default useApiError;
