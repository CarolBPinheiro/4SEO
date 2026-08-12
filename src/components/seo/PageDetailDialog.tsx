import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  ExternalLink, 
  FileText, 
  Hash, 
  Image, 
  Link2, 
  AlertTriangle,
  CheckCircle,
  XCircle 
} from "lucide-react";
import type { Page } from "./PagesTable";

// Labels e descrições para issues (em português)
const ISSUE_INFO: Record<string, { label: string; description: string; fix: string }> = {
  missing_title: { 
    label: "Título da página não definido", 
    description: "A página não possui uma tag <title> - essencial para aparecer nos resultados do Google",
    fix: "Adicione um título com 30-60 caracteres que descreva o conteúdo da página e inclua palavras-chave importantes"
  },
  title_length: { 
    label: "Tamanho do título inadequado", 
    description: "O título da página está muito curto (menos de 30 caracteres) ou muito longo (mais de 60 caracteres)",
    fix: "Ajuste o título para ter entre 30 e 60 caracteres - assim ele aparece completo no Google"
  },
  missing_meta_description: { 
    label: "Meta descrição não definida", 
    description: "A página não possui uma meta descrição - esse texto aparece nos resultados do Google",
    fix: "Adicione uma descrição atraente com 120 a 160 caracteres que convença o usuário a clicar"
  },
  meta_description_length: { 
    label: "Tamanho da meta descrição inadequado", 
    description: "A meta descrição está muito curta ou muito longa e pode ser cortada no Google",
    fix: "Ajuste a descrição para ter entre 120 e 160 caracteres"
  },
  missing_h1: { 
    label: "Título principal (H1) não encontrado", 
    description: "A página não possui um título H1, que é essencial para o Google entender o tema da página",
    fix: "Adicione um único título H1 que descreva claramente o conteúdo principal"
  },
  multiple_h1: { 
    label: "Múltiplos títulos H1 na página", 
    description: "Existem vários títulos H1 na página, o que pode confundir os buscadores",
    fix: "Mantenha apenas um H1 por página e use H2/H3 para subtítulos"
  },
  missing_h2: { 
    label: "Subtítulos (H2) não encontrados", 
    description: "A página não possui subtítulos H2 para organizar o conteúdo",
    fix: "Adicione subtítulos H2 para dividir o conteúdo em seções e facilitar a leitura"
  },
  missing_canonical: { 
    label: "Link canônico não definido", 
    description: "A página não indica qual é a URL principal (canônica), podendo ser penalizada por conteúdo duplicado",
    fix: "Adicione a tag: <link rel='canonical' href='URL_PRINCIPAL_DA_PÁGINA'>"
  },
  noindex_detected: { 
    label: "Página bloqueada para indexação", 
    description: "A página possui uma tag 'noindex' e NÃO aparecerá nos resultados do Google",
    fix: "Remova a meta tag 'noindex' se desejar que a página seja encontrada no Google"
  },
  missing_img_alt: { 
    label: "Imagens sem descrição alternativa", 
    description: "Algumas imagens não possuem texto alternativo (alt), prejudicando acessibilidade e SEO",
    fix: "Adicione descrições claras no atributo alt de cada imagem (ex: alt='Camiseta azul masculina')"
  },
  few_internal_links: { 
    label: "Poucos links internos", 
    description: "A página possui poucos links para outras páginas do seu site",
    fix: "Adicione links relevantes para outras páginas, ajudando o Google a descobrir mais conteúdo"
  },
  missing_og_tags: { 
    label: "Tags de redes sociais ausentes", 
    description: "Tags Open Graph (og:title e og:description) não encontradas",
    fix: "Adicione meta tags Open Graph para melhorar a aparência ao compartilhar nas redes sociais"
  },
  missing_og_image: { 
    label: "Imagem para compartilhamento não definida", 
    description: "Não há uma imagem definida para aparecer quando a página for compartilhada",
    fix: "Adicione a tag og:image com uma imagem atraente (1200x630px recomendado)"
  },
  missing_schema: { 
    label: "Dados estruturados não encontrados", 
    description: "A página não possui dados estruturados (Schema.org) que ajudam o Google a entender melhor o conteúdo",
    fix: "Adicione marcação Schema.org (JSON-LD) para produtos, artigos, FAQ, etc. e ganhe destaque nos resultados"
  },
};

