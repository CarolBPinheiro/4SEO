import { useState, useEffect, useMemo } from "react";
import {
  useNuvemshop,
  NuvemshopProposal,
  NuvemshopRollback,
} from "@/hooks/useNuvemshop";
import { DiagnosisPanel } from "@/components/seo/DiagnosisPanel";
import Toast from "@/components/seo/Toast";
import { RollbackHistory } from "@/components/seo/RollbackHistory";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Package,
  Search,
  Sparkles,
  Check,
  X,
  AlertTriangle,
  CheckCircle,
  Image,
  FileText,
  Loader2,
  FolderOpen,
  FileEdit,
  Newspaper,
  RefreshCw,
  ChevronRight,
  Lock,
  History,
} from "lucide-react";

type ContentTabType = "products" | "categories" | "pages" | "blog";

const FIELD_LABELS: Record<string, string> = {
  name: "Nome",
  title: "Título",
  description: "Descrição",
  body: "Conteúdo",
  content: "Conteúdo",
  seo_title: "SEO Title (Meta Title)",
  seo_description: "SEO Description (Meta Description)",
  image_alt: "Alt da Imagem",
  tags: "Tags e Keywords",
  handle: "URL Slug",
};

// Chaves batem EXATAMENTE com optimization_type gerado por
// backend/app/integrations/nuvemshop_optimizer.py:
// - Produto: sem prefixo (title/description/seo_title/seo_description/tags)
// - Categoria: "category_" + title/description/seo_title/seo_description
// - Página: "page_" + title/content/seo_title/seo_description
// - Blog: "blog_" + title/body/seo_title/seo_description/tags
// (chaves erradas aqui fazem o card cair no fallback "Otimização: undefined")
export const OPTIMIZATION_TITLES: Record<string, string> = {
  // Produto
  title: "Otimização do Nome do Produto",
  description: "Otimização da Descrição",
  seo_title: "Otimização do Meta Title (SEO)",
  seo_description: "Otimização da Meta Description (SEO)",
  tags: "Otimização de Tags e Palavras-chave",
  image_alt: "Otimização do Texto Alternativo da Imagem",
  // Categoria
  category_title: "Otimização do Nome da Categoria",
  category_description: "Otimização da Descrição da Categoria",
  category_seo_title: "Otimização do Meta Title da Categoria",
  category_seo_description: "Otimização da Meta Description da Categoria",
  // Página
  page_title: "Otimização do Título da Página",
  page_content: "Otimização do Conteúdo da Página",
  page_seo_title: "Otimização do Meta Title da Página",
  page_seo_description: "Otimização da Meta Description da Página",
  // Blog
  blog_title: "Otimização do Título do Post",
  blog_body: "Otimização do Conteúdo do Post",
  blog_seo_title: "Otimização do Meta Title do Post",
  blog_seo_description: "Otimização da Meta Description do Post",
  blog_tags: "Otimização de Tags do Post",
};

