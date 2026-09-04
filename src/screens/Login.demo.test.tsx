import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "@/screens/Login";

const authMock = {
  signIn: vi.fn(),
  signUp: vi.fn(),
  resetPassword: vi.fn(),
  updatePassword: vi.fn(),
  clearPasswordRecovery: vi.fn(),
  signOut: vi.fn(),
  user: null as { id: string } | null,
  loading: false,
  passwordRecovery: false,
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => authMock,
}));

vi.mock("@/lib/billingClaim", () => ({
  claimPendingCheckout: vi.fn(),
  persistBillingRef: vi.fn(),
  readPendingBillingRef: () => null,
}));

vi.mock("@/contexts/BillingContext", () => ({
  fetchSubscription: vi.fn().mockResolvedValue({ accessLevel: "none" }),
}));

describe("Login — recuperação de senha", () => {
  it("exibe o formulário de login por padrão", () => {
    authMock.passwordRecovery = false;
    authMock.user = null;

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /que bom ver você de volta/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Fazer login/i })).toBeInTheDocument();
  });

  it("abre o formulário de nova senha no fluxo passwordRecovery", () => {
    authMock.passwordRecovery = true;
    authMock.user = { id: "user-1" };

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /Defina sua nova senha/i }),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Nova senha")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Confirmar nova senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Atualizar senha/i })).toBeInTheDocument();
  });
});
