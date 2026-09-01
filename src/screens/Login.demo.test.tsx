import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "@/screens/Login";

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    signIn: vi.fn(),
    signUp: vi.fn(),
    resetPassword: vi.fn(),
    signOut: vi.fn(),
    user: null,
    loading: false,
  }),
}));

vi.mock("@/contexts/DemoContext", () => ({
  useDemo: () => ({
    enabled: true,
    loading: false,
    loginEmail: "demo@demo.4seo.local",
    loginPassword: "Demo4SEO!local",
    accounts: [],
  }),
}));

vi.mock("@/lib/billingClaim", () => ({
  claimPendingCheckout: vi.fn(),
  persistBillingRef: vi.fn(),
  readPendingBillingRef: () => null,
}));

describe("Login — sandbox demo", () => {
  it("preenche a conta demo no atalho", () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Preencher conta demo/i }));

    expect(screen.getByPlaceholderText("Endereço de e-mail")).toHaveValue(
      "demo@demo.4seo.local",
    );
    expect(screen.getByPlaceholderText("Senha")).toHaveValue("Demo4SEO!local");
  });
});
