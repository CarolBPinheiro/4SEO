import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useShopify } from "@/hooks/useShopify";
import { api } from "@/lib/apiClient";

/**
 * Regressão (mesma causa raiz corrigida em useIntegrationSeo.ts para VTEX/Loja Integrada, mas que também existia,
 * sem correção, no hook do Shopify — a integração mais madura e mais usada):
 * selectProduct/selectCollection/selectPage/selectArticle filtravam o
 * estado agregado `proposals` para manter só as propostas do item
 * recém-selecionado a cada troca de seleção, descartando propostas
 * aprovadas de QUALQUER outro item. A UI (ShopifyAnalise.tsx) já filtra
 * por item selecionado via `filteredProposals` só para exibição.
 */

vi.mock("@/lib/apiClient", () => ({
  api: {
    shopify: {
      connect: vi.fn(),
      products: vi.fn(),
      collections: vi.fn(),
      pages: vi.fn(),
      blogs: vi.fn(),
      articles: vi.fn(),
      analyzeProduct: vi.fn(),
      analyzeCollection: vi.fn(),
      analyzePage: vi.fn(),
      analyzeArticle: vi.fn(),
      optimizeProduct: vi.fn(),
      optimizeCollection: vi.fn(),
      optimizePage: vi.fn(),
      optimizeArticle: vi.fn(),
      listProposals: vi.fn(),
      approveProposals: vi.fn(),
      rejectProposals: vi.fn(),
      listRollbacks: vi.fn(),
      applyProposals: vi.fn(),
      rollbackDirect: vi.fn(),
    },
  },
}));

describe("useShopify — regressão (propostas somem ao trocar seleção)", () => {
  beforeEach(() => {
    vi.mocked(api.shopify.connect).mockReset().mockResolvedValue({ success: true, shop: { shop_name: "Loja Teste" } });
    vi.mocked(api.shopify.analyzeProduct).mockReset().mockResolvedValue({ score: 50, issues: [], recommendations: [] });
    vi.mocked(api.shopify.analyzeCollection).mockReset().mockResolvedValue({ score: 50, issues: [], recommendations: [] });
    vi.mocked(api.shopify.approveProposals).mockReset().mockResolvedValue({ approved: 1 });
  });

  it("mantém proposta aprovada de um produto ao selecionar outro produto", async () => {
    const proposalA = {
      id: "prod-a-1", product_id: 1, field: "title", original_value: "Antigo", proposed_value: "Novo",
      reasoning: "r", status: "pending" as const, created_at: "2026-01-01T00:00:00", content_type: "product" as const,
    };
    vi.mocked(api.shopify.optimizeProduct).mockResolvedValue({ proposals: [proposalA], total: 1 });

    const { result } = renderHook(() => useShopify());

    await act(async () => {
      await result.current.connect("https://loja.myshopify.com", "tok");
    });

    await act(async () => {
      await result.current.generateProposals(1);
    });
    expect(result.current.proposals).toHaveLength(1);

    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });
    expect(result.current.proposals.find(p => p.id === "prod-a-1")?.status).toBe("approved");

    await act(async () => {
      await result.current.selectProduct({ id: 2, title: "Produto B", handle: "produto-b" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });

  it("mantém proposta aprovada de um produto ao selecionar uma coleção", async () => {
    const proposalA = {
      id: "prod-a-1", product_id: 1, field: "title", original_value: "Antigo", proposed_value: "Novo",
      reasoning: "r", status: "pending" as const, created_at: "2026-01-01T00:00:00", content_type: "product" as const,
    };
    vi.mocked(api.shopify.optimizeProduct).mockResolvedValue({ proposals: [proposalA], total: 1 });

    const { result } = renderHook(() => useShopify());

    await act(async () => {
      await result.current.connect("https://loja.myshopify.com", "tok");
    });
    await act(async () => {
      await result.current.generateProposals(1);
    });
    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });

    await act(async () => {
      await result.current.selectCollection({ id: 9, title: "Coleção X", handle: "colecao-x", collection_type: "custom" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });
});
