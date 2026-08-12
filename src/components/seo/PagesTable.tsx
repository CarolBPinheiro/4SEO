import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { FileText, ExternalLink, Trash2, Eye } from "lucide-react";
import PageDetailDialog from "./PageDetailDialog";

export interface Page {
  id: string;
  url: string;
  status_code: number;
  title?: string;
  meta_description?: string;
  h1?: string;
  issues: Record<string, boolean | number>;
  seo_score?: number;
  geo_score?: number;
  total_score?: number;
}

// Labels amigáveis para issues
const ISSUE_LABELS: Record<string, string> = {
  missing_title: "Título da página não definido",
  title_length: "Tamanho do título inadequado (ideal: 30-60 caracteres)",
  missing_meta_description: "Meta descrição não definida",
  meta_description_length: "Tamanho da meta descrição inadequado (ideal: 120-160 caracteres)",
  missing_h1: "Título principal (H1) não encontrado",
  multiple_h1: "Múltiplos títulos H1 na mesma página",
  missing_h2: "Subtítulos (H2) não encontrados - melhore a estrutura",
  missing_canonical: "Link canônico não definido",
  noindex_detected: "Página bloqueada para indexação (noindex)",
  missing_img_alt: "Imagens sem descrição alternativa",
  few_internal_links: "Poucos links internos",
  missing_og_tags: "Tags de redes sociais (Open Graph) ausentes",
  missing_og_image: "Imagem para compartilhamento não definida",
  missing_schema: "Dados estruturados (Schema.org) não encontrados",
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

const getStatusColor = (code: number) => {
  if (code >= 200 && code < 300) return "text-green-500 bg-green-500/10";
  if (code >= 300 && code < 400) return "text-yellow-500 bg-yellow-500/10";
  return "text-red-500 bg-red-500/10";
};

interface PagesTableProps {
  pages: Page[];
  loading?: boolean;
  onDeletePage?: (pageId: string) => void;
}

const PagesTable = ({ pages, loading, onDeletePage }: PagesTableProps) => {
  const [selectedPage, setSelectedPage] = useState<Page | null>(null);

  return (
    <>
    <div className="card-gradient rounded-2xl border border-border p-5 shadow-soft flex-1 min-h-[200px]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Páginas Escaneadas</h3>
            <p className="text-xs text-muted-foreground">
              {pages.length} página(s) encontrada(s)
            </p>
          </div>
        </div>
      </div>

      {pages.length === 0 ? (
        <div className="text-center py-8">
          <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground mb-1">
            Nenhuma página carregada ainda.
          </p>
          <p className="text-xs text-muted-foreground/70">
            Rode uma varredura para ver os resultados.
          </p>
        </div>
      ) : (
        <div className="max-h-[360px] overflow-auto scrollbar-thin rounded-lg border border-border/50">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent bg-muted/30">
                <TableHead className="text-muted-foreground font-medium text-xs">URL</TableHead>
                <TableHead className="text-muted-foreground font-medium text-center text-xs w-[80px]">Score</TableHead>
                <TableHead className="text-muted-foreground font-medium text-center text-xs w-[60px]">Status</TableHead>
                <TableHead className="text-muted-foreground font-medium text-xs hidden lg:table-cell">Título</TableHead>
                <TableHead className="text-muted-foreground font-medium text-xs">Problemas</TableHead>
                {onDeletePage && (
                  <TableHead className="text-muted-foreground font-medium text-center text-xs w-[50px]"></TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {pages.map((page) => (
                <TableRow 
                  key={page.id} 
                  className="border-border/50 hover:bg-muted/20 group cursor-pointer"
                  onClick={() => setSelectedPage(page)}
                >
                  <TableCell className="max-w-[200px] py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedPage(page); }}
                        className="text-sm truncate hover:text-primary transition-colors flex items-center gap-1 group/link text-left"
                      >
                        <Eye className="w-3 h-3 opacity-0 group-hover:opacity-100 shrink-0 text-primary" />
                        <span className="truncate">{page.url.replace(/^https?:\/\//, '')}</span>
                      </button>
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="opacity-0 group-hover:opacity-100 shrink-0 hover:text-primary"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </TableCell>
                  <TableCell className="text-center py-3">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <span
                            className={`inline-flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold border ${getScoreBg(page.total_score)} ${getScoreColor(page.total_score)}`}
                          >
                            {page.total_score ?? "-"}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="bg-popover border-border">
                          <div className="text-xs space-y-1.5 p-1">
                            <div className="flex justify-between gap-4">
                              <span className="text-muted-foreground">SEO (70%):</span>
                              <span className={`font-medium ${getScoreColor(page.seo_score)}`}>{page.seo_score ?? "-"}</span>
                            </div>
                            <div className="flex justify-between gap-4">
                              <span className="text-muted-foreground">GEO (30%):</span>
                              <span className={`font-medium ${getScoreColor(page.geo_score)}`}>{page.geo_score ?? "-"}</span>
                            </div>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell className="text-center py-3">
                    <span className={`text-xs font-medium px-2 py-1 rounded-full ${getStatusColor(page.status_code)}`}>
                      {page.status_code}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs py-3 hidden lg:table-cell max-w-[180px]">
                    {page.title ? (
                      <span className="truncate block" title={page.title}>{page.title}</span>
                    ) : (
                      <span className="text-muted-foreground/60 italic">sem título</span>
                    )}
                  </TableCell>
                  <TableCell className="py-3">
                    {Object.keys(page.issues || {}).filter(k => page.issues[k] === true).length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(page.issues || {}).filter(k => page.issues[k] === true).slice(0, 3).map((issue) => (
                          <TooltipProvider key={issue}>
                            <Tooltip>
                              <TooltipTrigger>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium cursor-help">
                                  {ISSUE_LABELS[issue] || issue}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent className="bg-popover border-border">
                                <p className="text-xs">{issue}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ))}
                        {Object.keys(page.issues || {}).filter(k => page.issues[k] === true).length > 3 && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                            +{Object.keys(page.issues).filter(k => page.issues[k] === true).length - 3}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-green-500 font-medium flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                        OK
                      </span>
                    )}
                  </TableCell>
                  {onDeletePage && (
                    <TableCell className="text-center py-3">
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                            disabled={loading}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Remover página?</AlertDialogTitle>
                            <AlertDialogDescription>
                              A página será removida da lista de análise. Você pode escaneá-la novamente a qualquer momento.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => onDeletePage(page.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Remover
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>

    <PageDetailDialog 
      page={selectedPage} 
      open={!!selectedPage} 
      onClose={() => setSelectedPage(null)} 
    />
    </>
  );
};

export default PagesTable;
