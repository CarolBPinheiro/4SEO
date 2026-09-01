import { supabase } from "@/lib/supabase";
import { clearAdminSession, getAdminToken } from "@/lib/adminSession";
// Tipos das integrações VTEX/Loja Integrada (import type: sem dependência de runtime)
import type {
  ProductsResponse,
  CategoriesResponse,
  ProposalsResponse,
  ApplyResponse,
  RollbacksResponse,
  IntegrationProposal,
  IntegrationRollback,
  IntegrationSEOAnalysis,
} from "@/hooks/useIntegrationSeo";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// Resposta dos endpoints de conexão VTEX/Loja Integrada
interface IntegrationConnectResponse {
  success?: boolean;
  store_id?: string;
  store?: { name?: string; url?: string };
  message?: string;
  detail?: string;
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export function getToken(): string | null {
  return localStorage.getItem("auth_token");
}

export function setToken(token: string | null) {
  if (!token) localStorage.removeItem("auth_token");
  else localStorage.setItem("auth_token", token);
}

/**
 * Retorna um access_token sempre válido. O SDK do Supabase faz refresh
 * automático quando o token está prestes a expirar ou já expirou.
 */
async function getFreshToken(): Promise<string | null> {
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error || !data?.session?.access_token) {
      return getToken();
    }
    const fresh = data.session.access_token;
    if (fresh !== getToken()) setToken(fresh);
    return fresh;
  } catch {
    return getToken();
  }
}

async function request<T>(path: string, method: HttpMethod, body?: any): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = await getFreshToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Se 401, força refresh do Supabase e tenta uma vez mais
  if (res.status === 401) {
    let refreshed: string | null = null;
    try {
      const { data } = await supabase.auth.refreshSession();
      refreshed = data?.session?.access_token ?? null;
    } catch {
      refreshed = null;
    }

    if (refreshed) {
      setToken(refreshed);
      headers["Authorization"] = `Bearer ${refreshed}`;
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    }

    // Se ainda 401 após refresh, sessão está irrecuperável → logout + redirect
    if (res.status === 401) {
      try {
        await supabase.auth.signOut();
      } catch {
        /* ignore */
      }
      setToken(null);
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login?expired=1";
      }
    }
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const detail = data?.detail || data?.message || `Erro HTTP ${res.status}`;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
    const err = new Error(msg) as Error & { status?: number; code?: string };
    err.status = res.status;
    if (res.status === 402 || data?.code === "subscription_required") {
      err.code = "subscription_required";
    }
    throw err;
  }
  return data as T;
}

async function adminRequest<T>(path: string, method: HttpMethod, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAdminToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (res.status === 401) {
    clearAdminSession();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/admin/login")) {
      window.location.href = "/admin/login";
    }
  }

  if (!res.ok) {
    const detail = data?.detail || data?.message || `Erro HTTP ${res.status}`;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
    const err = new Error(msg) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return data as T;
}