const ISSUE_MESSAGES: Record<string, string> = {
  missing_name: "Produto sem nome definido",
  short_name: "Nome muito curto - adicione mais palavras-chave (ideal: 50-60 caracteres)",
  long_name: "Nome muito longo - será cortado nos resultados (ideal: 50-60 caracteres)",
  missing_title: "Produto sem título definido",
  short_title: "Título muito curto - adicione mais palavras-chave (ideal: 50-60 caracteres)",
  long_title: "Título muito longo - será cortado nos resultados (ideal: 50-60 caracteres)",
  missing_description: "Produto sem descrição - clientes não encontram informações",
  short_description: "Descrição muito curta - adicione mais detalhes sobre o produto",
  no_semantic_structure: "Descrição sem subtítulos (H2/H3) - dificulta a leitura",
  no_bullet_points: "Considere usar listas para destacar características e benefícios",
  missing_seo_title: "Meta título não definido - esse texto aparece nos resultados do Google",
  missing_seo_description: "Meta descrição não definida - texto que convence o usuário a clicar",
  short_seo_description: "Meta descrição muito curta - adicione mais informações atraentes",
  long_seo_description: "Meta descrição muito longa - será cortada no Google (máx: 160 caracteres)",
  missing_tags: "Sem tags/palavras-chave - dificulta a busca interna",
  few_tags: "Poucas tags - adicione mais para melhorar a busca (recomendado: 5+ tags)",
  missing_image_alt: "Imagem(ns) sem descrição alternativa - prejudica acessibilidade e SEO",
  missing_h2: "Subtítulos (H2) não encontrados - organize melhor o conteúdo",
  no_h2_headings: "Subtítulos (H2) não encontrados - organize melhor o conteúdo",
  missing_schema: "Dados estruturados (Schema.org) ausentes - sem rich snippets no Google",
  title_length: "Tamanho do título inadequado (ideal: 30-60 caracteres)",
  meta_description_length: "Tamanho da meta descrição inadequado (ideal: 120-160 caracteres)",
  missing_category_description: "Categoria sem descrição - explique o que o cliente encontrará",
  short_category_description: "Descrição da categoria muito curta - adicione mais detalhes",
  missing_category_seo: "Categoria sem meta tags SEO - não será bem posicionada no Google",
  missing_content: "Página sem conteúdo - adicione texto relevante",
  short_content: "Conteúdo muito curto - expanda com mais informações úteis",
  medium_content: "Conteúdo pode ser expandido - adicione mais detalhes para melhor ranqueamento",
  missing_page_seo: "Página sem meta tags SEO - não será bem posicionada no Google",
  no_headings: "Página sem estrutura de títulos (H1, H2, H3) - dificulta leitura e SEO",
  missing_body: "Post sem conteúdo - adicione texto relevante",
  short_body: "Conteúdo do post muito curto - expanda com mais informações",
  missing_blog_seo: "Post sem meta tags SEO - não será bem posicionado no Google",
  missing_featured_image: "Sem imagem de destaque - menos atraente visualmente",
};

