import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  TrendingUp,
  BarChart3
} from "lucide-react";

export interface ScanResult {
  pages_scanned: number;
  pages_found: number;
  tasks_created: number;
  score: number;
  duration_seconds: number;
  issues_summary: Record<string, number>;
}

// Labels amigáveis para cada tipo de issue (em português)
const ISSUE_LABELS: Record<string, { label: string; description: string; priority: "critical" | "high" | "medium" | "low" }> = {
  missing_title: { 
    label: "Título da página não definido", 
    description: "A página não possui uma tag <title> - essencial para o Google",
    priority: "critical"
  },
  title_length: { 
    label: "Tamanho do título inadequado", 
    description: "O título da página deve ter entre 30 e 60 caracteres para aparecer corretamente no Google",
    priority: "medium"
  },
  missing_meta_description: { 
    label: "Meta descrição não definida", 
    description: "A meta descrição aparece nos resultados do Google e ajuda a atrair cliques",
    priority: "high"
  },
  meta_description_length: { 
    label: "Tamanho da meta descrição inadequado", 
    description: "A meta descrição deve ter entre 120 e 160 caracteres para não ser cortada no Google",
    priority: "medium"
  },
  missing_h1: { 
    label: "Título principal (H1) não encontrado", 
    description: "Toda página precisa de um título principal (H1) para o Google entender o conteúdo",
    priority: "high"
  },
  multiple_h1: { 
    label: "Múltiplos títulos H1 na página", 
    description: "Use apenas um título H1 por página para não confundir os buscadores",
    priority: "medium"
  },
  missing_h2: { 
    label: "Subtítulos (H2) não encontrados", 
    description: "Adicione subtítulos H2 para organizar o conteúdo e facilitar a leitura",
    priority: "low"
  },
  missing_canonical: { 
    label: "Link canônico não definido", 
    description: "O link canônico evita penalizações por conteúdo duplicado",
    priority: "medium"
  },
  noindex_detected: { 
    label: "Página bloqueada para indexação", 
    description: "Esta página não aparecerá no Google devido à tag noindex",
    priority: "critical"
  },
  missing_img_alt: { 
    label: "Imagens sem descrição alternativa", 
    description: "O texto alternativo (alt) ajuda na acessibilidade e no SEO de imagens",
    priority: "high"
  },
  few_internal_links: { 
    label: "Poucos links internos", 
    description: "Links internos ajudam o Google a descobrir outras páginas do seu site",
    priority: "low"
  },
  missing_og_tags: { 
    label: "Tags de redes sociais ausentes", 
    description: "Tags Open Graph melhoram a aparência ao compartilhar nas redes sociais",
    priority: "medium"
  },
  missing_og_image: { 
    label: "Imagem para compartilhamento não definida", 
    description: "Defina uma imagem que aparecerá ao compartilhar a página nas redes sociais",
    priority: "low"
  },
  missing_schema: { 
    label: "Dados estruturados não encontrados", 
    description: "Dados estruturados (Schema.org) podem gerar rich snippets nos resultados do Google",
    priority: "medium"
  },
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case "critical": return "bg-red-500/20 text-red-400 border-red-500/30";
    case "high": return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "medium": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "low": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    default: return "bg-muted text-muted-foreground";
  }
};

const getScoreColor = (score: number) => {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
};

const getScoreLabel = (score: number) => {
  if (score >= 90) return "Excelente";
  if (score >= 80) return "Muito Bom";
  if (score >= 70) return "Bom";
  if (score >= 60) return "Regular";
  if (score >= 40) return "Precisa Melhorar";
  return "Crítico";
};

interface ScanSummaryProps {
  result: ScanResult | null;
  loading?: boolean;
}

const ScanSummary = ({ result, loading }: ScanSummaryProps) => {
  if (loading) {
    return (
      <Card className="card-gradient border-border">
        <CardContent className="p-6">
          <div className="flex items-center justify-center gap-3 py-8">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <div>
              <p className="text-sm font-medium">Analisando site...</p>
              <p className="text-xs text-muted-foreground">Isso pode levar alguns segundos</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return null;
  }

  const sortedIssues = Object.entries(result.issues_summary)
    .map(([code, count]) => ({
      code,
      count,
      ...ISSUE_LABELS[code] || { label: code, description: "", priority: "low" as const }
    }))
    .sort((a, b) => {
      const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });

  const totalIssues = Object.values(result.issues_summary).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      {/* Score Principal */}
      <Card className="card-gradient border-border overflow-hidden">
        <CardContent className="p-0">
          <div className="flex flex-col md:flex-row">
            {/* Score Circle */}
            <div className="flex-shrink-0 p-6 flex items-center justify-center bg-gradient-to-br from-primary/10 to-transparent">
              <div className="relative">
                <svg className="w-32 h-32 transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    className="text-muted/30"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${(result.score / 100) * 351.86} 351.86`}
                    className={getScoreColor(result.score)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-4xl font-bold ${getScoreColor(result.score)}`}>
                    {result.score}
                  </span>
                  <span className="text-xs text-muted-foreground">de 100</span>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="flex-1 p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center md:text-left">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-1">
                  <FileText className="w-4 h-4 text-primary" />
                  <span className="text-2xl font-bold">{result.pages_scanned}</span>
                </div>
                <p className="text-xs text-muted-foreground">Páginas analisadas</p>
                <p className="text-[10px] text-muted-foreground/60">{result.pages_found} encontradas</p>
              </div>

              <div className="text-center md:text-left">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-1">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                  <span className="text-2xl font-bold">{totalIssues}</span>
                </div>
                <p className="text-xs text-muted-foreground">Issues encontrados</p>
                <p className="text-[10px] text-muted-foreground/60">{result.tasks_created} tarefas criadas</p>
              </div>

              <div className="text-center md:text-left">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-1">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  <span className={`text-2xl font-bold ${getScoreColor(result.score)}`}>
                    {getScoreLabel(result.score)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Saúde SEO</p>
              </div>

              <div className="text-center md:text-left">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-1">
                  <Clock className="w-4 h-4 text-blue-500" />
                  <span className="text-2xl font-bold">{result.duration_seconds}s</span>
                </div>
                <p className="text-xs text-muted-foreground">Tempo de análise</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Issues Breakdown */}
      {sortedIssues.length > 0 && (
        <Card className="card-gradient border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Problemas Detectados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sortedIssues.map(({ code, count, label, description, priority }) => (
                <div 
                  key={code}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Badge 
                      variant="outline" 
                      className={`text-[10px] px-2 py-0.5 shrink-0 ${getPriorityColor(priority)}`}
                    >
                      {priority === "critical" ? "Crítico" : 
                       priority === "high" ? "Alto" : 
                       priority === "medium" ? "Médio" : "Baixo"}
                    </Badge>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate text-[#F5F5F5]">{label}</p>
                      <p className="text-xs text-muted-foreground truncate opacity-0 group-hover:opacity-100 transition-opacity">
                        {description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[#F5F5F5]">{count}</span>
                    <span className="text-xs text-[#F5F5F5]/70">ocorrência(s)</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Clear */}
      {sortedIssues.length === 0 && result.pages_scanned > 0 && (
        <Card className="card-gradient border-green-500/30 bg-green-500/5">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <h3 className="font-semibold text-green-500">Parabéns!</h3>
                <p className="text-sm text-muted-foreground">
                  Nenhum problema de SEO foi encontrado nas páginas analisadas.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ScanSummary;
