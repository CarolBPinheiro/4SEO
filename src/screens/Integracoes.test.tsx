import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Integracoes from "@/screens/Integracoes";

/**
 * Regressão: o diálogo de "Remover integração"
 * fechava incondicionalmente ao clicar em "Remover", mesmo quando a
 * desconexão falhava de verdade no backend (ex.: falha ao apagar as
 * credenciais salvas) — o usuário via a tela como se tivesse desconectado
 * com sucesso, e a loja "reaparecia" sozinha pouco depois (o mesmo loop de
 * reconexão relatado originalmente para o Shopify).
 *
 * Fix: StoreContext.disconnect() agora propaga a falha em vez de engolir, e
 * o diálogo em Integracoes.tsx só fecha em caso de sucesso — em caso de
 * erro, permanece aberto mostrando a mensagem para o usuário tentar de novo.
 */

const disconnectMock = vi.fn();

vi.mock("@/contexts/StoreContext", () => ({
  useStore: () => ({
    store: { platform: "shopify", name: "Minha Loja", url: "https://loja.myshopify.com", storeId: "loja" },
    connected: true,
    setStore: vi.fn(),
    refreshStatus: vi.fn(),
    disconnect: disconnectMock,
  }),
}));

vi.mock("@/lib/apiClient", () => ({
  api: {
    nuvemshop: { getAuthUrl: vi.fn() },
    shopify: { getAuthUrl: vi.fn(), connect: vi.fn() },
  },
}));

function openRemoveDialog() {
  const disconnectButtons = screen.getAllByRole("button", { name: /Desconectar/i });
  fireEvent.click(disconnectButtons[0]);
}

describe("Integracoes — regressão (diálogo de remover não finge sucesso)", () => {
  beforeEach(() => {
    disconnectMock.mockReset();
  });

  it("fecha o diálogo quando a desconexão dá certo", async () => {
    disconnectMock.mockResolvedValueOnce(undefined);

    render(
      <MemoryRouter>
        <Integracoes />
      </MemoryRouter>
    );

    openRemoveDialog();
    expect(screen.getByText(/Deseja realmente remover esta integração/i)).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^Remover$/i }));
    });

    expect(disconnectMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/Deseja realmente remover esta integração/i)).not.toBeInTheDocument();
  });

  it("mantém o diálogo aberto e mostra o erro quando a desconexão falha", async () => {
    disconnectMock.mockRejectedValueOnce(new Error("Falha ao apagar as credenciais salvas"));

    render(
      <MemoryRouter>
        <Integracoes />
      </MemoryRouter>
    );

    openRemoveDialog();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^Remover$/i }));
    });

    expect(disconnectMock).toHaveBeenCalledTimes(1);
    // Diálogo continua aberto — não finge que deu certo
    expect(screen.getByText(/Deseja realmente remover esta integração/i)).toBeInTheDocument();
    expect(screen.getByText(/Falha ao apagar as credenciais salvas/i)).toBeInTheDocument();
  });
});
