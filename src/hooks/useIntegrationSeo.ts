import { useState, useCallback, useEffect } from "react";

/**
 * Motor compartilhado dos hooks de integração VTEX / Loja Integrada.
 *
 * As duas plataformas expõem exatamente o mesmo contrato de API no backend
 * (produtos, categorias, propostas, rollback — protocolo espelhado do
 * useNuvemshop). Este hook genérico evita duplicar o motor; useVtex e
 * useLojaIntegrada são wrappers finos que injetam o namespace da API.
 */

export interface IntegrationProduct {
  id: number;
  name: string;
  // Campos específicos por plataforma (todos opcionais no shape comum)
  title?: string;          // VTEX: Title (title tag)
  link_id?: string;        // VTEX: LinkId (slug)
  handle?: string;         // LI: apelido (slug)
  description?: string;
  seo_title?: string;      // LI: seo.title
  seo_description?: string;
  seo_keywords?: string;   // LI: seo.keyword
  keywords?: string;       // VTEX: KeyWords
  brand?: string;
  url?: string;
  images?: Array<{ id?: number | string; src?: string; alt?: string | null }>;
  is_active?: boolean;
  ativo?: boolean;
}

export interface IntegrationCategory {
  id: number;
  name: string;
  title?: string;
  description?: string;
  keywords?: string;
  seo_title?: string;
  seo_description?: string;
  seo_keywords?: string;
  parent_id?: number | null;
  father_category_id?: number | null;
  url?: string;
  products_count?: number;
}

export interface IntegrationProposal {
  id: string;
  product_id: number;
  field_name: string;
  original_value: string | null;
  proposed_value: string;
  reasoning: string;
  status: "pending" | "approved" | "applied" | "rejected" | "rolled_back";
  created_at: string;
  optimization_type?: string;
  content_type?: "product" | "category";
  priority?: "high" | "medium" | "low";
  impact?: "ranking" | "ctr" | "conversao" | "visibilidade";
  effort?: "low" | "medium" | "high";
  target_keyword?: string;
  pre_metrics?: { clicks?: number; impressions?: number; ctr?: number; position?: number };
  transparencia?: {
    atributos?: { status: string; atributos: string[]; tag: string; descricao: string };
    semantica?: { status: string; total: number; keywords_incorporadas: string[]; tag: string; descricao: string };
  };
}

export interface IntegrationRollback {
  id: string;
  shop_url?: string;
  product_id: number;
  field_name: string;
  original_value: string | null;
  new_value: string;
  applied_at: string;
  rolled_back: boolean;
  rolled_back_at?: string | null;
  content_type?: "product" | "category";
  optimization_type?: string;
}

export interface IntegrationSEOAnalysis {
  score: number;
  score_justification?: string;
  summary?: string;
  issues: Array<{
    type: string;
    message?: string;
    severity: string;
    title?: string;
    why?: string;
    impact?: string;
    recommendation?: string;
    suggested_fields?: string[];
  }>;
  recommendations: string[];
  opportunities?: string[];
  recommended_actions?: string[];
  source?: string;
  type?: "product" | "category";
}

export interface IntegrationConnection {
  connected: boolean;
  store_id: string;
  store_name?: string;
}

export interface ToastData {
  message: string;
  type: "info" | "success" | "error" | "warning";
}

// Shapes de resposta do backend (contrato espelhado do Nuvemshop)
export interface ProductsResponse { products?: IntegrationProduct[]; total?: number }
export interface CategoriesResponse { categories?: IntegrationCategory[]; total?: number }
export interface ProposalsResponse { proposals?: IntegrationProposal[]; total?: number }
export interface ApplyResponse {
  applied?: number;
  rollback_records?: IntegrationRollback[];
  errors?: string[];
}
export interface RollbacksResponse {
  records?: IntegrationRollback[];
  rollback_records?: IntegrationRollback[];
  total?: number;
}

/** Contrato de API que ambas as plataformas implementam (api.vtex / api.lojaintegrada) */
export interface IntegrationApi {
  products: (store_id: string, limit?: number) => Promise<ProductsResponse>;
  analyzeProduct: (store_id: string, product_id: number) => Promise<IntegrationSEOAnalysis>;
  optimizeProduct: (store_id: string, product_id: number, options?: {
    target_keyword?: string;
    recommended_actions?: string[];
  }) => Promise<ProposalsResponse>;
  categories: (store_id: string, limit?: number) => Promise<CategoriesResponse>;
  analyzeCategory: (store_id: string, category_id: number) => Promise<IntegrationSEOAnalysis>;
  optimizeCategory: (store_id: string, category_id: number, target_keyword?: string) => Promise<ProposalsResponse>;
  listProposals: (store_id: string, status?: string, content_type?: string) => Promise<ProposalsResponse>;
  approveProposals: (store_id: string, proposal_ids: string[]) => Promise<{ approved?: number }>;
  rejectProposals: (store_id: string, proposal_ids: string[]) => Promise<{ rejected?: number }>;
  applyProposals: (store_id: string, item_id?: number, proposals?: IntegrationProposal[]) => Promise<ApplyResponse>;
  listRollbacks: (store_id: string, content_type?: string) => Promise<RollbacksResponse>;
  rollbackDirect: (store_id: string, record: IntegrationRollback) => Promise<{ rolled_back?: number; message?: string }>;
}

