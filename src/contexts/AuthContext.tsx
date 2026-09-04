import { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { AuthChangeEvent, User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { setToken } from "@/lib/apiClient";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  /** Sessão originada do link de recuperação de senha — não redirecionar/encerrar. */
  passwordRecovery: boolean;
}

interface AuthContextType extends AuthState {
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signUp: (
    email: string,
    password: string,
  ) => Promise<{ error?: string; sessionCreated?: boolean }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error?: string }>;
  updatePassword: (password: string) => Promise<{ error?: string }>;
  clearPasswordRecovery: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

/** Persiste o modo recovery entre o evento do SDK e um eventual refresh da página. */
const PASSWORD_RECOVERY_STORAGE_KEY = "4seo_password_recovery";

function getAuthRedirectUrl() {
  const configuredUrl = import.meta.env.VITE_AUTH_REDIRECT_URL;
  if (configuredUrl) {
    return configuredUrl;
  }
  return `${window.location.origin}/login`;
}

/** Redirect do e-mail de recuperação — `type=recovery` permite detectar o fluxo antes do signOut. */
function getPasswordRecoveryRedirectUrl() {
  const url = new URL(getAuthRedirectUrl());
  url.searchParams.set("type", "recovery");
  return url.toString();
}

function readPasswordRecoveryFlag(): boolean {
  try {
    return sessionStorage.getItem(PASSWORD_RECOVERY_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function writePasswordRecoveryFlag(active: boolean) {
  try {
    if (active) {
      sessionStorage.setItem(PASSWORD_RECOVERY_STORAGE_KEY, "1");
    } else {
      sessionStorage.removeItem(PASSWORD_RECOVERY_STORAGE_KEY);
    }
  } catch {
    // sessionStorage indisponível — o estado em memória ainda cobre o fluxo atual
  }
}

/** Detecta redirect de recovery nos params (hash implícito ou query). */
function isRecoveryRedirectUrl(): boolean {
  if (typeof window === "undefined") return false;
  const search = new URLSearchParams(window.location.search);
  if (search.get("type") === "recovery") return true;
  const rawHash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  if (!rawHash) return false;
  return new URLSearchParams(rawHash).get("type") === "recovery";
}

/** Há tokens/código de auth na URL — aguardar onAuthStateChange antes de liberar o Login. */
function hasAuthCallbackInUrl(): boolean {
  if (typeof window === "undefined") return false;
  const search = new URLSearchParams(window.location.search);
  if (search.has("code") || search.get("type") === "recovery") return true;
  const rawHash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  if (!rawHash) return false;
  const hash = new URLSearchParams(rawHash);
  return hash.has("access_token") || hash.get("type") === "recovery";
}

function isPasswordRecoveryEvent(event: AuthChangeEvent): boolean {
  return event === "PASSWORD_RECOVERY";
}

// Prefixos de chaves gravadas no localStorage por este app (loja conectada +
// caches de rollback por plataforma — ver StoreContext/useNuvemshop/useShopify/
// useIntegrationSeo). Nenhuma delas é isolada por user_id: se o navegador é
// compartilhado (ex.: máquina de agência) e outro usuário faz login logo em
// seguida, ele herdava esses dados (inclusive histórico de rollback de
// otimizações aplicadas) até sobrescrever cada chave manualmente. Limpar tudo
// no logout evita esse vazamento entre contas.
const APP_LOCAL_STORAGE_PREFIXES = [
  "4seo_store",
  "shopify_rollbacks_",
  "nuvemshop_rollbacks_",
  "vtex_rollbacks_",
  "lojaintegrada_rollbacks_",
];

export function clearAppLocalStorage() {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && APP_LOCAL_STORAGE_PREFIXES.some((prefix) => key.startsWith(prefix))) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => localStorage.removeItem(key));
  } catch {
    // localStorage indisponível (ex.: modo privado em alguns navegadores) — nada a fazer
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    user: null,
    session: null,
    loading: true,
    passwordRecovery: isRecoveryRedirectUrl() || readPasswordRecoveryFlag(),
  }));

  const markPasswordRecovery = useCallback((active: boolean) => {
    writePasswordRecoveryFlag(active);
    setState((prev) =>
      prev.passwordRecovery === active ? prev : { ...prev, passwordRecovery: active },
    );
  }, []);

  useEffect(() => {
    if (isRecoveryRedirectUrl()) {
      writePasswordRecoveryFlag(true);
    }

    const awaitingAuthCallback = hasAuthCallbackInUrl();

    // Get initial session (não libera loading se ainda há callback OAuth/recovery na URL)
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState((prev) => ({
        ...prev,
        user: session?.user ?? null,
        session,
        loading: awaitingAuthCallback ? prev.loading : false,
        passwordRecovery:
          prev.passwordRecovery || isRecoveryRedirectUrl() || readPasswordRecoveryFlag(),
      }));
      if (session?.access_token) {
        setToken(session.access_token);
      }
    });

    // Listen for auth changes — PASSWORD_RECOVERY chega ao clicar no link do e-mail
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      const recovery =
        isPasswordRecoveryEvent(event) ||
        isRecoveryRedirectUrl() ||
        readPasswordRecoveryFlag();

      if (isPasswordRecoveryEvent(event)) {
        writePasswordRecoveryFlag(true);
      }

      if (!session) {
        writePasswordRecoveryFlag(false);
      }

      setState({
        user: session?.user ?? null,
        session,
        loading: false,
        passwordRecovery: Boolean(session) && recovery,
      });

      if (session?.access_token) {
        setToken(session.access_token);
      } else {
        setToken(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error: error.message };
    return {};
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        // Após confirmar e-mail (se exigido), volta ao app e o post-auth manda ao /trial
        emailRedirectTo: `${window.location.origin}/login`,
      },
    });
    if (error) return { error: error.message };

    // Dropbox-like: se o Supabase já devolveu sessão, segue autenticado
    if (data.session?.access_token) {
      setToken(data.session.access_token);
      return { sessionCreated: true as const };
    }

    // Sem sessão (ex.: confirmação de e-mail ligada) — tenta login imediato
    const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (signInError) {
      return {
        sessionCreated: false as const,
        error:
          "Conta criada. Confirme o e-mail enviado e faça login para escolher seu plano.",
      };
    }
    if (signInData.session?.access_token) {
      setToken(signInData.session.access_token);
    }
    return { sessionCreated: true as const };
  }, []);

  const clearPasswordRecovery = useCallback(() => {
    markPasswordRecovery(false);
  }, [markPasswordRecovery]);

  const signOut = useCallback(async () => {
    writePasswordRecoveryFlag(false);
    await supabase.auth.signOut();
    setToken(null);
    clearAppLocalStorage();
    setState((prev) => ({ ...prev, passwordRecovery: false }));
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: getPasswordRecoveryRedirectUrl(),
    });
    if (error) return { error: error.message };
    return {};
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password });
    if (error) {
      const message = error.message.toLowerCase();
      if (message.includes("same password") || message.includes("should be different")) {
        return { error: "A nova senha deve ser diferente da senha atual." };
      }
      if (message.includes("session") || message.includes("not authenticated")) {
        return {
          error:
            "Link de recuperação inválido ou expirado. Solicite um novo link em “Esqueceu sua senha?”.",
        };
      }
      return { error: "Não foi possível atualizar a senha. Tente novamente." };
    }
    writePasswordRecoveryFlag(false);
    setState((prev) => ({ ...prev, passwordRecovery: false }));
    return {};
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        signIn,
        signUp,
        signOut,
        resetPassword,
        updatePassword,
        clearPasswordRecovery,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
