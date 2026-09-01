import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Integracoes from "@/screens/Integracoes";

vi.mock("@/contexts/StoreContext", () => ({
  useStore: () => ({
    store: null,
    connected: false,
    setStore: vi.fn(),
    refreshStatus: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

vi.mock("@/contexts/DemoContext", () => ({
  useDemo: () => ({ enabled: true, loading: false }),
}));

vi.mock("@/lib/apiClient", () => ({
  api: {
    nuvemshop: { getAuthUrl: vi.fn() },
    shopify: { getAuthUrl: vi.fn(), connect: vi.fn() },
    demo: { connect: vi.fn(), connectGsc: vi.fn() },
  },
}));

describe("Integracoes — sandbox demo", () => {
  it("mostra Conectar loja demo em cada plataforma", () => {
    render(
      <MemoryRouter>
        <Integracoes />
      </MemoryRouter>,
    );
    const buttons = screen.getAllByRole("button", { name: /Conectar loja demo/i });
    expect(buttons.length).toBe(4);
    expect(screen.getByRole("button", { name: /Conectar Search Console demo/i })).toBeInTheDocument();
  });
});
