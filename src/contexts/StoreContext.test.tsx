import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { StoreProvider, useStore } from "@/contexts/StoreContext";

const statusMock = vi.fn();
const billingState = {
  canUseAppPreview: true,
  loading: false,
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "user-1" } }),
}));

vi.mock("@/contexts/BillingContext", () => ({
  useBilling: () => billingState,
}));

vi.mock("@/lib/apiClient", () => ({
  getToken: () => "test-token",
  api: {
    integrations: {
      status: (...args: unknown[]) => statusMock(...args),
      disconnect: vi.fn(),
    },
  },
}));

function StoreProbe() {
  const { connected, store } = useStore();
  return (
    <div>
      <span>{connected ? "connected" : "disconnected"}</span>
      <span>{store?.platform || "none"}</span>
    </div>
  );
}

describe("StoreContext — trial vs paid store status", () => {
  beforeEach(() => {
    localStorage.clear();
    statusMock.mockReset();
    billingState.canUseAppPreview = true;
    billingState.loading = false;
    statusMock.mockResolvedValue({
      connected: true,
      platform: "nuvemshop",
      store_name: "Minha Loja",
      shop_url: "https://loja.nuvemshop.com.br",
      store_id: "123",
    });
  });

  it("carrega a loja conectada no trial (canUseAppPreview)", async () => {
    billingState.canUseAppPreview = true;

    render(
      <StoreProvider>
        <StoreProbe />
      </StoreProvider>,
    );

    await waitFor(() => {
      expect(statusMock).toHaveBeenCalled();
      expect(screen.getByText("connected")).toBeInTheDocument();
    });
    expect(screen.getByText("nuvemshop")).toBeInTheDocument();
  });

  it("não consulta status nem marca conectada sem trial/pago", async () => {
    billingState.canUseAppPreview = false;

    render(
      <StoreProvider>
        <StoreProbe />
      </StoreProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("disconnected")).toBeInTheDocument();
    });
    expect(statusMock).not.toHaveBeenCalled();
  });
});
