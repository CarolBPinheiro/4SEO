import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useIntegrationSeo, IntegrationApi, IntegrationProposal } from "@/hooks/useIntegrationSeo";

/**
 * Regressão: `selectProduct`/`selectCategory`
 * filtravam o estado agregado `proposals` para manter só o item recém
 * selecionado, descartando propostas aprovadas (mas ainda não aplicadas)
 * de QUALQUER outro produto/categoria a cada troca de seleção. A UI
 * (IntegrationAnalise.tsx) já filtra por item selecionado para exibição,
 * então o estado agregado nunca deveria ser podado ao trocar de seleção.
 */

function makeProposal(overrides: Partial<IntegrationProposal>): IntegrationProposal {
  return {
    id: "p1",
    product_id: 1,
    field_name: "seo_title",
    original_value: "Antigo",
    proposed_value: "Novo",
    reasoning: "r",
    status: "pending",
    created_at: "2026-01-01T00:00:00",
    content_type: "product",
    ...overrides,
  };
}

function makeApi(overrides: Partial<IntegrationApi> = {}): IntegrationApi {
  return {
    products: vi.fn().mockResolvedValue({ products: [], total: 0 }),
    analyzeProduct: vi.fn().mockResolvedValue({ score: 50, issues: [], recommendations: [] }),
    optimizeProduct: vi.fn().mockResolvedValue({ proposals: [], total: 0 }),
    categories: vi.fn().mockResolvedValue({ categories: [], total: 0 }),
    analyzeCategory: vi.fn().mockResolvedValue({ score: 50, issues: [], recommendations: [] }),
    optimizeCategory: vi.fn().mockResolvedValue({ proposals: [], total: 0 }),
    listProposals: vi.fn().mockResolvedValue({ proposals: [], total: 0 }),
    approveProposals: vi.fn().mockResolvedValue({ approved: 1 }),
    rejectProposals: vi.fn().mockResolvedValue({ rejected: 1 }),
    applyProposals: vi.fn().mockResolvedValue({ applied: 0, rollback_records: [] }),
    listRollbacks: vi.fn().mockResolvedValue({ records: [] }),
    rollbackDirect: vi.fn().mockResolvedValue({ rolled_back: 1 }),
    ...overrides,
  };
}

describe("useIntegrationSeo — regressão (propostas somem ao trocar seleção)", () => {
  beforeEach(() => {
    if (typeof window !== "undefined") window.localStorage.clear();
  });

  it("mantém proposta aprovada de um produto ao selecionar outro produto", async () => {
    const proposalA = makeProposal({ id: "prod-a-1", product_id: 1, content_type: "product" });
    const api = makeApi({
      optimizeProduct: vi.fn().mockResolvedValue({ proposals: [proposalA], total: 1 }),
    });
    const { result } = renderHook(() => useIntegrationSeo(api, "vtex"));

    act(() => result.current.setConnectionFromStore("store-1"));

    await act(async () => {
      await result.current.generateProductProposals(1);
    });
    expect(result.current.proposals).toHaveLength(1);

    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });
    expect(result.current.proposals.find(p => p.id === "prod-a-1")?.status).toBe("approved");

    // Troca de seleção para outro produto (sem propostas próprias ainda)
    await act(async () => {
      await result.current.selectProduct({ id: 2, name: "Produto B" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });

  it("mantém proposta aprovada de um produto ao selecionar uma categoria", async () => {
    const proposalA = makeProposal({ id: "prod-a-1", product_id: 1, content_type: "product" });
    const api = makeApi({
      optimizeProduct: vi.fn().mockResolvedValue({ proposals: [proposalA], total: 1 }),
    });
    const { result } = renderHook(() => useIntegrationSeo(api, "vtex"));

    act(() => result.current.setConnectionFromStore("store-1"));

    await act(async () => {
      await result.current.generateProductProposals(1);
    });
    await act(async () => {
      await result.current.approveProposals(["prod-a-1"]);
    });

    await act(async () => {
      await result.current.selectCategory({ id: 9, name: "Categoria X" });
    });

    const survivor = result.current.proposals.find(p => p.id === "prod-a-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });

  it("preserva propostas aprovadas de uma categoria ao trocar para outra categoria", async () => {
    const proposalCat = makeProposal({ id: "cat-1-1", product_id: 1, content_type: "category" });
    const api = makeApi({
      optimizeCategory: vi.fn().mockResolvedValue({ proposals: [proposalCat], total: 1 }),
    });
    const { result } = renderHook(() => useIntegrationSeo(api, "vtex"));

    act(() => result.current.setConnectionFromStore("store-1"));

    await act(async () => {
      await result.current.generateCategoryProposals(1);
    });
    await act(async () => {
      await result.current.approveProposals(["cat-1-1"]);
    });

    await act(async () => {
      await result.current.selectCategory({ id: 2, name: "Categoria Y" });
    });

    const survivor = result.current.proposals.find(p => p.id === "cat-1-1");
    expect(survivor).toBeDefined();
    expect(survivor?.status).toBe("approved");
  });
});