const getScoreColor = (score: number | undefined) => {
  if (score === undefined || score === null) return "text-muted-foreground";
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
};

const getScoreBg = (score: number | undefined) => {
  if (score === undefined || score === null) return "bg-muted";
  if (score >= 80) return "bg-green-500/10 border-green-500/30";
  if (score >= 60) return "bg-yellow-500/10 border-yellow-500/30";
  if (score >= 40) return "bg-orange-500/10 border-orange-500/30";
  return "bg-red-500/10 border-red-500/30";
};

interface PageDetailDialogProps {
  page: Page | null;
  open: boolean;
  onClose: () => void;
}

const PageDetailDialog = ({ page, open, onClose }: PageDetailDialogProps) => {
  if (!page) return null;

  const issues = Object.entries(page.issues || {}).filter(([_, value]) => value === true);
  const score = page.seo_score ?? page.total_score ?? 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            Detalhes da Página
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* URL e Score */}
          <div className="flex items-start justify-between gap-4 p-4 rounded-lg bg-muted/30">
            <div className="min-w-0 flex-1">
              <a 
                href={page.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sm font-medium text-primary hover:underline flex items-center gap-1"
              >
                {page.url.replace(/^https?:\/\//, '')}
                <ExternalLink className="w-3 h-3" />
              </a>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className={page.status_code === 200 ? "text-green-500" : "text-red-500"}>
                  HTTP {page.status_code}
                </Badge>
              </div>
            </div>
            <div className={`flex flex-col items-center p-3 rounded-xl border ${getScoreBg(score)}`}>
              <span className={`text-3xl font-bold ${getScoreColor(score)}`}>{score}</span>
              <span className="text-xs text-muted-foreground">Score SEO</span>
            </div>
          </div>

          {/* Informações Básicas */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <Hash className="w-4 h-4" />
              Informações SEO
            </h4>
            
            <div className="grid gap-3">
              <div className="p-3 rounded-lg border bg-card">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-muted-foreground">Title</span>
                  {page.title ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500" />
                  )}
                </div>
                <p className="text-sm">{page.title || <span className="text-muted-foreground italic">Não definido</span>}</p>
                {page.title && (
                  <p className="text-xs text-muted-foreground mt-1">{page.title.length} caracteres</p>
                )}
              </div>

              <div className="p-3 rounded-lg border bg-card">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-muted-foreground">Meta Description</span>
                  {page.meta_description ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500" />
                  )}
                </div>
                <p className="text-sm">{page.meta_description || <span className="text-muted-foreground italic">Não definido</span>}</p>
                {page.meta_description && (
                  <p className="text-xs text-muted-foreground mt-1">{page.meta_description.length} caracteres</p>
                )}
              </div>

              <div className="p-3 rounded-lg border bg-card">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-muted-foreground">H1</span>
                  {page.h1 ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500" />
                  )}
                </div>
                <p className="text-sm">{page.h1 || <span className="text-muted-foreground italic">Não definido</span>}</p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Issues */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              Problemas Detectados ({issues.length})
            </h4>
            
            {issues.length === 0 ? (
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-center">
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-green-500 font-medium">Nenhum problema encontrado!</p>
                <p className="text-xs text-muted-foreground">Esta página está otimizada.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {issues.map(([code]) => {
                  const info = ISSUE_INFO[code] || { label: code, description: "", fix: "" };
                  return (
                    <div key={code} className="p-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors">
                      <div className="flex items-start gap-3">
                        <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium">{info.label}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{info.description}</p>
                          <p className="text-xs text-primary mt-2 flex items-start gap-1">
                            <span className="shrink-0">Dica:</span>
                            <span>{info.fix}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PageDetailDialog;
