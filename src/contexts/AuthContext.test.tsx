import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { clearAppLocalStorage, AuthProvider, useAuth } from "@/contexts/AuthContext";

/**
 * Regressão: nada limpava o localStorage no
 * logout, e nenhuma das chaves era isolada por user_id — loja conectada
 * (4seo_store) e caches de rollback por plataforma (shopify/nuvemshop/
 * vtex/lojaintegrada) sobreviviam à troca de conta no mesmo navegador
 * (ex.: máquina de agência compartilhada), vazando dado de um usuário
 * pro próximo que fizesse login ali.
 */

const signOutMock = vi.fn().mockResolvedValue({ error: null });
const signUpMock = vi.fn().mockResolvedValue({ data: { session: null, user: null }, error: null });
const signInWithPasswordMock = vi.fn().mockResolvedValue({ data: {}, error: null });

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signOut: (...args: unknown[]) => signOutMock(...args),
      updateUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      resetPasswordForEmail: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signInWithPassword: (...args: unknown[]) => signInWithPasswordMock(...args),
      signUp: (...args: unknown[]) => signUpMock(...args),
    },
  },
}));

describe("clearAppLocalStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("remove todas as chaves de app (loja conectada + rollbacks de todas as plataformas)", () => {
    localStorage.setItem("4seo_store", JSON.stringify({ platform: "vtex" }));
    localStorage.setItem("shopify_rollbacks_https://loja.myshopify.com", "[]");
    localStorage.setItem("nuvemshop_rollbacks_123", "[]");
    localStorage.setItem("vtex_rollbacks_MinhaLoja", "[]");
    localStorage.setItem("lojaintegrada_rollbacks_abc", "[]");

    clearAppLocalStorage();

    expect(localStorage.getItem("4seo_store")).toBeNull();
    expect(localStorage.getItem("shopify_rollbacks_https://loja.myshopify.com")).toBeNull();
    expect(localStorage.getItem("nuvemshop_rollbacks_123")).toBeNull();
    expect(localStorage.getItem("vtex_rollbacks_MinhaLoja")).toBeNull();
    expect(localStorage.getItem("lojaintegrada_rollbacks_abc")).toBeNull();
  });

  it("não mexe em chaves que não pertencem ao app (ex.: token do Supabase, preferências do navegador)", () => {
    localStorage.setItem("4seo_store", "{}");
    localStorage.setItem("sb-vwgrrqybpemfdlycrrae-auth-token", "some-supabase-session-token");
    localStorage.setItem("auth_token", "jwt-do-backend");
    localStorage.setItem("theme", "dark");

    clearAppLocalStorage();

    expect(localStorage.getItem("4seo_store")).toBeNull();
    expect(localStorage.getItem("sb-vwgrrqybpemfdlycrrae-auth-token")).toBe("some-supabase-session-token");
    expect(localStorage.getItem("auth_token")).toBe("jwt-do-backend");
    expect(localStorage.getItem("theme")).toBe("dark");
  });
});

describe("AuthContext.signOut — regressão #14", () => {
  beforeEach(() => {
    localStorage.clear();
    signOutMock.mockClear();
  });

  it("limpa o localStorage do app ao deslogar", async () => {
    localStorage.setItem("4seo_store", JSON.stringify({ platform: "nuvemshop" }));
    localStorage.setItem("nuvemshop_rollbacks_999", "[]");

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(async () => {
      await result.current.signOut();
    });

    expect(signOutMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem("4seo_store")).toBeNull();
    expect(localStorage.getItem("nuvemshop_rollbacks_999")).toBeNull();
  });
});

describe("AuthContext.signUp — e-mail já cadastrado", () => {
  beforeEach(() => {
    signUpMock.mockReset();
    signInWithPasswordMock.mockReset();
  });

  it("não promete e-mail de confirmação quando o Supabase mascara conta existente", async () => {
    signUpMock.mockResolvedValue({
      data: {
        session: null,
        user: { id: "existing", identities: [] },
      },
      error: null,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    let response: Awaited<ReturnType<typeof result.current.signUp>> | undefined;
    await act(async () => {
      response = await result.current.signUp("carolbraga@4scale.com.br", "Senha@123");
    });

    expect(response?.reason).toBe("existing_user");
    expect(response?.sessionCreated).toBe(false);
    expect(response?.error).toMatch(/já possui uma conta/i);
    expect(signInWithPasswordMock).not.toHaveBeenCalled();
  });
});
