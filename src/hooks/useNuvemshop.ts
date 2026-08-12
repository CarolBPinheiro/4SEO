import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/apiClient";

export interface NuvemshopProduct {
  id: number;
  name: string;
  handle: string;
  description?: string;
  seo_title?: string;
  seo_description?: string;
  url?: string;
  images?: Array<{ id: number; src: string; alt?: string }>;
  variants?: Array<Record<string, unknown>>;
  categories?: Array<{ id: number; name: string }>;
  tags?: string;
  brand?: string;
}

export interface NuvemshopCategory {
  id: number;
  name: string;
  handle: string;
  description?: string;
  seo_title?: string;
  seo_description?: string;
  url?: string;
  parent_id?: number;
  subcategories?: number[];
  products_count?: number;
}

export interface NuvemshopPage {
  id: number;
  title: string;
  handle: string;
  content?: string;
  seo_title?: string;
  seo_description?: string;
  url?: string;
  published: boolean;
}

export interface NuvemshopBlogPost {
  id: number;
  blog_id?: number;
  title: string;
  handle: string;
  body?: string;
  seo_title?: string;
  seo_description?: string;
  url?: string;
  author?: string;
  tags?: string;
  published: boolean;
  published_at?: string;
}

export interface NuvemshopProposal {
  id: string;
  product_id: number;
  field_name: string;
  original_value: string;
  proposed_value: string;
  reasoning: string;
  status: "pending" | "approved" | "applied" | "rejected" | "rolled_back";
  created_at: string;
  optimization_type?: string;
  content_type?: "product" | "category" | "page" | "blog";
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

export interface NuvemshopRollback {
  id: string;
  shop_url?: string;
  product_id: number;
  field_name: string;
  original_value: string | null;
  new_value: string;
  applied_at: string;
  rolled_back: boolean;
  rolled_back_at?: string | null;
  blog_id?: number | null;
  content_type?: "product" | "category" | "page" | "blog";
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
  type?: "product" | "category" | "page" | "blog";
  images_without_alt?: number;
}

export interface NuvemshopConnection {
  connected: boolean;
  store_id: string;
  store_name?: string;
  store_url?: string;
  access_token?: string;
}

export interface ToastData {
  message: string;
  type: "info" | "success" | "error" | "warning";
}

export type ContentType = "products" | "categories" | "pages" | "blog";

export function useNuvemshop() {
  const [connection, setConnection] = useState<NuvemshopConnection>({
    connected: false,
    store_id: "",
  });
  
  // Estados para diferentes tipos de conteúdo
  const [products, setProducts] = useState<NuvemshopProduct[]>([]);
  const [categories, setCategories] = useState<NuvemshopCategory[]>([]);
  const [pages, setPages] = useState<NuvemshopPage[]>([]);
  const [blogPosts, setBlogPosts] = useState<NuvemshopBlogPost[]>([]);
  const [blogMessage, setBlogMessage] = useState<string | null>(null);
  
  // Item selecionado
  const [selectedProduct, setSelectedProduct] = useState<NuvemshopProduct | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<NuvemshopCategory | null>(null);
  const [selectedPage, setSelectedPage] = useState<NuvemshopPage | null>(null);
  const [selectedBlogPost, setSelectedBlogPost] = useState<NuvemshopBlogPost | null>(null);
  
  const [analysis, setAnalysis] = useState<SEOAnalysis | null>(null);
  const [proposals, setProposals] = useState<NuvemshopProposal[]>([]);
  const [rollbacks, setRollbacks] = useState<NuvemshopRollback[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = useCallback((message: string, type: ToastData["type"] = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // ==================== OAUTH ====================

  const getAuthUrl = useCallback(async (redirectUri?: string) => {
    try {
      const data = await api.nuvemshop.getAuthUrl(redirectUri);
      return data;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar URL de autorização", "error");
      return null;
    }
  }, [showToast]);

  const handleOAuthCallback = useCallback(async (code: string, state: string) => {
    setLoading(true);
    try {
      const data = await api.nuvemshop.oauthCallback(code, state);
      if (data.success) {
        setConnection({
          connected: true,
          store_id: data.store_id,
          store_name: data.store?.name,
          store_url: data.store?.url,
        });
        showToast(`Conectado à loja ${data.store?.name || data.store_id}`, "success");
        return true;
      } else {
        showToast(data.error || "Falha na autenticação OAuth", "error");
        return false;
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao processar callback", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // Troca manual de código (quando Nuvemshop mostra curl ao invés de redirecionar)
  const exchangeCodeManually = useCallback(async (code: string) => {
    setLoading(true);
    try {
      const data = await api.nuvemshop.exchangeCode(code);
      if (data.success) {
        setConnection({
          connected: true,
          store_id: data.store_id,
          store_name: data.store?.name,
          store_url: data.store?.url,
        });
        showToast(`Conectado à loja ${data.store?.name || data.store_id}`, "success");
        return true;
      } else {
        showToast(data.error || "Falha na troca do código", "error");
        return false;
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao trocar código", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // Conexão direta com token (quando já tem access_token e store_id do curl)
  const connectWithToken = useCallback(async (accessToken: string, storeId: string) => {
    setLoading(true);
    try {
      const data = await api.nuvemshop.connectWithToken(accessToken, storeId);
      if (data.success) {
        setConnection({
          connected: true,
          store_id: data.store_id,
          store_name: data.store?.name,
          store_url: data.store?.url,
        });
        showToast(`Conectado à loja ${data.store?.name || data.store_id}`, "success");
        return true;
      } else {
        showToast(data.error || "Falha na conexão", "error");
        return false;
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao conectar", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // Definir conexão após OAuth automático (quando backend já trocou o token)
  const setConnectionFromOAuth = useCallback((storeId: string, storeName?: string) => {
    setConnection({
      connected: true,
      store_id: storeId,
      store_name: storeName,
    });
    showToast(`Conectado à loja ${storeName || storeId}`, "success");
  }, [showToast]);

  // Desconectar
  const disconnect = useCallback(() => {
    setConnection({ connected: false, store_id: "" });
    setProducts([]);
    setCategories([]);
    setPages([]);
    setBlogPosts([]);
    setSelectedProduct(null);
    setSelectedCategory(null);
    setSelectedPage(null);
    setSelectedBlogPost(null);
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
      const data = await api.nuvemshop.products(connection.store_id);
      setProducts(data.products || []);
      showToast(`${data.total || 0} produto(s) carregado(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar produtos", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectProduct = useCallback(async (product: NuvemshopProduct) => {
    setSelectedProduct(product);
    setSelectedCategory(null);
    setSelectedPage(null);
    setSelectedBlogPost(null);
    setAnalysis(null);
    // Não filtra `proposals` aqui: o estado guarda o agregado de TODOS os
    // itens (produto/categoria/página/post) — a UI já filtra pelo item
    // selecionado via `filteredProposals` (NuvemshopAnalise.tsx). Filtrar
    // aqui descartava propostas aprovadas de outros itens a cada troca de
    // seleção (mesma causa raiz tratada em useIntegrationSeo.ts).

    setLoading(true);
    try {
      const data = await api.nuvemshop.analyzeProduct(connection.store_id, product.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar produto", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generateProductProposals = useCallback(async (
    product_id: number,
    options?: { target_keyword?: string; recommended_actions?: string[] }
  ) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.optimizeProduct(connection.store_id, product_id, options);
      const newProposals = (data.proposals || []).map((p: NuvemshopProposal) => ({
        ...p,
        content_type: 'product' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === product_id && p.content_type === 'product')), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== CATEGORIAS ====================

  const fetchCategories = useCallback(async () => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.categories(connection.store_id);
      setCategories(data.categories || []);
      showToast(`${data.total || 0} categoria(s) carregada(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar categorias", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectCategory = useCallback(async (category: NuvemshopCategory) => {
    setSelectedCategory(category);
    setSelectedProduct(null);
    setSelectedPage(null);
    setSelectedBlogPost(null);
    setAnalysis(null);
    // Ver comentário em selectProduct: não filtra `proposals` aqui.

    setLoading(true);
    try {
      const data = await api.nuvemshop.analyzeCategory(connection.store_id, category.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar categoria", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generateCategoryProposals = useCallback(async (category_id: number, target_keyword?: string) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.optimizeCategory(connection.store_id, category_id, target_keyword);
      const newProposals = (data.proposals || []).map((p: NuvemshopProposal) => ({
        ...p,
        content_type: 'category' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === category_id && p.content_type === 'category')), ...newProposals]);
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
      const data = await api.nuvemshop.pages(connection.store_id);
      setPages(data.pages || []);
      showToast(`${data.total || 0} página(s) carregada(s)`, "success");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar páginas", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectPage = useCallback(async (page: NuvemshopPage) => {
    setSelectedPage(page);
    setSelectedProduct(null);
    setSelectedCategory(null);
    setSelectedBlogPost(null);
    setAnalysis(null);
    // Ver comentário em selectProduct: não filtra `proposals` aqui.

    setLoading(true);
    try {
      const data = await api.nuvemshop.analyzePage(connection.store_id, page.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar página", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generatePageProposals = useCallback(async (page_id: number, target_keyword?: string) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.optimizePage(connection.store_id, page_id, target_keyword);
      const newProposals = (data.proposals || []).map((p: NuvemshopProposal) => ({
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

  // ==================== BLOG ====================

  const fetchBlogPosts = useCallback(async () => {
    if (!connection.connected) return;
    
    setLoading(true);
    setBlogMessage(null);
    try {
      const data = await api.nuvemshop.blogPosts(connection.store_id);
      setBlogPosts(data.posts || []);
      if (data.blog_enabled === false && data.message) {
        setBlogMessage(data.message);
        showToast(data.message, "info");
      } else {
        showToast(`${data.total || 0} post(s) carregado(s)`, "success");
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar posts", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const selectBlogPost = useCallback(async (post: NuvemshopBlogPost) => {
    setSelectedBlogPost(post);
    setSelectedProduct(null);
    setSelectedCategory(null);
    setSelectedPage(null);
    setAnalysis(null);
    // Ver comentário em selectProduct: não filtra `proposals` aqui.

    if (!post.blog_id) {
      showToast("Erro: post sem blog_id", "error");
      return;
    }
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.analyzeBlogPost(connection.store_id, post.blog_id, post.id);
      setAnalysis(data);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao analisar post", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const generateBlogProposals = useCallback(async (blog_id: number, post_id: number, target_keyword?: string) => {
    if (!connection.connected) return [];
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.optimizeBlogPost(connection.store_id, blog_id, post_id, target_keyword);
      const newProposals = (data.proposals || []).map((p: NuvemshopProposal) => ({
        ...p,
        content_type: 'blog' as const
      }));
      setProposals(prev => [...prev.filter(p => !(p.product_id === post_id && p.content_type === 'blog')), ...newProposals]);
      showToast(`${newProposals.length} proposta(s) gerada(s)`, "success");
      return newProposals;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao gerar propostas", "error");
      return [];
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  // ==================== PROPOSTAS ====================

  // Chave de localStorage para persistir rollbacks
  const rollbackStorageKey = useCallback(
    (store_id: string) => `nuvemshop_rollbacks_${store_id}`,
    []
  );

  const persistRollbacks = useCallback((store_id: string, items: NuvemshopRollback[]) => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(rollbackStorageKey(store_id), JSON.stringify(items));
      }
    } catch (e) {
      console.warn("Falha ao salvar rollbacks localmente", e);
    }
  }, [rollbackStorageKey]);

  const loadPersistedRollbacks = useCallback((store_id: string): NuvemshopRollback[] => {
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

  // Carregar rollbacks persistidos quando conectar
  useEffect(() => {
    if (connection.connected && connection.store_id) {
      const persisted = loadPersistedRollbacks(connection.store_id).filter(r => !r.rolled_back);
      if (persisted.length > 0) {
        setRollbacks(persisted);
      }
    }
  }, [connection.connected, connection.store_id, loadPersistedRollbacks]);

  // Carregar rollbacks (merge backend + localStorage)
  const fetchRollbacks = useCallback(async (content_type?: string) => {
    if (!connection.connected) return;
    const store_id = connection.store_id;
    const local = loadPersistedRollbacks(store_id).filter(r => !r.rolled_back);
    
    try {
      const data = await api.nuvemshop.listRollbacks(store_id, content_type);
      const backend: NuvemshopRollback[] = (data.records || data.rollback_records || []) as NuvemshopRollback[];
      const map = new Map<string, NuvemshopRollback>();
      for (const r of local) map.set(r.id, r);
      for (const r of backend) map.set(r.id, r);
      const merged = Array.from(map.values()).filter(r => !r.rolled_back);
      setRollbacks(merged);
      persistRollbacks(store_id, merged);
    } catch (error) {
      console.error("Erro ao carregar rollbacks:", error);
      setRollbacks(local);
    }
  }, [connection, loadPersistedRollbacks, persistRollbacks]);

  const fetchProposals = useCallback(async (status?: string, content_type?: string) => {
    if (!connection.connected) return;
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.listProposals(connection.store_id, status, content_type);
      setProposals(data.proposals || []);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao carregar propostas", "error");
    } finally {
      setLoading(false);
    }
  }, [connection, showToast]);

  const approveProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.approveProposals(connection.store_id, proposal_ids);
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

  const rejectProposals = useCallback(async (proposal_ids: string[]) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      const data = await api.nuvemshop.rejectProposals(connection.store_id, proposal_ids);
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

  const applyProposals = useCallback(async (item_id?: number) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      // Send approved proposals in body so backend doesn't depend on in-memory state
      const approved = proposals.filter(p => p.status === "approved");
      const data = await api.nuvemshop.applyProposals(connection.store_id, item_id, approved);
      setProposals(prev => prev.map(p => 
        p.status === "approved" ? { ...p, status: "applied" as const } : p
      ));
      const returned: NuvemshopRollback[] = (data.rollback_records || []) as NuvemshopRollback[];
      if (returned.length > 0) {
        setRollbacks(prev => {
          const map = new Map<string, NuvemshopRollback>();
          for (const r of prev) map.set(r.id, r);
          for (const r of returned) map.set(r.id, r);
          const merged = Array.from(map.values()).filter(r => !r.rolled_back);
          persistRollbacks(connection.store_id, merged);
          return merged;
        });
      } else {
        await fetchRollbacks();
      }
      showToast(`${data.applied || 0} otimização(ões) aplicada(s) à Nuvemshop!`, "success");
      return true;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Erro ao aplicar propostas", "error");
      return false;
    } finally {
      setLoading(false);
    }
  }, [connection, showToast, fetchRollbacks, proposals, persistRollbacks]);

  // ==================== ROLLBACK ====================

  const rollback = useCallback(async (type: "single" | "all", record?: NuvemshopRollback) => {
    if (!connection.connected) return false;
    
    setLoading(true);
    try {
      if (type === "single") {
        if (!record) {
          showToast("Registro de rollback não informado", "error");
          return false;
        }
        await api.nuvemshop.rollbackDirect(connection.store_id, record);
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
            await api.nuvemshop.rollbackDirect(connection.store_id, r);
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
  }, [connection, rollbacks, showToast, persistRollbacks]);

  // Limpar seleção
  const clearSelection = useCallback(() => {
    setSelectedProduct(null);
    setSelectedCategory(null);
    setSelectedPage(null);
    setSelectedBlogPost(null);
    setAnalysis(null);
  }, []);

  return {
    // Estado
    connection,
    products,
    categories,
    pages,
    blogPosts,
    blogMessage,
    selectedProduct,
    selectedCategory,
    selectedPage,
    selectedBlogPost,
    analysis,
    proposals,
    rollbacks,
    loading,
    toast,
    
    // OAuth
    getAuthUrl,
    handleOAuthCallback,
    exchangeCodeManually,
    connectWithToken,
    setConnectionFromOAuth,
    
    // Conexão
    disconnect,
    
    // Produtos
    fetchProducts,
    selectProduct,
    generateProductProposals,
    
    // Categorias
    fetchCategories,
    selectCategory,
    generateCategoryProposals,
    
    // Páginas
    fetchPages,
    selectPage,
    generatePageProposals,
    
    // Blog
    fetchBlogPosts,
    selectBlogPost,
    generateBlogProposals,
    
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
