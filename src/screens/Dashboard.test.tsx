import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "@/screens/Dashboard";
import { api } from "@/lib/apiClient";

/**
 * Regressão: ao conectar uma loja, o usuário era
 * redirecionado para o Dashboard após um setTimeout fixo de 1.5s em
 * Integracoes.tsx — tempo que não guarda nenhuma relação com o scan inicial
 * real (disparado em background no backend, pode levar minutos). O Dashboard
 * então mostrava um banner ESTÁTICO ("Seu site ainda não foi analisado" +
 * botão manual), sem nenhum sinal de que uma análise já estava rodando —
 * o usuário precisava adivinhar e clicar manualmente.
 *
 * Fix: o Dashboard agora detecta sozinho (site conectado com 0 páginas
 * escaneadas) e dispara o mesmo fluxo de refresh/polling automaticamente ao
 * montar, exibindo um banner de "Estamos analisando seu site..." em vez do
 * CTA estático enquanto isso acontece.
 */

vi.mock("@/contexts/StoreContext", () => ({
  useStore: () => ({ connected: true }),
}));

vi.mock("@/contexts/BillingContext", () => ({
  useBilling: () => ({
    hasActiveSubscription: true,
    loading: false,
    subscribeUrl: "http://localhost:3000/#planos",
    subscription: { status: "active" },
    refreshSubscription: vi.fn(),
  }),
}));

vi.mock("@/lib/apiClient", () => ({
  api: {
    dashboard: {
      summary: vi.fn(),
      scan: vi.fn(),
      oportunidades: vi.fn(),
    },
  },
}));

const notYetAnalyzed = {
  connected: true,
  total_pages_scanned: 0,
  last_scan: { completed_at: null, pages_scanned: 0, tasks_created: 0 },
  saude_seo: 0,
  visibilidade_seo: 0,
  potencial_seo_label: "--",
  potencial_seo_color: "cinza",
  oportunidades_encontradas: 0,
  cliques_organicos: 0,
  termos_count: 0,
};

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("Dashboard — regressão (sinalização automática de scan em andamento)", () => {
  beforeEach(() => {
    vi.mocked(api.dashboard.summary).mockReset();
    vi.mocked(api.dashboard.scan).mockReset();
    vi.mocked(api.dashboard.oportunidades).mockReset();
    vi.mocked(api.dashboard.oportunidades).mockResolvedValue({
      connected: true,
      oportunidades: [],
      counts: {},
      filtros_disponiveis: [],
    });
  });

  it("dispara o scan sozinho (sem clique do usuário) e mostra sinalização de 'analisando' ao montar com 0 páginas", async () => {
    vi.mocked(api.dashboard.summary).mockResolvedValueOnce(notYetAnalyzed);
    // Nunca resolve — simula o scan em andamento; o teste só precisa
    // confirmar que foi disparado e que a UI sinaliza "analisando".
    vi.mocked(api.dashboard.scan).mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await flush();
    await flush();

    expect(api.dashboard.scan).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Estamos analisando seu site/i)).toBeInTheDocument();
    expect(screen.queryByText(/Seu site ainda não foi analisado/i)).not.toBeInTheDocument();
  });

  it("não dispara scan automático quando o site já tem páginas escaneadas", async () => {
    vi.mocked(api.dashboard.summary).mockResolvedValueOnce({
      ...notYetAnalyzed,
      total_pages_scanned: 5,
      last_scan: { completed_at: "2026-01-01T00:00:00Z", pages_scanned: 5, tasks_created: 1 },
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await flush();
    await flush();

    expect(api.dashboard.scan).not.toHaveBeenCalled();
    expect(screen.queryByText(/Estamos analisando seu site/i)).not.toBeInTheDocument();
  });
});
