import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useNuvemshop } from "@/hooks/useNuvemshop";
import { api } from "@/lib/apiClient";

/**
 * Regressão (mesma causa raiz corrigida em useIntegrationSeo.ts para VTEX/Loja Integrada, mas que também existia,
 * sem correção, no hook da Nuvemshop — a integração mais madura e mais
 * usada): selectProduct/selectCategory/selectPage/selectBlogPost filtravam
 * o estado agregado `proposals` para manter só as propostas do item
 * recém-selecionado a cada troca de seleção, descartando propostas
 * aprovadas de QUALQUER outro item. A UI (NuvemshopAnalise.tsx) já filtra
 * por item selecionado via `filteredProposals` só para exibição.
 */

vi.mock("@/lib/apiClient", () => ({
  api: {
    nuvemshop: {
      products: vi.fn(),
      categories: vi.fn(),
      pages: vi.fn(),
      blogPosts: vi.fn(),
      analyzeProduct: vi.fn(),
      analyzeCategory: vi.fn(),
      analyzePage: vi.fn(),
      analyzeBlogPost: vi.fn(),
      optimizeProduct: vi.fn(),
      optimizeCategory: vi.fn(),
      optimizePage: vi.fn(),
      optimizeBlogPost: vi.fn(),
      listProposals: vi.fn(),
      approveProposals: vi.fn(),
      rejectProposals: vi.fn(),
      listRollbacks: vi.fn(),
      applyProposals: vi.fn(),
      rollbackDirect: vi.fn(),
    },
  },
}));

describe("useNuvemshop — regressão (propostas somem ao trocar seleção)", () => {
  beforeEach(() => {
    vi.mocked(api.nuvemshop.analyzeProduct).mockReset().mockResolvedValue({ score: 50, issues: [], recommendations: [] });
    vi.mocked(api.nuvemshop.analyzeCategory).mockReset().mockResolvedValue({ score: 50, issues: [], recommendations: [] });
    vi.mocked(api.nuvemshop.approveProposals).mockReset().mockResolvedValue({ approved: 1 });
  });

  it("mantém proposta aprovada de um produto ao selecionar outro produto", async () => {
    const proposalA = {
      id: "prod-a-1", product_id: 1, field_name: "title", original_value: "Antigo", proposed_value: "Novo",
      reasoning: "r", status: "pending" as const, created_at: "2026-01-01T00:00:00", content_type: "product" as const,
    };
    vi.mocked(api.nuvemshop.optimizeProduct).mockResolvedValue({ proposals: [proposalA], total: 1 });

    const { result } = renderHook(() => useNuvemshop());

    act(() => result.current.setConnectionFromOAuth("store-1", "Loja Teste"));

    await act(async () => {
      await result.current.generateProductProposals(1);
    });
    expect(result.current.proposals).toHaveLength(1);

    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });
    expect(result.current.proposals.find(p => p.id === "prod-a-1")?.status).toBe("approved");

    await act(async () => {
      await result.current.selectProduct({ id: 2, name: "Produto B", handle: "produto-b" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });

  it("mantém proposta aprovada de um produto ao selecionar uma categoria", async () => {
    const proposalA = {
      id: "prod-a-1", product_id: 1, field_name: "title", original_value: "Antigo", proposed_value: "Novo",
      reasoning: "r", status: "pending" as const, created_at: "2026-01-01T00:00:00", content_type: "product" as const,
    };
    vi.mocked(api.nuvemshop.optimizeProduct).mockResolvedValue({ proposals: [proposalA], total: 1 });

    const { result } = renderHook(() => useNuvemshop());

    act(() => result.current.setConnectionFromOAuth("store-1", "Loja Teste"));

    await act(async () => {
      await result.current.generateProductProposals(1);
    });
    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });

    await act(async () => {
      await result.current.selectCategory({ id: 9, name: "Categoria X", handle: "categoria-x" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });
});