export const api = {
  auth: {
    register: (email: string, password: string, company_name?: string) =>
      request<{ token: string; email: string; company_name: string }>("/auth/register", "POST", { email, password, company_name }),
    login: (email: string, password: string) =>
      request<{ token: string; email: string; company_name: string }>("/auth/login", "POST", { email, password }),
    me: () => request<{ email: string; company_name: string }>("/auth/me", "GET"),
    logout: () => setToken(null),
  },

  sites: {
    list: () => request<any[]>("/sites", "GET"),
    create: (base_url: string, platform?: string) => request<any>("/sites", "POST", { base_url, platform }),
    update: (siteId: string, base_url: string, platform?: string) =>
      request<any>(`/sites/${siteId}`, "PUT", { base_url, platform }),
    remove: (siteId: string) => request<any>(`/sites/${siteId}`, "DELETE"),
    scan: (siteId: string) => request<any>(`/site-scan/${siteId}`, "POST"),
    pages: (siteId: string) => request<any[]>(`/site-pages/${siteId}`, "GET"),
    deletePage: (siteId: string, pageId: string) => request<any>(`/site-pages/${siteId}?page_id=${pageId}`, "DELETE"),
    reviews: (siteId: string) => request<any[]>(`/site-review/${siteId}`, "GET"),
    analyze: (siteId: string) => request<any>(`/site-analyze/${siteId}`, "POST"),
    execute: (siteId: string) => request<any>(`/site-execute/${siteId}`, "POST"),
  },

  keywords: {
    generate: (url: string) => request<any>("/keywords", "POST", { url }),
  },

  tasks: {
    approve: (taskId: string) => request<any>(`/task-approve/${taskId}`, "POST"),
    delete: (taskId: string) => request<any>(`/task-approve/${taskId}`, "DELETE"),
  },

  // Novas APIs para integrações
  integrations: {
    status: () => request<any>("/integrations/status", "GET"),
    disconnect: () => request<any>("/integrations/disconnect", "DELETE"),
  },

  dashboard: {
    summary: (refresh?: boolean) =>
      request<any>(`/dashboard/summary${refresh ? "?refresh=true" : ""}`, "GET"),
    scan: (force?: boolean) => request<any>(`/scan${force ? "?force=true" : ""}`, "POST"),
    diagnose: () => request<any>("/scan/diagnose", "GET"),
    oportunidades: (filters?: { impactos?: string; tipos?: string; otimizados?: string }) => {
      const params = new URLSearchParams();
      if (filters?.impactos) params.set("impactos", filters.impactos);
      if (filters?.tipos) params.set("tipos", filters.tipos);
      if (filters?.otimizados) params.set("otimizados", filters.otimizados);
      const qs = params.toString();
      return request<{
        connected: boolean;
        oportunidades: unknown[];
        counts: Record<string, number>;
        filtros_disponiveis: { id: string; label: string; count: number; kind?: string }[];
      }>(`/dashboard/oportunidades${qs ? `?${qs}` : ""}`, "GET");
    },
  },

  // Google Search Console
  gsc: {
    getAuthUrl: () => request<{ auth_url: string }>("/gsc/auth-url", "GET"),
    status: () => request<{ connected: boolean; site_url?: string; updated_at?: string }>("/gsc/status", "GET"),
    sites: () => request<{ sites: string[] }>("/gsc/sites", "GET"),
    setSite: (site_url: string) => request<any>(`/gsc/site?site_url=${encodeURIComponent(site_url)}`, "PUT"),
    disconnect: () => request<any>("/gsc/disconnect", "DELETE"),
    overview: () => request<any>("/gsc/overview", "GET"),
    performance: (start_date?: string, end_date?: string) => {
      let url = "/gsc/performance";
      const params: string[] = [];
      if (start_date) params.push(`start_date=${start_date}`);
      if (end_date) params.push(`end_date=${end_date}`);
      if (params.length) url += `?${params.join("&")}`;
      return request<any>(url, "GET");
    },
  },

  // Termos de Pesquisa (SearchAPI / Google Trends)
  termos: {
    trends: (keywords: string[], geo = "BR", timeframe = "today 3-m") =>
      request<any>("/termos/trends", "POST", { keywords, geo, timeframe }),
    trending: () =>
      request<{
        geo: string;
        time: string;
        trends: Array<{
          position: number;
          query: string;
          search_volume: number;
          percentage_increase: number;
          categories: string[];
          keywords: string[];
          is_active: boolean;
          start_date?: string | null;
        }>;
        count: number;
        cached: boolean;
        error?: string;
      }>("/termos/trending", "GET"),
    lookup: (term: string, geo = "BR", timeframe = "today 3-m") =>
      request<{
        term: string;
        geo: string;
        timeframe: string;
        chance: "alta" | "moderada" | "baixa";
        current_interest: number;
        average_interest: number;
        peak_interest: number;
        trend: string;
        searches_per_month: string;
        conversion_estimate: string;
        related: { top: Array<{ query: string; value: number }>; rising: Array<{ query: string; value: number }> };
        warning?: string;
      }>("/termos/lookup", "POST", { term, geo, timeframe }),
    list: () => request<any>("/termos", "GET"),
    add: (term: string) => request<any>("/termos", "POST", { term }),
    remove: (termId: string) => request<any>(`/termos/${termId}`, "DELETE"),
    refresh: () => request<any>("/termos/refresh", "POST"),
  },

  // Histórico (GSC Snapshots)
  historico: {
    list: (days = 30) => request<any>(`/historico?days=${days}`, "GET"),
    snapshot: () => request<any>("/historico/snapshot", "POST"),
  },

  // Panorama SEO
  panorama: {
    get: () => request<any>("/panorama", "GET"),
  },

  // API Shopify
  shopify: {
    /** Inicia OAuth do app 4SEO (requer domínio da loja). */
    getAuthUrl: (shop: string) =>
      request<{ auth_url: string; state: string; shop: string }>("/shopify/auth", "POST", { shop }),

    /** Conexão legada com access token de app customizado na loja. */
    connect: (shop_url: string, access_token: string) =>
      request<any>("/shopify/connect", "POST", { shop_url, access_token }),
    
    disconnect: (shop_url: string) =>
      request<any>(`/shopify/disconnect?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
    
    products: (shop_url: string, limit = 1000) =>
      request<any>(`/shopify/products?shop_url=${encodeURIComponent(shop_url)}&limit=${limit}`, "GET"),
    
    analyzeProduct: (shop_url: string, product_id: number) =>
      request<any>(`/shopify/product/${product_id}/analyze?shop_url=${encodeURIComponent(shop_url)}`, "GET"),
    
    optimizeProduct: (shop_url: string, product_id: number, options?: {
      optimize_title?: boolean;
      optimize_description?: boolean;
      optimize_seo_title?: boolean;
      optimize_seo_description?: boolean;
      optimize_image_alts?: boolean;
      target_keyword?: string;
      recommended_actions?: string[];
    }) =>
      request<any>(`/shopify/product/${product_id}/optimize?shop_url=${encodeURIComponent(shop_url)}`, "POST", options || {
        optimize_title: true,
        optimize_description: true,
        optimize_seo_title: true,
        optimize_seo_description: true,
        optimize_image_alts: false,
      }),
    
    listProposals: (shop_url: string, status?: string, product_id?: number) => {
      let url = `/shopify/proposals?shop_url=${encodeURIComponent(shop_url)}`;
      if (status) url += `&status=${status}`;
      if (product_id) url += `&product_id=${product_id}`;
      return request<any>(url, "GET");
    },
    
    approveProposals: (shop_url: string, proposal_ids: string[]) => {
      const params = new URLSearchParams();
      params.append('shop_url', shop_url);
      proposal_ids.forEach(id => params.append('proposal_ids', id));
      return request<any>(`/shopify/proposals/approve?${params.toString()}`, "POST");
    },
    
    rejectProposals: (shop_url: string, proposal_ids: string[]) => {
      const params = new URLSearchParams();
      params.append('shop_url', shop_url);
      proposal_ids.forEach(id => params.append('proposal_ids', id));
      return request<any>(`/shopify/proposals/reject?${params.toString()}`, "POST");
    },
    
    applyProposals: (shop_url: string, product_id?: number, proposals?: any[]) => {
      let url = `/shopify/proposals/apply?shop_url=${encodeURIComponent(shop_url)}`;
      if (product_id) url += `&product_id=${product_id}`;
      return request<any>(url, "POST", proposals && proposals.length ? { proposals } : undefined);
    },
    
    listRollbacks: (shop_url: string, product_id?: number) => {
      let url = `/shopify/rollback?shop_url=${encodeURIComponent(shop_url)}`;
      if (product_id) url += `&product_id=${product_id}`;
      return request<any>(url, "GET");
    },
    
    rollbackSingle: (shop_url: string, rollback_id: string) =>
      request<any>(`/shopify/rollback/${rollback_id}?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
    
    rollbackProduct: (shop_url: string, product_id: number) =>
      request<any>(`/shopify/rollback/product/${product_id}?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
    
    rollbackAll: (shop_url: string) =>
      request<any>(`/shopify/rollback/all?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
    
    rollbackDirect: (shop_url: string, record: any) =>
      request<any>(`/shopify/rollback/direct?shop_url=${encodeURIComponent(shop_url)}`, "POST", { record }),
    
    // ==================== COLEÇÕES ====================
    
    collections: (shop_url: string, limit: number = 50) =>
      request<any>(`/shopify/collections?shop_url=${encodeURIComponent(shop_url)}&limit=${limit}`),
    
    analyzeCollection: (shop_url: string, collection_id: number, collection_type: string = "custom") =>
      request<any>(`/shopify/collection/${collection_id}/analyze?shop_url=${encodeURIComponent(shop_url)}&collection_type=${collection_type}`),
    
    optimizeCollection: (shop_url: string, collection_id: number, collection_type: string = "custom") =>
      request<any>(`/shopify/collection/${collection_id}/optimize?shop_url=${encodeURIComponent(shop_url)}&collection_type=${collection_type}`, "POST"),
    
    // ==================== PÁGINAS ====================
    
    pages: (shop_url: string, limit: number = 50) =>
      request<any>(`/shopify/pages?shop_url=${encodeURIComponent(shop_url)}&limit=${limit}`),
    
    analyzePage: (shop_url: string, page_id: number) =>
      request<any>(`/shopify/page/${page_id}/analyze?shop_url=${encodeURIComponent(shop_url)}`),
    
    optimizePage: (shop_url: string, page_id: number) =>
      request<any>(`/shopify/page/${page_id}/optimize?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
    
    // ==================== BLOG E ARTIGOS ====================
    
    blogs: (shop_url: string) =>
      request<any>(`/shopify/blogs?shop_url=${encodeURIComponent(shop_url)}`),
    
    articles: (shop_url: string, blog_id?: number, limit: number = 50) =>
      request<any>(`/shopify/articles?shop_url=${encodeURIComponent(shop_url)}${blog_id ? `&blog_id=${blog_id}` : ''}&limit=${limit}`),
    
    analyzeArticle: (shop_url: string, blog_id: number, article_id: number) =>
      request<any>(`/shopify/article/${blog_id}/${article_id}/analyze?shop_url=${encodeURIComponent(shop_url)}`),
    
    optimizeArticle: (shop_url: string, blog_id: number, article_id: number) =>
      request<any>(`/shopify/article/${blog_id}/${article_id}/optimize?shop_url=${encodeURIComponent(shop_url)}`, "POST"),
  },

  // API Nuvemshop (Brasil)
  nuvemshop: {
    // OAuth
    getAuthUrl: (redirect_uri?: string) => {
      let url = "/nuvemshop/auth";
      if (redirect_uri) url += `?redirect_uri=${encodeURIComponent(redirect_uri)}`;
      return request<any>(url, "GET");
    },
    
    oauthCallback: (code: string, state: string) =>
      request<any>(`/nuvemshop/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`, "GET"),
    
    // Troca manual de código (quando Nuvemshop não redireciona)
    exchangeCode: (code: string) =>
      request<any>("/nuvemshop/exchange-code", "POST", { code }),
    
    // Conexão direta com token (quando já tem access_token e store_id)
    connectWithToken: (access_token: string, store_id: string) =>
      request<any>("/nuvemshop/connect-token", "POST", { access_token, store_id }),
    
    // Produtos
    products: (store_id: string, limit = 1000) =>
      request<any>(`/nuvemshop/products?store_id=${store_id}&limit=${limit}`, "GET"),
    
    analyzeProduct: (store_id: string, product_id: number) =>
      request<any>(`/nuvemshop/product/${product_id}/analyze?store_id=${store_id}`, "GET"),
    
    optimizeProduct: (store_id: string, product_id: number, options?: {
      optimize_name?: boolean;
      optimize_title?: boolean;
      optimize_description?: boolean;
      optimize_seo_title?: boolean;
      optimize_seo_description?: boolean;
      optimize_image_alts?: boolean;
      generate_tags?: boolean;
      target_keyword?: string;
      recommended_actions?: string[];
    }) =>
      request<any>(`/nuvemshop/product/${product_id}/optimize?store_id=${store_id}${options?.target_keyword ? `&target_keyword=${encodeURIComponent(options.target_keyword)}` : ''}`, "POST", options || {
        optimize_title: true,
        optimize_description: true,
        optimize_seo_title: true,
        optimize_seo_description: true,
        generate_tags: true,
      }),
    
    // Categorias
    categories: (store_id: string, limit = 50) =>
      request<any>(`/nuvemshop/categories?store_id=${store_id}&limit=${limit}`, "GET"),
    
    analyzeCategory: (store_id: string, category_id: number) =>
      request<any>(`/nuvemshop/category/${category_id}/analyze?store_id=${store_id}`, "GET"),
    
    optimizeCategory: (store_id: string, category_id: number, target_keyword?: string) =>
      request<any>(`/nuvemshop/category/${category_id}/optimize?store_id=${store_id}${target_keyword ? `&target_keyword=${encodeURIComponent(target_keyword)}` : ''}`, "POST"),
    
    // Páginas
    pages: (store_id: string, limit = 50) =>
      request<any>(`/nuvemshop/pages?store_id=${store_id}&limit=${limit}`, "GET"),
    
    analyzePage: (store_id: string, page_id: number) =>
      request<any>(`/nuvemshop/page/${page_id}/analyze?store_id=${store_id}`, "GET"),
    
    optimizePage: (store_id: string, page_id: number, target_keyword?: string) =>
      request<any>(`/nuvemshop/page/${page_id}/optimize?store_id=${store_id}${target_keyword ? `&target_keyword=${encodeURIComponent(target_keyword)}` : ''}`, "POST"),
    
    // Blog
    blogPosts: (store_id: string, limit = 50) =>
      request<any>(`/nuvemshop/blog?store_id=${store_id}&limit=${limit}`, "GET"),
    
    analyzeBlogPost: (store_id: string, blog_id: number, post_id: number) =>
      request<any>(`/nuvemshop/blog/${blog_id}/${post_id}/analyze?store_id=${store_id}`, "GET"),
    
    optimizeBlogPost: (store_id: string, blog_id: number, post_id: number, target_keyword?: string) =>
      request<any>(`/nuvemshop/blog/${blog_id}/${post_id}/optimize?store_id=${store_id}${target_keyword ? `&target_keyword=${encodeURIComponent(target_keyword)}` : ''}`, "POST"),
    
    // Propostas
    listProposals: (store_id: string, status?: string, content_type?: string) => {
      let url = `/nuvemshop/proposals?store_id=${store_id}`;
      if (status) url += `&status=${status}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<any>(url, "GET");
    },
    
    approveProposals: (store_id: string, proposal_ids: string[]) =>
      request<any>(`/nuvemshop/proposals/approve?store_id=${store_id}`, "POST", { proposal_ids }),
    
    rejectProposals: (store_id: string, proposal_ids: string[]) =>
      request<any>(`/nuvemshop/proposals/reject?store_id=${store_id}`, "POST", { proposal_ids }),
    
    applyProposals: (store_id: string, item_id?: number, proposals?: any[]) => {
      let url = `/nuvemshop/proposals/apply?store_id=${store_id}`;
      if (item_id) url += `&item_id=${item_id}`;
      return request<any>(url, "POST", proposals?.length ? { proposals } : undefined);
    },
    
    // Rollback
    listRollbacks: (store_id: string, content_type?: string) => {
      let url = `/nuvemshop/rollback?store_id=${store_id}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<any>(url, "GET");
    },
    
    rollbackSingle: (store_id: string, rollback_id: string) =>
      request<any>(`/nuvemshop/rollback/${rollback_id}?store_id=${store_id}`, "POST"),
    
    rollbackAll: (store_id: string) =>
      request<any>(`/nuvemshop/rollback/all?store_id=${store_id}`, "POST"),
    
    rollbackDirect: (store_id: string, record: any) =>
      request<any>(`/nuvemshop/rollback/direct?store_id=${store_id}`, "POST", { record }),
  },

  // API VTEX
  vtex: {
    connect: (account_name: string, app_key: string, app_token: string) =>
      request<IntegrationConnectResponse>("/vtex/connect", "POST", { account_name, app_key, app_token }),

    products: (store_id: string, limit = 500) =>
      request<ProductsResponse>(`/vtex/products?store_id=${encodeURIComponent(store_id)}&limit=${limit}`, "GET"),

    analyzeProduct: (store_id: string, product_id: number) =>
      request<IntegrationSEOAnalysis>(`/vtex/product/${product_id}/analyze?store_id=${encodeURIComponent(store_id)}`, "GET"),

    optimizeProduct: (store_id: string, product_id: number, options?: {
      target_keyword?: string;
      recommended_actions?: string[];
    }) =>
      request<ProposalsResponse>(
        `/vtex/product/${product_id}/optimize?store_id=${encodeURIComponent(store_id)}${options?.target_keyword ? `&target_keyword=${encodeURIComponent(options.target_keyword)}` : ''}`,
        "POST",
        options || {}
      ),

    categories: (store_id: string, limit = 100) =>
      request<CategoriesResponse>(`/vtex/categories?store_id=${encodeURIComponent(store_id)}&limit=${limit}`, "GET"),

    analyzeCategory: (store_id: string, category_id: number) =>
      request<IntegrationSEOAnalysis>(`/vtex/category/${category_id}/analyze?store_id=${encodeURIComponent(store_id)}`, "GET"),

    optimizeCategory: (store_id: string, category_id: number, target_keyword?: string) =>
      request<ProposalsResponse>(`/vtex/category/${category_id}/optimize?store_id=${encodeURIComponent(store_id)}${target_keyword ? `&target_keyword=${encodeURIComponent(target_keyword)}` : ''}`, "POST"),

    listProposals: (store_id: string, status?: string, content_type?: string) => {
      let url = `/vtex/proposals?store_id=${encodeURIComponent(store_id)}`;
      if (status) url += `&status=${status}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<ProposalsResponse>(url, "GET");
    },

    approveProposals: (store_id: string, proposal_ids: string[]) =>
      request<{ approved?: number }>(`/vtex/proposals/approve?store_id=${encodeURIComponent(store_id)}`, "POST", { proposal_ids }),

    rejectProposals: (store_id: string, proposal_ids: string[]) =>
      request<{ rejected?: number }>(`/vtex/proposals/reject?store_id=${encodeURIComponent(store_id)}`, "POST", { proposal_ids }),

    applyProposals: (store_id: string, item_id?: number, proposals?: IntegrationProposal[]) => {
      let url = `/vtex/proposals/apply?store_id=${encodeURIComponent(store_id)}`;
      if (item_id) url += `&item_id=${item_id}`;
      return request<ApplyResponse>(url, "POST", proposals?.length ? { proposals } : undefined);
    },

    listRollbacks: (store_id: string, content_type?: string) => {
      let url = `/vtex/rollback?store_id=${encodeURIComponent(store_id)}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<RollbacksResponse>(url, "GET");
    },

    rollbackDirect: (store_id: string, record: IntegrationRollback) =>
      request<{ rolled_back?: number; message?: string }>(`/vtex/rollback/direct?store_id=${encodeURIComponent(store_id)}`, "POST", { record }),

    rollbackAll: (store_id: string) =>
      request<{ rolled_back?: number; message?: string }>(`/vtex/rollback/all?store_id=${encodeURIComponent(store_id)}`, "POST"),
  },

  // API Loja Integrada
  lojaintegrada: {
    connect: (chave_api: string) =>
      request<IntegrationConnectResponse>("/lojaintegrada/connect", "POST", { chave_api }),

    products: (store_id: string, limit = 500) =>
      request<ProductsResponse>(`/lojaintegrada/products?store_id=${encodeURIComponent(store_id)}&limit=${limit}`, "GET"),

    analyzeProduct: (store_id: string, product_id: number) =>
      request<IntegrationSEOAnalysis>(`/lojaintegrada/product/${product_id}/analyze?store_id=${encodeURIComponent(store_id)}`, "GET"),

    optimizeProduct: (store_id: string, product_id: number, options?: {
      target_keyword?: string;
      recommended_actions?: string[];
    }) =>
      request<ProposalsResponse>(
        `/lojaintegrada/product/${product_id}/optimize?store_id=${encodeURIComponent(store_id)}${options?.target_keyword ? `&target_keyword=${encodeURIComponent(options.target_keyword)}` : ''}`,
        "POST",
        options || {}
      ),

    categories: (store_id: string, limit = 100) =>
      request<CategoriesResponse>(`/lojaintegrada/categories?store_id=${encodeURIComponent(store_id)}&limit=${limit}`, "GET"),

    analyzeCategory: (store_id: string, category_id: number) =>
      request<IntegrationSEOAnalysis>(`/lojaintegrada/category/${category_id}/analyze?store_id=${encodeURIComponent(store_id)}`, "GET"),

    optimizeCategory: (store_id: string, category_id: number, target_keyword?: string) =>
      request<ProposalsResponse>(`/lojaintegrada/category/${category_id}/optimize?store_id=${encodeURIComponent(store_id)}${target_keyword ? `&target_keyword=${encodeURIComponent(target_keyword)}` : ''}`, "POST"),

    listProposals: (store_id: string, status?: string, content_type?: string) => {
      let url = `/lojaintegrada/proposals?store_id=${encodeURIComponent(store_id)}`;
      if (status) url += `&status=${status}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<ProposalsResponse>(url, "GET");
    },

    approveProposals: (store_id: string, proposal_ids: string[]) =>
      request<{ approved?: number }>(`/lojaintegrada/proposals/approve?store_id=${encodeURIComponent(store_id)}`, "POST", { proposal_ids }),

    rejectProposals: (store_id: string, proposal_ids: string[]) =>
      request<{ rejected?: number }>(`/lojaintegrada/proposals/reject?store_id=${encodeURIComponent(store_id)}`, "POST", { proposal_ids }),

    applyProposals: (store_id: string, item_id?: number, proposals?: IntegrationProposal[]) => {
      let url = `/lojaintegrada/proposals/apply?store_id=${encodeURIComponent(store_id)}`;
      if (item_id) url += `&item_id=${item_id}`;
      return request<ApplyResponse>(url, "POST", proposals?.length ? { proposals } : undefined);
    },

    listRollbacks: (store_id: string, content_type?: string) => {
      let url = `/lojaintegrada/rollback?store_id=${encodeURIComponent(store_id)}`;
      if (content_type) url += `&content_type=${content_type}`;
      return request<RollbacksResponse>(url, "GET");
    },

    rollbackDirect: (store_id: string, record: IntegrationRollback) =>
      request<{ rolled_back?: number; message?: string }>(`/lojaintegrada/rollback/direct?store_id=${encodeURIComponent(store_id)}`, "POST", { record }),

    rollbackAll: (store_id: string) =>
      request<{ rolled_back?: number; message?: string }>(`/lojaintegrada/rollback/all?store_id=${encodeURIComponent(store_id)}`, "POST"),
  },

  admin: {
    login: async (email: string, password: string) => {
      const res = await fetch(`${API_BASE}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : null;
      if (!res.ok) {
        const detail = data?.detail || data?.message || `Erro HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : "Falha no login administrativo");
      }
      return data as { ok: boolean; token: string; email: string };
    },
    me: () => adminRequest<{ ok: boolean; userId: string | null; email: string }>("/admin/me", "GET"),
    overview: (period: "7d" | "30d" | "90d" | "12m" = "30d") =>
      adminRequest<Record<string, unknown>>(`/admin/overview?period=${period}`, "GET"),
    users: (params: { page?: number; perPage?: number; q?: string; subscription?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.page) qs.set("page", String(params.page));
      if (params.perPage) qs.set("perPage", String(params.perPage));
      if (params.q) qs.set("q", params.q);
      if (params.subscription) qs.set("subscription", params.subscription);
      const q = qs.toString();
      return adminRequest<{
        items: Array<Record<string, unknown>>;
        page: number;
        perPage: number;
        total: number;
      }>(`/admin/users${q ? `?${q}` : ""}`, "GET");
    },
    user: (userId: string) =>
      adminRequest<Record<string, unknown>>(`/admin/users/${encodeURIComponent(userId)}`, "GET"),
    subscriptions: (
      params: { status?: string; plan?: string; expiringDays?: number; page?: number; perPage?: number } = {}
    ) => {
      const qs = new URLSearchParams();
      if (params.status) qs.set("status", params.status);
      if (params.plan) qs.set("plan", params.plan);
      if (params.expiringDays) qs.set("expiringDays", String(params.expiringDays));
      if (params.page) qs.set("page", String(params.page));
      if (params.perPage) qs.set("perPage", String(params.perPage));
      const q = qs.toString();
      return adminRequest<{
        items: Array<Record<string, unknown>>;
        page: number;
        perPage: number;
        total: number;
      }>(`/admin/subscriptions${q ? `?${q}` : ""}`, "GET");
    },
    changePlan: (
      subscriptionId: string,
      body: { planId: string; billingCycle?: string; reason?: string }
    ) =>
      adminRequest<{ ok: boolean; subscription: Record<string, unknown> }>(
        `/admin/subscriptions/${encodeURIComponent(subscriptionId)}/change-plan`,
        "POST",
        body
      ),
    cancelSubscription: (subscriptionId: string, reason: string) =>
      adminRequest<{ ok: boolean; subscription: Record<string, unknown> }>(
        `/admin/subscriptions/${encodeURIComponent(subscriptionId)}/cancel`,
        "POST",
        { reason }
      ),
    tickets: () =>
      adminRequest<{ items: Array<Record<string, unknown>>; counts: Record<string, number> }>(
        "/admin/tickets",
        "GET"
      ),
    patchTicket: (ticketId: string, body: { status?: string; priority?: string }) =>
      adminRequest<{ ok: boolean; ticket: Record<string, unknown> }>(
        `/admin/tickets/${encodeURIComponent(ticketId)}`,
        "PATCH",
        body
      ),
    health: () => adminRequest<Record<string, unknown>>("/admin/health", "GET"),
    audit: (limit = 50) =>
      adminRequest<{ items: Array<Record<string, unknown>> }>(`/admin/audit?limit=${limit}`, "GET"),
  },
};