export function useIntegrationSeo(platformApi: IntegrationApi, storagePrefix: string) {
  const [connection, setConnection] = useState<IntegrationConnection>({ connected: false, store_id: "" });

  const [products, setProducts] = useState<IntegrationProduct[]>([]);
  const [categories, setCategories] = useState<IntegrationCategory[]>([]);

  const [selectedProduct, setSelectedProduct] = useState<IntegrationProduct | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<IntegrationCategory | null>(null);

  const [analysis, setAnalysis] = useState<IntegrationSEOAnalysis | null>(null);
  const [proposals, setProposals] = useState<IntegrationProposal[]>([]);
  const [rollbacks, setRollbacks] = useState<IntegrationRollback[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = useCallback((message: string, type: ToastData["type"] = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // ==================== CONEXÃO ====================

  const setConnectionFromStore = useCallback((storeId: string, storeName?: string) => {
    setConnection({ connected: true, store_id: storeId, store_name: storeName });
  }, []);

  const disconnect = useCallback(() => {
    setConnection({ connected: false, store_id: "" });
    setProducts([]);
    setCategories([]);
    setSelectedProduct(null);
    setSelectedCategory(null);
    setAnalysis(null);
    setProposals([]);
    setRollbacks([]);
    showToast("Desconectado da loja", "info");
  }, [showToast]);

  // ==================== PRODUTOS ====================

  const fetchProducts = useCallback(async () => {
    if (!connection.connected) return;
    setLoading(true);
    try {
      const data = await platformApi.products(connection.store_id);
      setProducts(data.products || []);
      showToast(`${data.total || 0} produto(s) carregado(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar produtos", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const selectProduct = useCallback(async (product: IntegrationProduct) => {
    setSelectedProduct(product);
    setSelectedCategory(null);
    setAnalysis(null);
    // Não filtra `proposals` aqui: o estado guarda o agregado de TODOS os
    // produtos/categorias (a UI já filtra pelo item selecionado em
    // IntegrationAnalise.tsx via `filteredProposals`). Filtrar aqui descartava
    // propostas aprovadas de outros itens a cada troca de seleção.

    setLoading(true);
    try {
      const data = await platformApi.analyzeProduct(connection.store_id, product.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar produto", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const generateProductProposals = useCallback(async (
    product_id: number,
    options?: { target_keyword?: string; recommended_actions?: string[] }
  ) => {
    if (!connection.connected) return [];
    setLoading(true);
    try {
      const data = await platformApi.optimizeProduct(connection.store_id, product_id, options);
      const newProposals = (data.proposals || []).map((p: IntegrationProposal) => ({
        ...p,
        content_type: "product" as const,
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === product_id && p.content_type === "product")), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  // ==================== CATEGORIAS ====================

  const fetchCategories = useCallback(async () => {
    if (!connection.connected) return;
    setLoading(true);
    try {
      const data = await platformApi.categories(connection.store_id);
      setCategories(data.categories || []);
      showToast(`${data.total || 0} categoria(s) carregada(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar categorias", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const selectCategory = useCallback(async (category: IntegrationCategory) => {
    setSelectedCategory(category);
    setSelectedProduct(null);
    setAnalysis(null);
    // Ver comentário em selectProduct: não filtra `proposals` aqui.

    setLoading(true);
    try {
      const data = await platformApi.analyzeCategory(connection.store_id, category.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar categoria", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const generateCategoryProposals = useCallback(async (category_id: number, target_keyword?: string) => {
    if (!connection.connected) return [];
    setLoading(true);
    try {
      const data = await platformApi.optimizeCategory(connection.store_id, category_id, target_keyword);
      const newProposals = (data.proposals || []).map((p: IntegrationProposal) => ({
        ...p,
        content_type: "category" as const,
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === category_id && p.content_type === "category")), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  // ==================== ROLLBACKS (persistência local, padrão Nuvemshop) ====================

  const rollbackStorageKey = useCallback(
    (store_id: string) => `${storagePrefix}_rollbacks_${store_id}`,
    [storagePrefix]
  );

  const persistRollbacks = useCallback((store_id: string, items: IntegrationRollback[]) => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(rollbackStorageKey(store_id), JSON.stringify(items));
      }
    } catch (e) {
      console.warn("Falha ao salvar rollbacks localmente", e);
    }
  }, [rollbackStorageKey]);

  const loadPersistedRollbacks = useCallback((store_id: string): IntegrationRollback[] => {
    try {
      if (typeof window === "undefined") return [];
      const raw = window.localStorage.getItem(rollbackStorageKey(store_id));
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }, [rollbackStorageKey]);

  useEffect(() => {
    if (connection.connected && connection.store_id) {
      const persisted = loadPersistedRollbacks(connection.store_id).filter(r => !r.rolled_back);
      if (persisted.length > 0) setRollbacks(persisted);
    }
  }, [connection.connected, connection.store_id, loadPersistedRollbacks]);

  const fetchRollbacks = useCallback(async (content_type?: string) => {
    if (!connection.connected) return;
    const store_id = connection.store_id;
    const local = loadPersistedRollbacks(store_id).filter(r => !r.rolled_back);
    try {
      const data = await platformApi.listRollbacks(store_id, content_type);
      const backend: IntegrationRollback[] = (data.records || data.rollback_records || []) as IntegrationRollback[];
      const map = new Map<string, IntegrationRollback>();
      for (const r of local) map.set(r.id, r);
      for (const r of backend) map.set(r.id, r);
      const merged = Array.from(map.values()).filter(r => !r.rolled_back);
      setRollbacks(merged);
      persistRollbacks(store_id, merged);
    } catch (error) {
      console.error("Erro ao carregar rollbacks:", error);
      setRollbacks(local);
    }
  }, [connection, platformApi, loadPersistedRollbacks, persistRollbacks]);

  // ==================== PROPOSTAS ====================

  const approveProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    setLoading(true);
    try {
      const data = await platformApi.approveProposals(connection.store_id, proposal_ids);
      setProposals(prev => prev.map(p =>
        proposal_ids.includes(p.id) ? { ...p, status: "approved" as const } : p
      ));
      showToast(`${data.approved || 0} proposta(s) aprovada(s)`, "success");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao aprovar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const rejectProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    setLoading(true);
    try {
      const data = await platformApi.rejectProposals(connection.store_id, proposal_ids);
      setProposals(prev => prev.filter(p => !proposal_ids.includes(p.id)));
      showToast(`${data.rejected || 0} proposta(s) rejeitada(s)`, "success");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao rejeitar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast]);

  const applyProposals = useCallback(async (item_id?: number) => {
    if (!connection.connected) return false;
    setLoading(true);
    try {
      // Envia as aprovadas no body (stateless — sobrevive a cold starts do backend)
      const approved = proposals.filter(p => p.status === "approved");
      const data = await platformApi.applyProposals(connection.store_id, item_id, approved);
      if (data.errors?.length) {
        showToast(`Aplicadas ${data.applied || 0}; erro(s): ${data.errors.join("; ")}`, "warning");
      } else {
        showToast(`${data.applied || 0} otimização(ões) aplicada(s)!`, "success");
      }
      setProposals(prev => prev.map(p =>
        p.status === "approved" ? { ...p, status: "applied" as const } : p
      ));
      const returned: IntegrationRollback[] = (data.rollback_records || []) as IntegrationRollback[];
      if (returned.length > 0) {
        setRollbacks(prev => {
          const map = new Map<string, IntegrationRollback>();
          for (const r of prev) map.set(r.id, r);
          for (const r of returned) map.set(r.id, r);
          const merged = Array.from(map.values()).filter(r => !r.rolled_back);
          persistRollbacks(connection.store_id, merged);
          return merged;
        });
      } else {
        await fetchRollbacks();
      }
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao aplicar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, showToast, fetchRollbacks, proposals, persistRollbacks]);

  // ==================== ROLLBACK ====================

  const rollback = useCallback(async (type: "single" | "all", record?: IntegrationRollback) => {
    if (!connection.connected) return false;
    setLoading(true);
    try {
      if (type === "single") {
        if (!record) {
          showToast("Registro de rollback não informado", "error");
          return false;
        }
        await platformApi.rollbackDirect(connection.store_id, record);
        setRollbacks(prev => {
          const next = prev.filter(r => r.id !== record.id);
          persistRollbacks(connection.store_id, next);
          return next;
        });
        showToast("Alteração revertida com sucesso!", "success");
      } else {
        const current = rollbacks.slice();
        let reverted = 0;
        const errors: string[] = [];
        for (const r of current) {
          try {
            await platformApi.rollbackDirect(connection.store_id, r);
            reverted += 1;
          } catch (e) {
            errors.push(`${r.field_name}: ${e instanceof Error ? e.message : String(e)}`);
          }
        }
        setRollbacks(prev => {
          const remaining = prev.filter(r => !current.some(c => c.id === r.id));
          persistRollbacks(connection.store_id, remaining);
          return remaining;
        });
        if (errors.length) {
          showToast(`${reverted} revertida(s), ${errors.length} erro(s)`, "warning");
        } else {
          showToast(`${reverted} alteração(ões) revertida(s)`, "success");
        }
      }
      setProposals(prev => prev.filter(p => p.status !== "applied"));
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao executar rollback", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, platformApi, rollbacks, showToast, persistRollbacks]);

  const clearSelection = useCallback(() => {
    setSelectedProduct(null);
    setSelectedCategory(null);
    setAnalysis(null);
  }, []);

  return {
    connection,
    products,
    categories,
    selectedProduct,
    selectedCategory,
    analysis,
    proposals,
    rollbacks,
    loading,
    toast,
    setConnectionFromStore,
    disconnect,
    fetchProducts,
    selectProduct,
    generateProductProposals,
    fetchCategories,
    selectCategory,
    generateCategoryProposals,
    approveProposals,
    rejectProposals,
    applyProposals,
    fetchRollbacks,
    rollback,
    clearSelection,
    showToast,
  };
}
