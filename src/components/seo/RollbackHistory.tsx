import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Undo2, Loader2, ChevronDown, ChevronUp, History } from "lucide-react";

export interface RollbackRecordLike {
  id: string;
  product_id: number;
  field_name: string;
  original_value: string | null;
  new_value: string;
  applied_at: string;
  rolled_back: boolean;
  content_type?: string;
  optimization_type?: string;
}

interface RollbackHistoryProps {
  records: RollbackRecordLike[];
  loading?: boolean;
  onRollbackSingle: (record: RollbackRecordLike) => Promise<boolean> | void;
  onRollbackAll: () => Promise<boolean> | void;
}

function stripHtml(text: string | null | undefined): string {
  if (!text) return "";
  return String(text).replace(/<[^>]+>/g, "").trim();
}

function truncate(text: string | null | undefined, max = 80): string {
  const clean = stripHtml(text);
  if (!clean) return "(vazio)";
  if (clean.length <= max) return clean;
  return clean.slice(0, max) + "...";
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const FIELD_LABELS: Record<string, string> = {
  title: "Titulo",
  description: "Descricao",
  rich_description: "Descricao",
  seo_title: "SEO Title",
  seo_description: "SEO Description",
  tags: "Tags",
  image_alt: "Alt de imagem",
  faq: "FAQ",
  collection_title: "Titulo da colecao",
  collection_description: "Descricao da colecao",
  collection_seo_title: "SEO Title da colecao",
  collection_seo_description: "SEO Description da colecao",
  category_title: "Titulo da categoria",
  category_description: "Descricao da categoria",
  category_seo_title: "SEO Title da categoria",
  category_seo_description: "SEO Description da categoria",
  page_title: "Titulo da pagina",
  page_content: "Conteudo da pagina",
  page_seo_title: "SEO Title da pagina",
  page_seo_description: "SEO Description da pagina",
  article_title: "Titulo do artigo",
  article_content: "Conteudo do artigo",
  article_seo_title: "SEO Title do artigo",
  article_seo_description: "SEO Description do artigo",
  article_tags: "Tags do artigo",
  blog_title: "Titulo do post",
  blog_body: "Corpo do post",
  blog_seo_title: "SEO Title do post",
  blog_seo_description: "SEO Description do post",
  blog_tags: "Tags do post",
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  product: "Produto",
  collection: "Colecao",
  category: "Categoria",
  page: "Pagina",
  article: "Artigo",
  blog: "Post de blog",
};

function fieldLabel(rec: RollbackRecordLike): string {
  const key = rec.optimization_type || rec.field_name;
  return FIELD_LABELS[key] || key || "Campo";
}

function contentTypeLabel(ct?: string): string {
  if (!ct) return "Item";
  return CONTENT_TYPE_LABELS[ct] || ct;
}

export function RollbackHistory({
  records,
  loading,
  onRollbackSingle,
  onRollbackAll,
}: RollbackHistoryProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [rollingAll, setRollingAll] = useState(false);

  const active = records.filter((r) => !r.rolled_back);

  const handleSingle = async (rec: RollbackRecordLike) => {
    setPendingId(rec.id);
    try {
      await onRollbackSingle(rec);
    } finally {
      setPendingId(null);
    }
  };

  const handleAll = async () => {
    if (!window.confirm(`Reverter todas as ${active.length} alteracoes? Esta acao nao pode ser desfeita.`)) {
      return;
    }
    setRollingAll(true);
    try {
      await onRollbackAll();
    } finally {
      setRollingAll(false);
    }
  };

  if (active.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <History className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            Nenhuma alteracao disponivel para reverter.
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Depois de aplicar propostas, o historico aparece aqui.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card>
        <CardContent className="py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-muted-foreground" />
            <span className="text-sm">
              <strong>{active.length}</strong> alteracao(oes) disponivel(is) para reversao
            </span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleAll}
            disabled={rollingAll || loading}
          >
            {rollingAll ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Undo2 className="h-4 w-4 mr-2" />
            )}
            Reverter todas
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {active.map((rec) => {
          const isExpanded = expanded[rec.id];
          return (
            <Card key={rec.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="text-xs">
                        {contentTypeLabel(rec.content_type)} #{rec.product_id}
                      </Badge>
                      <CardTitle className="text-sm">{fieldLabel(rec)}</CardTitle>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Aplicado em {formatDate(rec.applied_at)}
                    </p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpanded((e) => ({ ...e, [rec.id]: !e[rec.id] }))}
                    >
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSingle(rec)}
                      disabled={pendingId === rec.id || rollingAll || loading}
                    >
                      {pendingId === rec.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Undo2 className="h-4 w-4 mr-1" />
                          Reverter
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              {isExpanded ? (
                <CardContent className="space-y-2 pt-0">
                  <div className="p-2.5 bg-muted/50 rounded-lg">
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">
                      Valor anterior
                    </p>
                    <p className="text-xs break-words whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {truncate(rec.original_value, 500)}
                    </p>
                  </div>
                  <div className="p-2.5 bg-muted/30 rounded-lg">
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">
                      Valor aplicado
                    </p>
                    <p className="text-xs break-words whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {truncate(rec.new_value, 500)}
                    </p>
                  </div>
                </CardContent>
              ) : (
                <CardContent className="pt-0 pb-3">
                  <p className="text-xs text-muted-foreground truncate">
                    <span className="line-through opacity-70">{truncate(rec.original_value, 60)}</span>
                  </p>
                  <p className="text-xs truncate mt-0.5">
                    {truncate(rec.new_value, 60)}
                  </p>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default RollbackHistory;
