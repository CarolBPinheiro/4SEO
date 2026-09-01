import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ signOut: vi.fn() }),
}));

vi.mock("@/contexts/BillingContext", () => ({
  useBilling: () => ({
    hasFullAccess: true,
    hasTrialAccess: false,
    canUseAppPreview: true,
    loading: false,
    subscribeUrl: "http://localhost:3000/#planos",
    subscription: { status: "active", planId: "scale", trialEndsAt: null },
  }),
}));

vi.mock("@/contexts/StoreContext", () => ({
  useStore: () => ({
    connected: true,
    store: { name: "Loja Demo", url: "https://demo.example" },
  }),
}));

const demoState = { enabled: true };

vi.mock("@/contexts/DemoContext", () => ({
  useDemo: () => demoState,
}));

describe("AppLayout — banner de demonstração", () => {
  it("mostra o aviso quando o backend está em DEMO_MODE", () => {
    demoState.enabled = true;
    render(
      <MemoryRouter>
        <AppLayout>
          <p>conteúdo</p>
        </AppLayout>
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      /Ambiente de demonstração — dados fictícios/i,
    );
  });

  it("esconde o aviso fora do sandbox", () => {
    demoState.enabled = false;
    render(
      <MemoryRouter>
        <AppLayout>
          <p>conteúdo</p>
        </AppLayout>
      </MemoryRouter>,
    );
    expect(screen.queryByText(/Ambiente de demonstração/i)).not.toBeInTheDocument();
  });
});
