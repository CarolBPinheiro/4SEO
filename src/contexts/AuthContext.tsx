import { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { setToken } from "@/lib/apiClient";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
}

interface AuthContextType extends AuthState {
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signUp: (email: string, password: string) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error?: string }>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function getAuthRedirectUrl() {
  const configuredUrl = import.meta.env.VITE_AUTH_REDIRECT_URL;
  if (configuredUrl) {
    return configuredUrl;
  }
  return `${window.location.origin}/login`;
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
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    loading: true,
  });

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({ user: session?.user ?? null, session, loading: false });
      if (session?.access_token) {
        setToken(session.access_token);
      }
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setState({ user: session?.user ?? null, session, loading: false });
        if (session?.access_token) {
          setToken(session.access_token);
        } else {
          setToken(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error: error.message };
    return {};
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: getAuthRedirectUrl(),
      },
    });
    if (error) return { error: error.message };
    return {};
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setToken(null);
    clearAppLocalStorage();
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: getAuthRedirectUrl(),
    });
    if (error) return { error: error.message };
    return {};
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signUp, signOut, resetPassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