/* ── Stepper ── */
function Stepper({ currentStep, loading }: { currentStep: number; loading: boolean }) {
  const steps = [
    { label: "Selecionar item", num: 1 },
    { label: "Analisar SEO", num: 2 },
    { label: "Gerar propostas", num: 3 },
    { label: "Aplicar mudanças", num: 4 },
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
              <div className={`w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-sm font-bold ${loading ? "animate-pulse" : ""}`}>
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : step.num}
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

/* ═══ Main Component ═══ */
export default function NuvemshopAnalise({ storeId, storeName }: { storeId: string; storeName?: string }) {
  const {
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
    setConnectionFromOAuth,
    fetchProducts,
    fetchCategories,
    fetchPages,
    fetchBlogPosts,
    selectProduct,
    selectCategory,
    selectPage,
    selectBlogPost,
    generateProductProposals,
    generateCategoryProposals,
    generatePageProposals,
    generateBlogProposals,
    approveProposals,
    rejectProposals,
    applyProposals,
    rollback,
    clearSelection,
  } = useNuvemshop();

  const [contentTab, setContentTab] = useState<ContentTabType>("products");
  const [actionTab, setActionTab] = useState<"analysis" | "proposals" | "rollback">("analysis");
  const [optimizing, setOptimizing] = useState(false);
  const [targetKeyword, setTargetKeyword] = useState("");

  // Initialize connection from StoreContext
  useEffect(() => {
    if (!connection.connected && storeId) {
      setConnectionFromOAuth(storeId, storeName);
    }
  }, [storeId, storeName, connection.connected, setConnectionFromOAuth]);

  // Auto-fetch products when first connected
  useEffect(() => {
    if (connection.connected && products.length === 0) {
      fetchProducts();
    }
  }, [connection.connected, products.length, fetchProducts]);

  const contentTypeMap: Record<ContentTabType, string> = {
    products: "product",
    categories: "category",
    pages: "page",
    blog: "blog",
  };

  const currentContentType = contentTypeMap[contentTab];
  const currentSelection = selectedProduct || selectedCategory || selectedPage || selectedBlogPost;
  const filteredProposals = useMemo(
    () => proposals.filter(p =>
      (!p.content_type || p.content_type === currentContentType) &&
      (!currentSelection || !p.product_id || p.product_id === currentSelection.id)
    ),
    [proposals, currentContentType, currentSelection],
  );
  const pendingProposals = filteredProposals.filter(p => p.status === "pending");
  const approvedProposals = filteredProposals.filter(p => p.status === "approved");

  const currentName = selectedProduct?.name || selectedCategory?.name || selectedPage?.title || selectedBlogPost?.title;

  const appliedCount = filteredProposals.filter(p => p.status === "applied").length;
  const flowStep = appliedCount > 0 ? 4
    : filteredProposals.length > 0 ? 3
    : analysis ? 2
    : currentSelection ? 1
    : 0;

  const handleContentTabChange = (tab: string) => {
    const newTab = tab as ContentTabType;
    setContentTab(newTab);
    clearSelection();
    setActionTab("analysis");
    // Auto-fetch data for the new tab if empty
    if (newTab === "categories" && categories.length === 0) fetchCategories();
    else if (newTab === "pages" && pages.length === 0) fetchPages();
    else if (newTab === "blog" && blogPosts.length === 0) fetchBlogPosts();
  };

  const handleOptimize = async () => {
    setOptimizing(true);
    const kw = targetKeyword.trim() || undefined;
    if (selectedProduct) {
      await generateProductProposals(selectedProduct.id, {
        target_keyword: kw,
        recommended_actions: analysis?.recommended_actions,
      });
    }
    else if (selectedCategory) await generateCategoryProposals(selectedCategory.id, kw);
    else if (selectedPage) await generatePageProposals(selectedPage.id, kw);
    else if (selectedBlogPost?.blog_id) await generateBlogProposals(selectedBlogPost.blog_id, selectedBlogPost.id, kw);
    setOptimizing(false);
    setActionTab("proposals");
  };

  const handleApproveAll = async () => {
    const ids = pendingProposals.map(p => p.id);
    if (ids.length > 0) await approveProposals(ids);
  };

  const handleRejectAll = async () => {
    const ids = pendingProposals.map(p => p.id);
    if (ids.length > 0) await rejectProposals(ids);
  };

  const handleApplyChanges = async () => {
    if (approvedProposals.length > 0) await applyProposals();
  };

  if (!connection.connected) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-primary mr-3" />
        <span className="text-muted-foreground">Conectando à loja...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Stepper currentStep={flowStep} loading={loading || optimizing} />

      {/* Content type tabs */}
      <Tabs value={contentTab} onValueChange={handleContentTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="products" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            <span className="hidden sm:inline">Produtos</span>
            {products.length > 0 && <Badge variant="secondary" className="ml-1">{products.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="categories" className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4" />
            <span className="hidden sm:inline">Categorias</span>
            {categories.length > 0 && <Badge variant="secondary" className="ml-1">{categories.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="pages" className="flex items-center gap-2">
            <FileEdit className="w-4 h-4" />
            <span className="hidden sm:inline">Páginas</span>
            {pages.length > 0 && <Badge variant="secondary" className="ml-1">{pages.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="blog" className="flex items-center gap-2">
            <Newspaper className="w-4 h-4" />
            <span className="hidden sm:inline">Blog</span>
            {blogPosts.length > 0 && <Badge variant="secondary" className="ml-1">{blogPosts.length}</Badge>}
          </TabsTrigger>
        </TabsList>

        <div className="mt-4 grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-5">
          {/* ── Left Panel: Item list ── */}
          <div>
            <TabsContent value="products" className="mt-0">
              <ItemList
                icon={<Package className="w-4 h-4" />}
                title="Produtos"
                count={products.length}
                onRefresh={fetchProducts}
                loading={loading}
                emptyIcon={<Package className="w-10 h-10 text-muted-foreground/30" />}
              >
                {products.map((product) => (
                  <ItemButton
                    key={product.id}
                    selected={selectedProduct?.id === product.id}
                    onClick={() => { selectProduct(product); setActionTab("analysis"); }}
                    image={product.images?.[0]?.src}
                    title={product.name}
                    subtitle={product.brand || "Sem marca"}
                  />
                ))}
              </ItemList>
            </TabsContent>

            <TabsContent value="categories" className="mt-0">
              <ItemList
                icon={<FolderOpen className="w-4 h-4" />}
                title="Categorias"
                count={categories.length}
                onRefresh={fetchCategories}
                loading={loading}
                emptyIcon={<FolderOpen className="w-10 h-10 text-muted-foreground/30" />}
              >
                {categories.map((cat) => (
                  <ItemButton
                    key={cat.id}
                    selected={selectedCategory?.id === cat.id}
                    onClick={() => { selectCategory(cat); setActionTab("analysis"); }}
                    title={cat.name}
                    subtitle={`${cat.products_count || 0} produto(s)`}
                  />
                ))}
              </ItemList>
            </TabsContent>

            <TabsContent value="pages" className="mt-0">
              <ItemList
                icon={<FileEdit className="w-4 h-4" />}
                title="Páginas"
                count={pages.length}
                onRefresh={fetchPages}
                loading={loading}
                emptyIcon={<FileEdit className="w-10 h-10 text-muted-foreground/30" />}
              >
                {pages.map((page) => (
                  <ItemButton
                    key={page.id}
                    selected={selectedPage?.id === page.id}
                    onClick={() => { selectPage(page); setActionTab("analysis"); }}
                    title={page.title}
                    subtitle={`/${page.handle}`}
                  />
                ))}
              </ItemList>
            </TabsContent>

            <TabsContent value="blog" className="mt-0">
              {blogMessage ? (
                <div className="flex flex-col items-center justify-center py-10 px-4 text-center gap-3">
                  <Newspaper className="w-10 h-10 text-muted-foreground/30" />
                  <p className="text-sm text-muted-foreground">{blogMessage}</p>
                </div>
              ) : (
              <ItemList
                icon={<Newspaper className="w-4 h-4" />}
                title="Blog Posts"
                count={blogPosts.length}
                onRefresh={fetchBlogPosts}
                loading={loading}
                emptyIcon={<Newspaper className="w-10 h-10 text-muted-foreground/30" />}
              >
                {blogPosts.map((post) => (
                  <ItemButton
                    key={post.id}
                    selected={selectedBlogPost?.id === post.id}
                    onClick={() => { selectBlogPost(post); setActionTab("analysis"); }}
                    title={post.title}
                    subtitle={post.author || "Sem autor"}
                  />
                ))}
              </ItemList>
              )}
            </TabsContent>
          </div>

          {/* Right Panel */}
          <div className="flex flex-col gap-4">
            {/* Action tab switcher */}
            <div className="flex gap-2 border-b pb-2 flex-wrap">
              <Button variant={actionTab === "analysis" ? "default" : "ghost"} size="sm" onClick={() => setActionTab("analysis")}>
                <FileText className="w-4 h-4 mr-2" />
                Analise
              </Button>
              <Button
                variant={actionTab === "proposals" ? "default" : "ghost"}
                size="sm"
                onClick={() => filteredProposals.length > 0 && setActionTab("proposals")}
                disabled={filteredProposals.length === 0}
                className={filteredProposals.length === 0 ? "opacity-50" : ""}
              >
                {filteredProposals.length === 0 ? <Lock className="w-4 h-4 mr-2 text-muted-foreground" /> : <Sparkles className="w-4 h-4 mr-2" />}
                Propostas
                {pendingProposals.length > 0 && <Badge className="ml-2 h-5 px-1.5" variant="secondary">{pendingProposals.length}</Badge>}
              </Button>
              <Button
                variant={actionTab === "rollback" ? "default" : "ghost"}
                size="sm"
                onClick={() => setActionTab("rollback")}
              >
                <History className="w-4 h-4 mr-2" />
                Rollback
                {rollbacks.filter(r => !r.rolled_back).length > 0 && (
                  <Badge className="ml-2 h-5 px-1.5" variant="secondary">
                    {rollbacks.filter(r => !r.rolled_back).length}
                  </Badge>
                )}
              </Button>
            </div>

            {actionTab === "analysis" && (
              <AnalysisPanel
                currentSelection={currentSelection}
                currentName={currentName}
                contentTab={contentTab}
                selectedProduct={selectedProduct}
                selectedCategory={selectedCategory}
                selectedPage={selectedPage}
                selectedBlogPost={selectedBlogPost}
                analysis={analysis}
                loading={loading}
                optimizing={optimizing}
                onOptimize={handleOptimize}
                targetKeyword={targetKeyword}
                onKeywordChange={setTargetKeyword}
              />
            )}

            {actionTab === "proposals" && (
              <ProposalsPanel
                proposals={filteredProposals}
                pendingProposals={pendingProposals}
                approvedProposals={approvedProposals}
                loading={loading}
                onApproveAll={handleApproveAll}
                onRejectAll={handleRejectAll}
                onApplyChanges={handleApplyChanges}
                onApprove={(id) => approveProposals([id])}
                onReject={(id) => rejectProposals([id])}
              />
            )}

            {actionTab === "rollback" && (
              <RollbackHistory
                records={rollbacks}
                loading={loading}
                onRollbackSingle={(rec) => rollback("single", rec as NuvemshopRollback)}
                onRollbackAll={() => rollback("all")}
              />
            )}
          </div>
        </div>
      </Tabs>

      {toast && <Toast toast={{ ...toast, type: toast.type === "warning" ? "error" : toast.type }} />}
    </div>
  );
}

/* ═══ Sub-components ═══ */

function ItemList({ icon, title, count, onRefresh, loading, emptyIcon, children }: {
  icon: React.ReactNode; title: string; count: number;
  onRefresh: () => void; loading: boolean; emptyIcon: React.ReactNode;
  children: React.ReactNode;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : !!children;
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">{icon}{title}</CardTitle>
          <Button size="sm" variant="outline" onClick={onRefresh} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
        </div>
        <CardDescription className="text-xs">{count} item(ns) carregado(s)</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[55vh]">
          {!hasChildren ? (
            <div className="p-6 text-center">
              {emptyIcon}
              <p className="text-sm text-muted-foreground mt-2">Clique em atualizar para carregar</p>
            </div>
          ) : (
            <div className="divide-y">{children}</div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function ItemButton({ selected, onClick, image, title, subtitle }: {
  selected: boolean; onClick: () => void; image?: string; title: string; subtitle: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 hover:bg-muted/50 transition-colors flex items-center gap-3 ${
        selected ? "bg-primary/10 border-l-3 border-primary" : ""
      }`}
    >
      {image ? (
        <img src={image} alt="" className="w-10 h-10 rounded object-cover" />
      ) : (
        <div className="w-10 h-10 rounded bg-muted flex items-center justify-center">
          <Image className="w-4 h-4 text-muted-foreground" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{title}</p>
        <p className="text-xs text-muted-foreground truncate">{subtitle}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-muted-foreground" />
    </button>
  );
}

function AnalysisPanel({ currentSelection, currentName, contentTab, selectedProduct, selectedCategory, selectedPage, selectedBlogPost, analysis, loading, optimizing, onOptimize, targetKeyword, onKeywordChange }: {
  currentSelection: any; currentName: string | undefined; contentTab: ContentTabType;
  selectedProduct: any; selectedCategory: any; selectedPage: any; selectedBlogPost: any;
  analysis: any; loading: boolean; optimizing: boolean; onOptimize: () => void;
  targetKeyword: string; onKeywordChange: (v: string) => void;
}) {
  if (!currentSelection) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-12 text-center">
          <Search className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-muted-foreground">Selecione um item na lista à esquerda para analisar</p>
        </CardContent>
      </Card>
    );
  }

  const iconMap: Record<ContentTabType, React.ReactNode> = {
    products: <Package className="w-8 h-8 text-muted-foreground" />,
    categories: <FolderOpen className="w-8 h-8 text-muted-foreground" />,
    pages: <FileText className="w-8 h-8 text-muted-foreground" />,
    blog: <Newspaper className="w-8 h-8 text-muted-foreground" />,
  };

  const subtitleText = selectedProduct ? (selectedProduct.brand || "Sem marca")
    : selectedCategory ? `${selectedCategory.products_count || 0} produto(s)`
    : selectedPage ? `/${selectedPage.handle}`
    : selectedBlogPost ? (selectedBlogPost.author || "Sem autor")
    : "";

  return (
    <div className="space-y-4">
      {/* Item card */}
      <Card>
        <CardHeader>
          <div className="flex items-start gap-4">
            {selectedProduct?.images?.[0] ? (
              <img src={selectedProduct.images[0].src} alt="" className="w-16 h-16 rounded-lg object-cover" />
            ) : (
              <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center">{iconMap[contentTab]}</div>
            )}
            <div className="flex-1 min-w-0">
              <CardTitle className="truncate">{currentName}</CardTitle>
              <CardDescription className="mt-1">{subtitleText}</CardDescription>
              <Badge variant="outline" className="mt-2 text-xs">
                {selectedProduct?.handle || selectedCategory?.handle || selectedPage?.handle || selectedBlogPost?.handle}
              </Badge>
            </div>
            <div className="flex flex-col items-end gap-2">
              <input
                type="text"
                placeholder="Keyword alvo (opcional)"
                value={targetKeyword}
                onChange={e => onKeywordChange(e.target.value)}
                className="w-48 px-3 py-1.5 text-xs border rounded-md bg-background"
              />
              <Button onClick={onOptimize} disabled={loading || optimizing || !analysis}>
                {optimizing ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Gerando...</> : <><Sparkles className="w-4 h-4 mr-2" />Otimizar com IA</>}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Loading analysis */}
      {loading && !analysis && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary mr-3" />
          <span className="text-muted-foreground">Analisando SEO...</span>
        </div>
      )}

      {/* Analysis results */}
      {analysis && (
        <DiagnosisPanel
          analysis={analysis}
          issueFallbackLabel={(issue) => ISSUE_MESSAGES[issue.type || ""] || issue.message || issue.type || ""}
        />
      )}
    </div>
  );
}

function ProposalsPanel({ proposals, pendingProposals, approvedProposals, loading, onApproveAll, onRejectAll, onApplyChanges, onApprove, onReject }: {
  proposals: NuvemshopProposal[]; pendingProposals: NuvemshopProposal[]; approvedProposals: NuvemshopProposal[];
  loading: boolean; onApproveAll: () => void; onRejectAll: () => void; onApplyChanges: () => void;
  onApprove: (id: string) => void; onReject: (id: string) => void;
}) {
  if (proposals.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Sparkles className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-muted-foreground">Nenhuma proposta gerada ainda</p>
          <p className="text-sm text-muted-foreground/70 mt-1">Selecione um item e clique em "Otimizar com IA"</p>
        </CardContent>
      </Card>
    );
  }

  // Group proposals by optimization_type or field
  const grouped: Record<string, NuvemshopProposal[]> = {};
  for (const p of proposals) {
    const key = p.optimization_type || p.field_name;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(p);
  }

  return (
    <div className="space-y-3">
      {/* Batch actions */}
      {pendingProposals.length > 0 && (
        <Card>
          <CardContent className="py-3 flex items-center justify-between flex-wrap gap-2">
            <span className="text-sm"><strong>{pendingProposals.length}</strong> proposta(s) pendente(s)</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={onRejectAll} disabled={loading}>
                <X className="w-4 h-4 mr-1" />Rejeitar todas
              </Button>
              <Button size="sm" onClick={onApproveAll} disabled={loading}>
                <Check className="w-4 h-4 mr-1" />Aprovar todas
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {approvedProposals.length > 0 && (
        <Card className="border-green-500/30 bg-green-500/5">
          <CardContent className="py-3 flex items-center justify-between flex-wrap gap-2">
            <span className="text-sm text-green-600"><strong>{approvedProposals.length}</strong> aprovada(s) pronta(s) para aplicar</span>
            <Button size="sm" onClick={onApplyChanges} disabled={loading} className="bg-green-600 hover:bg-green-500">
              <CheckCircle className="w-4 h-4 mr-1" />Aplicar na Nuvemshop
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Grouped proposal cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(grouped).map(([key, groupProposals]) => {
          const groupPending = groupProposals.filter(p => p.status === "pending");
          const hasApplied = groupProposals.some(p => p.status === "applied");
          const hasApproved = groupProposals.some(p => p.status === "approved");
          const first = groupProposals[0];
          const title = OPTIMIZATION_TITLES[key] || OPTIMIZATION_TITLES[first.field_name] || `Otimização: ${FIELD_LABELS[first.field_name] || first.field_name}`;

          return (
            <Card key={key} className={
              hasApplied ? "border-blue-500/30 bg-blue-500/5" :
              hasApproved ? "border-green-500/30" : ""
            }>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">{title}</CardTitle>
                  <Badge className={
                    hasApplied ? "bg-blue-600" :
                    hasApproved ? "bg-green-600" :
                    groupPending.length > 0 ? "bg-yellow-600/80 text-white" : ""
                  }>
                    {hasApplied ? "Aplicado" : hasApproved ? "Aprovado" : "Pendente"}
                  </Badge>
                </div>
                {first.priority && (
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    <Badge variant="outline" className={`text-[10px] h-5 ${first.priority === 'high' ? 'border-red-400 text-red-600' : first.priority === 'medium' ? 'border-yellow-400 text-yellow-700' : 'border-gray-300 text-gray-500'}`}>
                      {first.priority === 'high' ? 'Alta' : first.priority === 'medium' ? 'Média' : 'Baixa'}
                    </Badge>
                    {first.impact && (
                      <Badge variant="outline" className="text-[10px] h-5 border-purple-300 text-purple-600">
                        {first.impact === 'ranking' ? ' Ranking' : first.impact === 'ctr' ? ' CTR' : first.impact === 'conversao' ? ' Conversão' : ' Visibilidade'}
                      </Badge>
                    )}
                    {first.effort && (
                      <Badge variant="outline" className="text-[10px] h-5 border-cyan-300 text-cyan-600">
                        Esforço: {first.effort === 'low' ? 'Baixo' : first.effort === 'medium' ? 'Médio' : 'Alto'}
                      </Badge>
                    )}
                  </div>
                )}
                {first.reasoning && (
                  <CardDescription className="text-xs italic mt-1">{first.reasoning}</CardDescription>
                )}
                {/* Exibe selos de transparência da IA */}
                {first.transparencia?.semantica?.tag && (
                  <div className="flex items-center gap-1.5 mt-2 text-xs font-medium text-orange-400">
                    <span>{first.transparencia.semantica.tag}</span>
                  </div>
                )}
                {first.transparencia?.atributos?.tag && (
                  <div className={`flex items-center gap-1.5 mt-1 text-xs font-medium ${
                    first.transparencia.atributos.status === "atributos_identificados"
                      ? "text-green-400"
                      : "text-muted-foreground"
                  }`}>
                    <span>{first.transparencia.atributos.tag}</span>
                    {first.transparencia.atributos.atributos?.length > 0 && (
                      <span className="text-muted-foreground">
                        ({first.transparencia.atributos.atributos.join(", ")})
                      </span>
                    )}
                  </div>
                )}
                {/* Motivos Técnicos Aplicados (Seção 3/6 da spec) */}
                {(() => {
                  const motivos: string[] = [];
                  const attr = first.transparencia?.atributos;
                  const sem = first.transparencia?.semantica;
                  if (attr?.status === "atributos_identificados") {
                    motivos.push("Atributos descritivos inclusos no título (atendimento a cauda longa)");
                  }
                  if (sem && sem.total >= 2) {
                    motivos.push("Palavras-chave estratégicas incorporadas (melhor cobertura semântica)");
                  } else if (sem && sem.total === 1) {
                    motivos.push("Palavra-chave estratégica incorporada (ganho de relevância)");
                  }
                  if (motivos.length === 0) return null;
                  return (
                    <div className="mt-2">
                      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                        Motivos Técnicos Aplicados
                      </p>
                      <ul className="mt-1 space-y-0.5">
                        {motivos.map((m, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                            <span className="text-green-400 leading-tight">✓</span>
                            <span>{m}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })()}
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Current value */}
                <div className="p-2.5 bg-green-500/10 rounded-lg">
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">Atual</p>
                  <p className="text-xs text-green-600 break-words whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {first.original_value || "(vazio)"}
                  </p>
                </div>

                {/* Individual proposals */}
                {groupProposals.map((proposal, idx) => (
                  <div key={proposal.id} className={`rounded-lg border ${
                    proposal.status === "approved" ? "border-green-500/40 bg-green-500/5" :
                    proposal.status === "applied" ? "border-blue-500/40 bg-blue-500/5" :
                    "border-border"
                  }`}>
                    <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
                      <span className="text-xs font-semibold">Proposta {idx + 1}</span>
                      {proposal.status === "pending" && (
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" className="h-6 px-2 text-red-500 hover:bg-red-500/10 hover:text-red-600" onClick={() => onReject(proposal.id)} disabled={loading}>
                            <X className="w-3.5 h-3.5 mr-1" />Rejeitar
                          </Button>
                          <Button size="sm" variant="ghost" className="h-6 px-2 text-green-500 hover:bg-green-500/10 hover:text-green-600" onClick={() => onApprove(proposal.id)} disabled={loading}>
                            <Check className="w-3.5 h-3.5 mr-1" />Aprovar
                          </Button>
                        </div>
                      )}
                      {proposal.status === "approved" && (
                        <Badge variant="outline" className="text-green-600 border-green-500/40 text-[10px] h-5">Aprovado</Badge>
                      )}
                      {proposal.status === "applied" && (
                        <Badge variant="outline" className="text-blue-600 border-blue-500/40 text-[10px] h-5">Aplicado</Badge>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="text-xs break-words whitespace-pre-wrap max-h-32 overflow-y-auto">
                        {proposal.proposed_value}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
