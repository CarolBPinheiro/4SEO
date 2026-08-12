import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/apiClient";

export interface ShopifyProduct {
  id: number;
  title: string;
  handle: string;
  body_html?: string;
  vendor?: string;
  product_type?: string;
  images?: Array<{ id: number; src: string; alt?: string }>;
  metafields?: {
    title_tag?: string;
    description_tag?: string;
  };
}

export interface ShopifyCollection {
  id: number;
  title: string;
  handle: string;
  body_html?: string;
  url?: string;
  image?: { src: string; alt?: string };
  collection_type: "custom" | "smart";
  products_count?: number;
}

export interface ShopifyPage {
  id: number;
  title: string;
  handle: string;
  body_html?: string;
  url?: string;
  published: boolean;
}

export interface ShopifyBlog {
  id: number;
  title: string;
  handle: string;
}

export interface ShopifyArticle {
  id: number;
  blog_id: number;
  title: string;
  handle: string;
  body_html?: string;
  author?: string;
  tags?: string;
  url?: string;
  image?: { src: string; alt?: string };
  published: boolean;
}

export interface ShopifyProposal {
  id: string;
  product_id: number;
  field: string;
  original_value: string;
  proposed_value: string;
  reasoning: string;
  status: "pending" | "approved" | "applied" | "rejected" | "rolled_back";
  created_at: string;
  optimization_type?: string;
  content_type?: "product" | "collection" | "page" | "article";
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

export interface ShopifyRollback {
  id: string;
  shop_url?: string;
  product_id: number;
  field_name: string;
  original_value: string | null;
  new_value: string;
  applied_at: string;
  rolled_back: boolean;
  rolled_back_at?: string | null;
  image_id?: number | null;
  blog_id?: number | null;
  content_type?: "product" | "collection" | "page" | "article";
  optimization_type?: string;
}

export interface SEOAnalysis {
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
  type?: "product" | "collection" | "page" | "article";
  images_without_alt?: number | unknown[];
}

export interface ProductAnalysis extends SEOAnalysis {
  product: ShopifyProduct;
  images_without_alt: number | unknown[];
  seo_features?: {
    has_semantic_structure: boolean;
    has_faq: boolean;
    has_schema: boolean;
    tags_count: number;
  };
}

export interface ShopifyConnection {
  connected: boolean;
  shop_url: string;
  shop_name?: string;
  access_token?: string;
}

export interface ToastData {
  message: string;
  type: "info" | "success" | "error" | "warning";
}

// Tipo para itens genéricos (produto, coleção, página ou artigo)
export type ShopifyItem = ShopifyProduct | ShopifyCollection | ShopifyPage | ShopifyArticle;
export type ContentType = "products" | "collections" | "pages" | "articles";

export function useShopify() {
  const [connection, setConnection] = useState<ShopifyConnection>({
    connected: false,
    shop_url: "",
  });
  
  // Estados para diferentes tipos de conteúdo
  const [products, setProducts] = useState<ShopifyProduct[]>([]);
  const [collections, setCollections] = useState<ShopifyCollection[]>([]);
  const [pages, setPages] = useState<ShopifyPage[]>([]);
  const [blogs, setBlogs] = useState<ShopifyBlog[]>([]);
  const [articles, setArticles] = useState<ShopifyArticle[]>([]);
  
  // Item selecionado (genérico)
  const [selectedProduct, setSelectedProduct] = useState<ShopifyProduct | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<ShopifyCollection | null>(null);
  const [selectedPage, setSelectedPage] = useState<ShopifyPage | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<ShopifyArticle | null>(null);
  
  const [analysis, setAnalysis] = useState<SEOAnalysis | null>(null);
  const [proposals, setProposals] = useState<ShopifyProposal[]>([]);
  const [rollbacks, setRollbacks] = useState<ShopifyRollback[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = useCallback((message: string, type: ToastData["type"] = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // Conectar à loja Shopify
  const connect = useCallback(async (shop_url: string, access_token: string) => {
    setLoading(true);
    try {
      const data = await api.shopify.connect(shop_url, access_token);
      if (data.success) {
        setConnection({
          connected: true,
          shop_url,
          shop_name: data.shop?.shop_name,
          access_token,
        });
        showToast(`Conectado à loja ${data.shop?.shop_name || shop_url}`, "success");
        return true;
      } else {
        showToast(data.error || "Falha ao conectar", "error");
        return false;
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao conectar à loja", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // Desconectar
  const disconnect = useCallback(() => {
    setConnection({ connected: false, shop_url: "" });
    setProducts([]);
    setCollections([]);
    setPages([]);
    setBlogs([]);
    setArticles([]);
    setSelectedProduct(null);
    setSelectedCollection(null);
    setSelectedPage(null);
    setSelectedArticle(null);
    setAnalysis(null);
    setProposals([]);
    setRollbacks([]);
    showToast("Desconectado da loja", "info");
  }, [showToast]);

  // Inicializar conexão a partir do StoreContext (backend já tem o token cacheado)
  const initFromStore = useCallback((shop_url: string, shop_name?: string) => {
    if (connection.connected && connection.shop_url === shop_url) return;
    setConnection({
      connected: true,
      shop_url,
      shop_name,
    });
  }, [connection]);

  // ==================== PRODUTOS ====================

  // Carregar produtos
  const fetchProducts = useCallback(async () => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.shopify.products(connection.shop_url);
      setProducts(data.products || []);
      showToast(`${data.total || 0} produto(s) carregado(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar produtos", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== COLEÇÕES ====================

  const fetchCollections = useCallback(async () => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.shopify.collections(connection.shop_url);
      setCollections(data.collections || []);
      showToast(`${data.total || 0} coleção(ões) carregada(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar coleções", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectCollection = useCallback(async (collection: ShopifyCollection) => {
    setSelectedCollection(collection);
    setAnalysis(null);
    // Não filtra `proposals` aqui: o estado guarda o agregado de TODOS os
    // itens (produto/coleção/página/artigo) — a UI já filtra pelo item
    // selecionado via `filteredProposals` (ShopifyAnalise.tsx). Filtrar aqui
    // descartava propostas aprovadas de outros itens a cada troca de seleção
    // (mesma causa raiz tratada em useIntegrationSeo.ts).

    setLoading(true);
    try {
      const data = await api.shopify.analyzeCollection(
        connection.shop_url, 
        collection.id, 
        collection.collection_type
      );
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar coleção", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generateCollectionProposals = useCallback(async (collection_id: number, collection_type: string) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.shopify.optimizeCollection(connection.shop_url, collection_id, collection_type);
      const newProposals = (data.proposals || []).map((p: ShopifyProposal) => ({
        ...p,
        content_type: 'collection' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === collection_id && p.content_type === 'collection')), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== PÁGINAS ====================

  const fetchPages = useCallback(async () => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.shopify.pages(connection.shop_url);
      setPages(data.pages || []);
      showToast(`${data.total || 0} página(s) carregada(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar páginas", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectPage = useCallback(async (page: ShopifyPage) => {
    setSelectedPage(page);
    setAnalysis(null);
    // Ver comentário em selectCollection: não filtra `proposals` aqui.

    setLoading(true);
    try {
      const data = await api.shopify.analyzePage(connection.shop_url, page.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar página", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generatePageProposals = useCallback(async (page_id: number) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.shopify.optimizePage(connection.shop_url, page_id);
      const newProposals = (data.proposals || []).map((p: ShopifyProposal) => ({
        ...p,
        content_type: 'page' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === page_id && p.content_type === 'page')), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== BLOG E ARTIGOS ====================

  const fetchBlogs = useCallback(async () => {
    if (!connection.connected) return;
    
    try {
      const data = await api.shopify.blogs(connection.shop_url);
      setBlogs(data.blogs || []);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar blogs", "error");
    }
  }, [connection, showToast]);

  const fetchArticles = useCallback(async (blog_id?: number) => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.shopify.articles(connection.shop_url, blog_id);
      setArticles(data.articles || []);
      showToast(`${data.total || 0} artigo(s) carregado(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar artigos", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectArticle = useCallback(async (article: ShopifyArticle) => {
    setSelectedArticle(article);
    setAnalysis(null);
    // Ver comentário em selectCollection: não filtra `proposals` aqui.

    setLoading(true);
    try {
      const data = await api.shopify.analyzeArticle(connection.shop_url, article.blog_id, article.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar artigo", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generateArticleProposals = useCallback(async (blog_id: number, article_id: number) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.shopify.optimizeArticle(connection.shop_url, blog_id, article_id);
      const newProposals = (data.proposals || []).map((p: ShopifyProposal) => ({
        ...p,
        content_type: 'article' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === article_id && p.content_type === 'article')), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== ANÁLISE DE PRODUTOS ====================

  // Analisar produto
  const analyzeProduct = useCallback(async (product_id: number) => {
    if (!connection.connected) return null;
    
    setLoading(true);
    try {
      const data = await api.shopify.analyzeProduct(connection.shop_url, product_id);
      setAnalysis(data);
      return data;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar produto", "error");
      return null;
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // Gerar propostas de otimização
  const generateProposals = useCallback(async (product_id: number, options?: {
    optimize_title?: boolean;
    optimize_description?: boolean;
    optimize_seo_title?: boolean;
    optimize_seo_description?: boolean;
    optimize_image_alts?: boolean;
    generate_faq?: boolean;
    generate_rich_description?: boolean;
    generate_tags?: boolean;
    target_keyword?: string;
    recommended_actions?: string[];
  }) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.shopify.optimizeProduct(connection.shop_url, product_id, options);
      const newProposals = (data.proposals || []).map((p: ShopifyProposal) => ({
        ...p,
        content_type: 'product' as const
      }));
      setProposals(prev => {
        // Remover propostas antigas do mesmo produto e adicionar novas
        const filtered = prev.filter(p => !(p.product_id === product_id && p.content_type === 'product'));
        return [...filtered, ...newProposals];
      });
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // Carregar propostas existentes
  const fetchProposals = useCallback(async (status?: string, product_id?: number) => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.shopify.listProposals(connection.shop_url, status, product_id);
      setProposals(data.proposals || []);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar propostas", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // Aprovar propostas
  const approveProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      const data = await api.shopify.approveProposals(connection.shop_url, proposal_ids);
      // Atualizar status local
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
  }, [connection, showToast]);

  // Rejeitar propostas
  const rejectProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      const data = await api.shopify.rejectProposals(connection.shop_url, proposal_ids);
      // Remover da lista local
      setProposals(prev => prev.filter(p => !proposal_ids.includes(p.id)));
      showToast(`${data.rejected || 0} proposta(s) rejeitada(s)`, "success");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao rejeitar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // Chave de localStorage para persistir rollbacks (sobrevive a cold starts do backend)
  const rollbackStorageKey = useCallback(
    (shop_url: string) => `shopify_rollbacks_${shop_url}`,
    []
  );

  const persistRollbacks = useCallback((shop_url: string, items: ShopifyRollback[]) => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(rollbackStorageKey(shop_url), JSON.stringify(items));
      }
    } catch (e) {
      console.warn("Falha ao salvar rollbacks localmente", e);
    }
  }, [rollbackStorageKey]);

  const loadPersistedRollbacks = useCallback((shop_url: string): ShopifyRollback[] => {
    try {
      if (typeof window === "undefined") return [];
      const raw = window.localStorage.getItem(rollbackStorageKey(shop_url));
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }, [rollbackStorageKey]);

  // Carregar rollbacks persistidos quando conectar
  useEffect(() => {
    if (connection.connected && connection.shop_url) {
      const persisted = loadPersistedRollbacks(connection.shop_url).filter(r => !r.rolled_back);
      if (persisted.length > 0) {
        setRollbacks(persisted);
      }
    }
  }, [connection.connected, connection.shop_url, loadPersistedRollbacks]);

  // Carregar rollbacks (merge backend + localStorage)
  const fetchRollbacks = useCallback(async (product_id?: number) => {
    if (!connection.connected) return;
    const shop_url = connection.shop_url;
    const local = loadPersistedRollbacks(shop_url).filter(r => !r.rolled_back);
    
    try {
      const data = await api.shopify.listRollbacks(shop_url, product_id);
      const backend: ShopifyRollback[] = (data.rollback_records || data.records || []) as ShopifyRollback[];
      // Merge by id, prefer backend version when duplicated
      const map = new Map<string, ShopifyRollback>();
      for (const r of local) map.set(r.id, r);
      for (const r of backend) map.set(r.id, r);
      const merged = Array.from(map.values()).filter(r => !r.rolled_back);
      setRollbacks(merged);
      persistRollbacks(shop_url, merged);
    } catch (error) {
      console.error("Erro ao carregar rollbacks:", error);
      // Fallback: usar apenas localStorage
      setRollbacks(local);
    }
  }, [connection, loadPersistedRollbacks, persistRollbacks]);

  // Aplicar propostas aprovadas
  const applyProposals = useCallback(async (product_id?: number, proposals?: any[]) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      const data = await api.shopify.applyProposals(connection.shop_url, product_id, proposals);
      // Atualizar status local
      setProposals(prev => prev.map(p => 
        p.status === "approved" ? { ...p, status: "applied" as const } : p
      ));
      // Capturar rollback_records retornados e persistir
      const returned: ShopifyRollback[] = (data.rollback_records || []) as ShopifyRollback[];
      if (returned.length > 0) {
        setRollbacks(prev => {
          const map = new Map<string, ShopifyRollback>();
          for (const r of prev) map.set(r.id, r);
          for (const r of returned) map.set(r.id, r);
          const merged = Array.from(map.values()).filter(r => !r.rolled_back);
          persistRollbacks(connection.shop_url, merged);
          return merged;
        });
      } else {
        // Sem retorno: tenta buscar do backend
        await fetchRollbacks(product_id);
      }
      showToast(`${data.applied || 0} otimização(ões) aplicada(s) ao Shopify!`, "success");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao aplicar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, showToast, fetchRollbacks, persistRollbacks]);

  // Executar rollback - envia o registro completo para o backend (funciona após cold starts)
  const rollback = useCallback(async (
    type: "single" | "all",
    record?: ShopifyRollback
  ) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      if (type === "single") {
        if (!record) {
          showToast("Registro de rollback não informado", "error");
          return false;
        }
        await api.shopify.rollbackDirect(connection.shop_url, record);
        setRollbacks(prev => {
          const next = prev.filter(r => r.id !== record.id);
          persistRollbacks(connection.shop_url, next);
          return next;
        });
        showToast("Alteração revertida com sucesso!", "success");
      } else {
        // All
        const current = rollbacks.slice();
        let reverted = 0;
        const errors: string[] = [];
        for (const r of current) {
          try {
            await api.shopify.rollbackDirect(connection.shop_url, r);
            reverted += 1;
          } catch (e) {
            errors.push(`${r.field_name}: ${e instanceof Error ? e.message : String(e)}`);
          }
        }
        setRollbacks(prev => {
          const remaining = prev.filter(r => !current.some(c => c.id === r.id));
          persistRollbacks(connection.shop_url, remaining);
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
  }, [connection, rollbacks, showToast, persistRollbacks]);

  // Selecionar produto e analisar
  const selectProduct = useCallback(async (product: ShopifyProduct) => {
    setSelectedProduct(product);
    setSelectedCollection(null);
    setSelectedPage(null);
    setSelectedArticle(null);
    setAnalysis(null);
    // Ver comentário em selectCollection: não filtra `proposals` aqui.
    await analyzeProduct(product.id);
  }, [analyzeProduct]);

  // Limpar seleção atual
  const clearSelection = useCallback(() => {
    setSelectedProduct(null);
    setSelectedCollection(null);
    setSelectedPage(null);
    setSelectedArticle(null);
    setAnalysis(null);
  }, []);

  return {
    // Estado
    connection,
    products,
    collections,
    pages,
    blogs,
    articles,
    selectedProduct,
    selectedCollection,
    selectedPage,
    selectedArticle,
    analysis,
    proposals,
    rollbacks,
    loading,
    toast,
    
    // Conexão
    connect,
    disconnect,
    initFromStore,
    
    // Produtos
    fetchProducts,
    selectProduct,
    analyzeProduct,
    generateProposals,
    
    // Coleções
    fetchCollections,
    selectCollection,
    generateCollectionProposals,
    
    // Páginas
    fetchPages,
    selectPage,
    generatePageProposals,
    
    // Blog/Artigos
    fetchBlogs,
    fetchArticles,
    selectArticle,
    generateArticleProposals,
    
    // Propostas
    fetchProposals,
    approveProposals,
    rejectProposals,
    applyProposals,
    
    // Rollback
    fetchRollbacks,
    rollback,
    
    // Utilitários
    clearSelection,
    showToast,
  };
}
