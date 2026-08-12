import { AlertTriangle, CheckCircle, Image } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface DiagnosisIssue {
  type?: string;
  title?: string;
  message?: string;
  severity?: string;
  why?: string;
  impact?: string;
  recommendation?: string;
  suggested_fields?: string[];
}

export interface DiagnosisAnalysis {
  score?: number;
  score_justification?: string;
  summary?: string;
  issues?: DiagnosisIssue[];
  opportunities?: string[];
  recommended_actions?: string[];
  recommendations?: string[];
  images_without_alt?: number | unknown[];
  source?: string;
}

function severityClass(severity?: string): string {
  if (severity === "critical") return "bg-red-500/10 text-red-600 border-red-500/20";
  if (severity === "warning" || severity === "important") {
    return "bg-yellow-500/10 text-yellow-700 border-yellow-500/20";
  }
  return "bg-blue-500/10 text-blue-600 border-blue-500/20";
}

function imagesWithoutAltCount(value: DiagnosisAnalysis["images_without_alt"]): number {
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return value.length;
  return 0;
}

/**
 * Painel de diagnóstico inteligente compartilhado pelas plataformas.
 * Remove o checklist engessado "Ao clicar em Otimizar será gerado".
 */
export function DiagnosisPanel({
  analysis,
  issueFallbackLabel,
}: {
  analysis: DiagnosisAnalysis;
  /** Fallback legado quando a API ainda devolve só `type`/`message`. */
  issueFallbackLabel?: (issue: DiagnosisIssue) => string;
}) {
  const score = typeof analysis.score === "number" ? analysis.score : 0;
  const issues = analysis.issues || [];
  const imgCount = imagesWithoutAltCount(analysis.images_without_alt);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Análise SEO</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">{score}</span>
            <span className="text-muted-foreground">/100</span>
          </div>
        </div>
        <Progress value={score} className="h-2" />
        {analysis.score_justification && (
          <p className="text-sm text-muted-foreground mt-3 leading-relaxed">
            {analysis.score_justification}
          </p>
        )}
        {analysis.summary && !analysis.score_justification && (
          <p className="text-sm text-muted-foreground mt-3">{analysis.summary}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {issues.length === 0 ? (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="w-5 h-5" />
            <span>Nenhum problema encontrado!</span>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">
              {issues.length} problema(s) encontrado(s):
            </p>
            {issues.map((issue, i) => {
              const title =
                issue.title ||
                (issueFallbackLabel ? issueFallbackLabel(issue) : null) ||
                issue.message ||
                issue.type ||
                "Problema identificado";
              return (
                <div
                  key={`${issue.type || "issue"}-${i}`}
                  className={`rounded-lg border p-3 ${severityClass(issue.severity)}`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <div className="space-y-1.5 min-w-0">
                      <p className="text-sm font-semibold">{title}</p>
                      {issue.why && <p className="text-xs opacity-90 leading-relaxed">{issue.why}</p>}
                      {!issue.why && issue.message && issue.title && (
                        <p className="text-xs opacity-90 leading-relaxed">{issue.message}</p>
                      )}
                      {issue.impact && (
                        <p className="text-xs opacity-80">
                          <span className="font-medium">Impacto:</span> {issue.impact}
                        </p>
                      )}
                      {issue.recommendation && (
                        <p className="text-xs opacity-80">
                          <span className="font-medium">Recomendação:</span> {issue.recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {imgCount > 0 && !issues.some((i) => i.type === "missing_image_alt") && (
          <div className="p-3 bg-yellow-500/10 rounded-lg">
            <p className="text-sm text-yellow-600 flex items-center gap-2">
              <Image className="w-4 h-4" />
              {imgCount} imagem(ns) sem texto alternativo
            </p>
          </div>
        )}

        {analysis.opportunities && analysis.opportunities.length > 0 && (
          <div className="rounded-lg border border-border bg-muted/20 p-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Oportunidades</p>
            <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-4">
              {analysis.opportunities.map((op, i) => (
                <li key={i}>{op}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Monta options de optimize a partir do diagnóstico. */
export function optimizeOptionsFromAnalysis(
  analysis: DiagnosisAnalysis | null | undefined,
  targetKeyword?: string
): Record<string, unknown> {
  const actions = analysis?.recommended_actions || [];
  const base: Record<string, unknown> = {};
  if (targetKeyword) base.target_keyword = targetKeyword;
  if (actions.length > 0) {
    base.recommended_actions = actions;
  }
  return base;
}
