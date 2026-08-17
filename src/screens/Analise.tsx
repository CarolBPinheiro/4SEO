import { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useSeoScanner } from "@/hooks/useSeoScanner";
import { useShopify, ShopifyProposal } from "@/hooks/useShopify";
import { useStore } from "@/contexts/StoreContext";
import NuvemshopAnalise from "@/components/seo/NuvemshopAnalise";
import ShopifyAnalise from "@/components/seo/ShopifyAnalise";
import VtexAnalise from "@/components/seo/VtexAnalise";
import LojaIntegradaAnalise from "@/components/seo/LojaIntegradaAnalise";
import Toast from "@/components/seo/Toast";
import SiteForm from "@/components/seo/SiteForm";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useBilling } from "@/contexts/BillingContext";
import {
  FileSearch,
  AlertTriangle,
  CheckCircle,
  Lock,
  Sparkles,
  ArrowLeft,
  FileText,
  Image,
  Loader2,
  Package,
  RefreshCw,
  Check,
  X,
} from "lucide-react";

/* ── Stepper ─────────────────────────────────── */
function Stepper({ currentStep }: { currentStep: number }) {
  const steps = [
    { label: "Página Selecionada", num: 1 },
    { label: "Analisar SEO", num: 2 },
    { label: "Gerar Propostas", num: 3 },
    { label: "Aplicar", num: 4 },
  ];

  return (
    <div className="flex items-center justify-center gap-0 mb-6">
      {steps.map((step, i) => (
        <div key={step.num} className="flex items-center">
          <div className="flex flex-col items-center gap-1.5">
            {step.num < currentStep ? (
              <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-white" />
              </div>
            ) : step.num === currentStep ? (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-sm font-bold">
                {step.num}
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-muted/50 flex items-center justify-center">
                <Lock className="w-4 h-4 text-muted-foreground" />
              </div>
            )}
            <span className={`text-xs whitespace-nowrap ${step.num === currentStep ? "text-foreground font-semibold" : "text-muted-foreground"}`}>
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-16 h-0.5 mx-2 mt-[-18px] ${step.num < currentStep ? "bg-green-500" : "bg-muted/50"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Score card (simplified) ────────────────── */
function ScoreCard({ label, score, barColor }: {
  label: string;
  score: number;
  barColor: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 flex flex-col">
      <span className="text-sm text-muted-foreground mb-2">{label}</span>
      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-3xl font-bold">{score}</span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
      <div className="w-full h-1.5 bg-muted/30 rounded-full">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}

/* ── Shopify field labels ────────────────── */
const FIELD_LABELS: Record<string, string> = {
  title: "Título do Produto",
  body_html: "Descrição",
  title_tag: "SEO Title",
  description_tag: "SEO Description",
  alt_text: "Alt Text da Imagem",
  tags: "Tags",
  faq: "FAQ (Perguntas Frequentes)",
  rich_description: "Descrição Rica",
};

/* ── Issue labels for Shopify analysis ──── */
const ISSUE_MESSAGES: Record<string, string> = {
  missing_title_tag: "Meta Title SEO ausente",
  short_title_tag: "Meta Title SEO muito curto",
  long_title_tag: "Meta Title SEO muito longo",
  missing_description_tag: "Meta Description SEO ausente",
  short_description_tag: "Meta Description SEO muito curta",
  long_description_tag: "Meta Description SEO muito longa",
  missing_body_html: "Descrição do produto ausente",
  short_body_html: "Descrição do produto muito curta",
  images_without_alt: "Imagens sem texto alternativo",
  no_images: "Produto sem imagens",
  missing_tags: "Produto sem tags/categorias",
  missing_h1: "Tag H1 ausente na descrição",
  missing_schema: "Schema.org ausente",
  generic_title: "Título genérico (pouco descritivo)",
};

/* ═══════════════════════════════════════════════
   Connected Mode  - Shopify product-based analysis
   ═══════════════════════════════════════════════ */
function ConnectedAnalise() {
  const {
    products,
    selectedProduct,
    analysis,
    proposals,
    loading,
    toast: shopifyToast,
    fetchProducts,
    selectProduct,
    generateProposals,
    approveProposals,
    rejectProposals,
    applyProposals,
    connection,
    initFromStore,
  } = useShopify();

  const { store } = useStore();

  const [view, setView] = useState<"analysis" | "proposals">("analysis");

  // Initialize useShopify connection from StoreContext (backend already has the token)
  useEffect(() => {
    if (!store?.url || connection.connected) return;
    initFromStore(store.url, store.name);
  }, [store, connection.connected, initFromStore]);

  // Auto-fetch products when connected
  useEffect(() => {
    if (connection.connected && products.length === 0) {
      fetchProducts();
    }
  }, [connection.connected, products.length, fetchProducts]);

  // Determine stepper step
  const currentStep = !selectedProduct ? 1 : view === "analysis" ? 2 : proposals.length > 0 ? (proposals.some(p => p.status === "applied") ? 4 : 3) : 3;

  // Pending proposals for current product
  const productProposals = useMemo(
    () => proposals.filter(p => selectedProduct && p.product_id === selectedProduct.id),
    [proposals, selectedProduct]
  );

  const pendingProposals = productProposals.filter(p => p.status === "pending");
  const approvedProposals = productProposals.filter(p => p.status === "approved");

  return (
    <div className="space-y-4">
      <Stepper currentStep={currentStep} />

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-5">
        {/* ── Left Panel: Products as "Páginas" ── */}
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-semibold">Páginas</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">{products.length}</Badge>
              <button
                onClick={fetchProducts}
                disabled={loading}
                className="text-muted-foreground hover:text-foreground transition-colors"
                title="Recarregar"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          <div className="w-full text-left text-xs px-2 py-1.5 rounded-lg bg-primary/15 text-primary mb-2">
            {store?.url || connection.shop_url}
          </div>
          <p className="text-xs text-muted-foreground mb-3">Selecione uma página para analisar</p>

          {/* Products list */}
          <div className="space-y-1 max-h-[60vh] overflow-y-auto pr-1">
            {products.map((product) => {
              const thumb = product.images?.[0]?.src;
              return (
                <button
                  key={product.id}
                  onClick={() => { selectProduct(product); setView("analysis"); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors ${
                    selectedProduct?.id === product.id
                      ? "bg-primary/15 text-primary border border-primary/30"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                  }`}
                >
                  {thumb ? (
                    <img src={thumb} alt="" className="w-8 h-8 rounded object-cover flex-shrink-0" />
                  ) : (
                    <Package className="w-4 h-4 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{product.title}</p>
                    <p className="text-[10px] text-muted-foreground truncate">/{product.handle}</p>
                  </div>
                </button>
              );
            })}
            {products.length === 0 && !loading && (
              <p className="text-xs text-muted-foreground text-center py-4">
                {connection.connected ? "Nenhum produto encontrado" : "Conectando à loja..."}
              </p>
            )}
            {loading && products.length === 0 && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>
        </div>

        {/* ── Right Panel ── */}
        <div className="flex flex-col gap-4">
          {!selectedProduct ? (
            /* Empty state */
            <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center">
              <Package className="w-16 h-16 text-muted-foreground/30 mb-4" />
              <p className="text-lg text-muted-foreground">
                {products.length === 0
                  ? "Carregando páginas da loja..."
                  : "Selecione uma página para analisar"}
              </p>
            </div>
          ) : view === "analysis" ? (
            /* ═══ ANALYSIS VIEW (Step 2) ═══ */
            <>
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center gap-3 mb-4">
                  {selectedProduct.images?.[0]?.src && (
                    <img src={selectedProduct.images[0].src} alt="" className="w-12 h-12 rounded-lg object-cover" />
                  )}
                  <div>
                    <h2 className="text-lg font-semibold">{selectedProduct.title}</h2>
                    <p className="text-xs text-muted-foreground">/{selectedProduct.handle}</p>
                  </div>
                </div>

                {loading && !analysis ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-primary mr-3" />
                    <span className="text-muted-foreground">Analisando SEO...</span>
                  </div>
                ) : analysis ? (
                  <>
                    {/* Score */}
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                      <ScoreCard
                        label="SEO Score"
                        score={analysis.score}
                        barColor={analysis.score >= 80 ? "hsl(145, 65%, 45%)" : analysis.score >= 50 ? "hsl(45, 100%, 55%)" : "hsl(0, 70%, 50%)"}
                      />
                      {analysis.images_without_alt !== undefined && (
                        <ScoreCard
                          label="Imagens sem Alt"
                          score={Math.max(0, 100 - (analysis.images_without_alt ?? 0) * 20)}
                          barColor={analysis.images_without_alt === 0 ? "hsl(145, 65%, 45%)" : "hsl(24, 100%, 55%)"}
                        />
                      )}
                      <ScoreCard
                        label="Problemas"
                        score={Math.max(0, 100 - (analysis.issues?.length ?? 0) * 15)}
                        barColor={analysis.issues?.length === 0 ? "hsl(145, 65%, 45%)" : "hsl(0, 70%, 50%)"}
                      />
                    </div>

                    {/* Issues list */}
                    {analysis.issues && analysis.issues.length > 0 && (
                      <div className="mb-6">
                        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-yellow-500" />
                          Problemas Encontrados ({analysis.issues.length})
                        </h3>
                        <div className="space-y-2">
                          {analysis.issues.map((issue, i) => (
                            <div
                              key={i}
                              className={`flex items-start gap-3 px-4 py-3 rounded-lg border ${
                                issue.severity === "critical"
                                  ? "border-red-500/30 bg-red-500/5"
                                  : issue.severity === "warning"
                                  ? "border-yellow-500/30 bg-yellow-500/5"
                                  : "border-border bg-muted/5"
                              }`}
                            >
                              <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                                issue.severity === "critical" ? "text-red-400" : "text-yellow-400"
                              }`} />
                              <div>
                                <p className="text-sm font-medium">
                                  {ISSUE_MESSAGES[issue.type] || issue.message || issue.type}
                                </p>
                                {issue.message && ISSUE_MESSAGES[issue.type] && (
                                  <p className="text-xs text-muted-foreground mt-0.5">{issue.message}</p>
                                )}
                              </div>
                              <Badge variant="outline" className={`ml-auto text-[10px] flex-shrink-0 ${
                                issue.severity === "critical" ? "border-red-500/30 text-red-400" : "border-yellow-500/30 text-yellow-400"
                              }`}>
                                {issue.severity === "critical" ? "Crítico" : "Aviso"}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommendations */}
                    {analysis.recommendations && analysis.recommendations.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          Recomendações ({analysis.recommendations.length})
                        </h3>
                        <div className="space-y-2">
                          {analysis.recommendations.map((rec, i) => (
                            <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg border border-green-500/20 bg-green-500/5">
                              <Sparkles className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                              <p className="text-sm text-muted-foreground">{rec}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : null}
              </div>

              {/* Generate proposals button */}
              {analysis && (
                <div className="flex justify-end">
                  <Button
                    className="btn-gradient text-primary-foreground font-semibold gap-2"
                    size="lg"
                    onClick={async () => {
                      if (selectedProduct) {
                        await generateProposals(selectedProduct.id);
                        setView("proposals");
                      }
                    }}
                    disabled={loading}
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Sparkles className="w-5 h-5" />
                    )}
                    Gerar Propostas de Otimização IA
                  </Button>
                </div>
              )}
            </>
          ) : (
            /* ═══ PROPOSALS VIEW (Step 3/4) ═══ */
            <>
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center text-primary">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">Propostas de Otimização IA</h2>
                      <p className="text-xs text-muted-foreground">
                        {productProposals.length} proposta(s) para <span className="font-semibold text-foreground">{selectedProduct?.title}</span>
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => setView("analysis")}>
                    <ArrowLeft className="w-4 h-4" />
                    Voltar à análise
                  </Button>
                </div>

                {/* Batch actions */}
                {pendingProposals.length > 0 && (
                  <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5 border-green-500/30 text-green-400 hover:bg-green-500/10"
                      onClick={() => approveProposals(pendingProposals.map(p => p.id))}
                      disabled={loading}
                    >
                      <Check className="w-3.5 h-3.5" />
                      Aprovar Todas ({pendingProposals.length})
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5 border-red-500/30 text-red-400 hover:bg-red-500/10"
                      onClick={() => rejectProposals(pendingProposals.map(p => p.id))}
                      disabled={loading}
                    >
                      <X className="w-3.5 h-3.5" />
                      Rejeitar Todas
                    </Button>
                    {approvedProposals.length > 0 && (
                      <Button
                        size="sm"
                        className="gap-1.5 btn-gradient text-primary-foreground ml-auto"
                        onClick={() => selectedProduct && applyProposals(selectedProduct.id)}
                        disabled={loading}
                      >
                        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                        Aplicar no Shopify ({approvedProposals.length})
                      </Button>
                    )}
                  </div>
                )}

                {approvedProposals.length > 0 && pendingProposals.length === 0 && (
                  <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                    <Button
                      size="sm"
                      className="gap-1.5 btn-gradient text-primary-foreground"
                      onClick={() => selectedProduct && applyProposals(selectedProduct.id)}
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                      Aplicar no Shopify ({approvedProposals.length})
                    </Button>
                  </div>
                )}
              </div>

              {/* Proposal cards */}
              <div className="space-y-3">
                {productProposals.length > 0 ? productProposals.map((proposal) => (
                  <div key={proposal.id} className={`rounded-xl border bg-card p-5 ${
                    proposal.status === "approved" ? "border-green-500/30" :
                    proposal.status === "applied" ? "border-blue-500/30" :
                    proposal.status === "rejected" ? "border-red-500/30 opacity-50" :
                    "border-border"
                  }`}>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-sm">
                            {FIELD_LABELS[proposal.field] || proposal.field}
                          </span>
                          <Badge className={`text-[10px] ${
                            proposal.status === "approved" ? "bg-green-500/20 text-green-400 border-green-500/30" :
                            proposal.status === "applied" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
                            proposal.status === "rejected" ? "bg-red-500/20 text-red-400 border-red-500/30" :
                            "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                          }`}>
                            {proposal.status === "pending" ? "PENDENTE" :
                             proposal.status === "approved" ? "APROVADA" :
                             proposal.status === "applied" ? "APLICADA" : "REJEITADA"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{proposal.reasoning}</p>
                      </div>

                      {proposal.status === "pending" && (
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 h-7 text-xs border-green-500/30 text-green-400 hover:bg-green-500/10"
                            onClick={() => approveProposals([proposal.id])}
                            disabled={loading}
                          >
                            <Check className="w-3 h-3" />
                            Aprovar
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-1 h-7 text-xs border-red-500/30 text-red-400 hover:bg-red-500/10"
                            onClick={() => rejectProposals([proposal.id])}
                            disabled={loading}
                          >
                            <X className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>

                    {/* Original vs Proposed diff */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                        <p className="text-[10px] uppercase tracking-wider text-red-400 mb-1 font-semibold">Original</p>
                        <p className="text-xs text-muted-foreground break-words line-clamp-4">
                          {proposal.original_value || <em className="text-muted-foreground/50">(vazio)</em>}
                        </p>
                      </div>
                      <div className="p-3 rounded-lg bg-green-500/5 border border-green-500/20">
                        <p className="text-[10px] uppercase tracking-wider text-green-400 mb-1 font-semibold">Proposta</p>
                        <p className="text-xs text-muted-foreground break-words line-clamp-4">
                          {proposal.proposed_value}
                        </p>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="rounded-xl border border-border bg-card p-12 flex flex-col items-center justify-center text-center">
                    <Sparkles className="w-12 h-12 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">
                      {loading ? "Gerando propostas com IA..." : "Nenhuma proposta gerada ainda."}
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {shopifyToast && <Toast toast={{ message: shopifyToast.message, type: shopifyToast.type === "warning" ? "info" : shopifyToast.type }} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Disconnected Mode  - Generic site crawler
   ═══════════════════════════════════════════════ */
function DisconnectedAnalise() {
  const {
    sites,
    selectedSite,
    pages,
    scanning,
    loading,
    toast,
    createSite,
    selectSite,
    scanSite,
  } = useSeoScanner();

  const [addingSite, setAddingSite] = useState(false);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center gap-3 mb-4">
          <FileSearch className="w-6 h-6 text-primary" />
          <div>
            <h2 className="text-lg font-semibold">Análise SEO</h2>
            <p className="text-xs text-muted-foreground">
              Conecte uma loja para análise completa com IA, ou escaneie um site manualmente
            </p>
          </div>
        </div>

        {/* Site selector / add site */}
        {sites.length === 0 || addingSite ? (
          <div className="max-w-md">
            <SiteForm
              onSubmit={async (url) => {
                const ok = await createSite(url);
                if (ok) setAddingSite(false);
                return ok;
              }}
              loading={loading}
              onCancel={sites.length > 0 ? () => setAddingSite(false) : undefined}
            />
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            <button
              onClick={() => selectSite(sites[0])}
              className={`w-full text-left text-sm px-3 py-2 rounded-lg transition-colors ${
                selectedSite?.id === sites[0].id
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
              }`}
            >
              {sites[0].base_url}
            </button>
            <button onClick={() => setAddingSite(true)} className="text-xs text-primary hover:underline">
              + Analisar outro site
            </button>
          </div>
        )}

        {selectedSite && (
          <Button
            size="sm"
            className="btn-gradient text-primary-foreground gap-2"
            onClick={scanSite}
            disabled={loading || scanning}
          >
            {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSearch className="w-4 h-4" />}
            {scanning ? "Escaneando..." : "Escanear site"}
          </Button>
        )}

        {/* Simple pages list */}
        {pages.length > 0 && (
          <div className="mt-4 space-y-2">
            <h3 className="text-sm font-semibold">Páginas encontradas ({pages.length})</h3>
            {pages.map((page) => (
              <div key={page.id} className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border">
                <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{page.title || page.url}</p>
                  <p className="text-[10px] text-muted-foreground truncate">{page.url}</p>
                </div>
                {page.seo_score !== undefined && (
                  <Badge variant={page.seo_score >= 70 ? "default" : "destructive"} className="text-xs">
                    {page.seo_score}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {toast && <Toast toast={toast} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Main Export  - Routes between modes
   ═══════════════════════════════════════════════ */
export default function Analise() {
  const { connected, store, refreshStatus } = useStore();
  const { loading: billingLoading } = useBilling();
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle OAuth callback params (?connected=true&store_id=X&store_name=Y)
  useEffect(() => {
    const oauthConnected = searchParams.get("connected");
    if (oauthConnected === "true") {
      // Refresh the store context so it picks up the new integration
      refreshStatus();
      // Clean the URL params
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, refreshStatus, setSearchParams]);

  if (billingLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (connected && store?.platform === "nuvemshop") {
    const storeId = store.storeId || store.url.replace(/^https?:\/\//, "").replace(/\/$/, "");
    return <NuvemshopAnalise storeId={storeId} storeName={store.name} />;
  }

  if (connected && store?.platform === "shopify") {
    return <ShopifyAnalise storeUrl={store.url} storeName={store.name} />;
  }

  if (connected && store?.platform === "vtex") {
    return <VtexAnalise storeId={store.storeId} storeName={store.name} />;
  }

  if (connected && store?.platform === "lojaintegrada") {
    return <LojaIntegradaAnalise storeId={store.storeId} storeName={store.name} />;
  }

  if (connected) return <ConnectedAnalise />;
  return <DisconnectedAnalise />;
}
