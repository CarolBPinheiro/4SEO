import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "@/contexts/StoreContext";
import { useBilling } from "@/contexts/BillingContext";
import { api } from "@/lib/apiClient";
import {
  RefreshCw,
  CheckSquare,
  TrendingUp,
  Loader2,
  Sparkles,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";

// Donut chart SVG component
function ScoreDonut({ score, size = 180 }: { score: number; size?: number }) {
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const center = size / 2;

  // Color based on score
  const color = score >= 70 ? "hsl(24, 100%, 55%)" : score >= 40 ? "hsl(45, 100%, 55%)" : "hsl(0, 84%, 60%)";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          strokeWidth="10"
          stroke="hsl(240, 12%, 14%)"
          fill="none"
        />
        {/* Progress circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          strokeWidth="10"
          stroke={color}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold text-foreground">{score || 0}</span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
    </div>
  );
}

// Filtros rápidos das oportunidades
function FiltrosRapidos({
  filtros,
  ativos,
  onToggle
}: {
  filtros: { id: string; label: string; count: number }[];
  ativos: Set<string>;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {filtros.map((f) => {
        // "Todos" fica ativo quando nenhum outro filtro está selecionado
        const isActive = f.id === "todos" ? ativos.size === 0 : ativos.has(f.id);
        return (
          <button
            key={f.id}
            onClick={() => onToggle(f.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors
              ${isActive
                ? "bg-primary/20 border-primary text-primary"
                : "bg-card border-border text-muted-foreground hover:border-muted-foreground"
              }`}
          >
            {f.label}
            <span className="opacity-50">({f.count})</span>
          </button>
        );
      })}
    </div>
  );
}

interface Oportunidade {
  page_url: string;
  page_id: string;
  issue_code: string;
  issue_label: string;
  impacto: "alto" | "medio" | "baixo";
  penalty: number;
  message: string;
  otimizado: boolean;
  task_id: string | null;
}

interface FiltroDisponivel {
  id: string;
  label: string;
  count: number;
  kind?: string;
}

// Categorias de filtro (ids fixos definidos pela spec / backend)
const IMPACTO_IDS = ["alto", "medio", "baixo"];
const OTIMIZADO_IDS = ["nao_otimizados", "ja_otimizados"];

// Card de oportunidade individual com nível de impacto
function OportunidadeCard({ op }: { op: Oportunidade }) {
  const impactoEmoji: Record<string, string> = {
    alto: "🔴",
    medio: "🟡",
    baixo: "🟢",
  };
  const impactoBg: Record<string, string> = {
    alto: "bg-red-500/10 border-red-500/30",
    medio: "bg-yellow-500/10 border-yellow-500/30",
    baixo: "bg-green-500/10 border-green-500/30",
  };

  return (
    <div className={`rounded-lg border p-4 ${impactoBg[op.impacto] || ""}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span>{impactoEmoji[op.impacto]}</span>
            <span className="text-sm font-semibold">{op.issue_label}</span>
            {op.otimizado && (
              <span className="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                ✓ Otimizado
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{op.message}</p>
          <p className="text-xs text-muted-foreground mt-1 truncate max-w-md">
            {op.page_url}
          </p>
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          -{op.penalty} pts
        </span>
      </div>
    </div>
  );
}

// Card Saúde SEO (substitui "Pontuação da Loja")
function SaudeSeoCard({ score }: { score: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 flex flex-col items-center">
      <div className="w-full flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-medium text-muted-foreground">Saúde SEO</h3>
      </div>
      <ScoreDonut score={score} size={120} />
      <p className="text-xs text-muted-foreground mt-3">{score}/100</p>
    </div>
  );
}

// Novo card Visibilidade SEO — usa dados de data.visibilidade_seo
function VisibilidadeCard({ pct }: { pct: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-medium text-muted-foreground">Visibilidade SEO</h3>
      </div>
      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-3xl font-bold">{pct}%</span>
      </div>
      <div className="w-full h-2 bg-muted/30 rounded-full mb-2">
        <div className="h-full rounded-full bg-primary transition-all"
             style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        Percentual de visibilidade nos motores de busca com base nos critérios monitorados
      </p>
    </div>
  );
}

// Card Potencial SEO com badge colorido
function PotencialSEO({ label, color }: { label: string; color: string }) {
  const colorMap: Record<string, string> = {
    "verde": "bg-green-500/20 text-green-400 border-green-500/30",
    "amarelo": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    "cinza": "bg-muted text-muted-foreground border-border",
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-medium text-muted-foreground">Potencial SEO</h3>
      </div>
      <span className={`inline-block px-3 py-1 text-sm font-bold rounded-full border ${colorMap[color] || colorMap.cinza}`}>
        {label}
      </span>
      <p className="text-xs text-muted-foreground mt-3" title="Estimativa baseada nas oportunidades de otimização identificadas pela plataforma.">
        Estimativa baseada nas oportunidades de otimização identificadas
      </p>
    </div>
  );
}

// Card Oportunidades Encontradas (substitui "Tarefas Pendentes")
function OportunidadesEncontradas({ total }: { total: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-medium text-muted-foreground">Oportunidades Encontradas</h3>
      </div>
      <span className="text-3xl font-bold">{total}</span>
      <p className="text-xs text-muted-foreground mt-3">
        Ganho potencial identificado pela plataforma
      </p>
    </div>
  );
}

// Card Cliques Orgânicos (substitui "Menções")
function CliquesOrganicos({ total }: { total: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-medium text-muted-foreground">Cliques Orgânicos</h3>
      </div>
      <span className="text-3xl font-bold">{total.toLocaleString()}</span>
      <p className="text-xs text-muted-foreground mt-3">
        Volume de cliques oriundos de tráfego orgânico (via GSC)
      </p>
    </div>
  );
}

// Card Termos Monitorados
function TermosMonitorados({ total }: { total: number }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-medium text-muted-foreground">Termos Monitorados</h3>
      </div>
      <span className="text-3xl font-bold">{total}</span>
      <p className="text-xs text-muted-foreground mt-3">
        Termos de pesquisa acompanhados no Google Trends
      </p>
    </div>
  );
}

// Cards de volumetria contextualizada
function VolumetriaCard({ tipo, score, analisados }: {
  tipo: "Produtos" | "Páginas";
  score: number;
  analisados: number
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 flex items-center justify-between">
      <div>
        <h4 className="text-sm font-medium">{tipo}</h4>
        <p className="text-xs text-muted-foreground">
          {analisados} {tipo.toLowerCase()} {tipo === "Páginas" ? "analisadas" : "analisados"}
        </p>
      </div>
      <div className="text-right">
        <span className="text-2xl font-bold">{score}</span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
    </div>
  );
}

interface DashboardDataV2 {
  connected: boolean;
  // Novos campos
  saude_seo: number;
  visibilidade_seo: number;
  potencial_seo: string;
  potencial_seo_label: string;
  potencial_seo_color: string;
  oportunidades_encontradas: number;
  cliques_organicos: number;
  volumetria_produtos: { score: number; analisados: number };
  volumetria_paginas: { score: number; analisados: number };
  termos_count: number;
  // Legado (ainda usados em outros componentes)
  store_score: number;
  visibility_pct: number;
  growth_potential: string;
  growth_potential_label: string;
  total_pages_scanned: number;
  last_scan: { completed_at: string | null; pages_scanned: number; tasks_created: number };
  [key: string]: unknown;  // outros campos existentes
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { connected } = useStore();
  const { hasActiveSubscription, loading: billingLoading, subscribeUrl } = useBilling();
  const [data, setData] = useState<DashboardDataV2 | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchSummary = useCallback(async (refresh = false) => {
    if (!connected || !hasActiveSubscription) return;
    setLoading(true);
    try {
      const result = await api.dashboard.summary(refresh);
      setData(result);
    } catch {
      // API protegida por assinatura — UI permanece zerada
    } finally {
      setLoading(false);
    }
  }, [connected, hasActiveSubscription]);

  const [scanError, setScanError] = useState<string | null>(null);

  // Atualiza panorama: dispara scan via /api/scan e faz polling até o scan terminar
  const handleRefresh = useCallback(async () => {
    if (!connected || !hasActiveSubscription) return;
    setLoading(true);
    setScanError(null);
    try {
      // Marca o completed_at atual antes de disparar
      const before = data?.last_scan?.completed_at ?? null;
      const hadPages = (data?.total_pages_scanned ?? 0) > 0;
      // Se ainda não há páginas, força bypass do cooldown
      try {
        const r = await api.dashboard.scan(!hadPages);
        if (r?.status === "cooldown") {
          setScanError(`Aguarde ${r.seconds_until_next || 60}s antes de re-escanear`);
        } else if (r?.status === "already_running") {
          setScanError("Uma análise já está em andamento — aguardando ela terminar...");
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Falha ao iniciar scan";
        setScanError(msg);
      }
      // Atualiza UI imediatamente com último estado do banco
      try {
        const initial = await api.dashboard.summary(false);
        setData(initial);
      } catch {
        // ignore
      }

      // Polling: 5s × 24 tentativas (~2 min) até completed_at avançar
      let scanCompleted = false;
      for (let i = 0; i < 24; i++) {
        await new Promise(r => setTimeout(r, 5000));
        try {
          const next = await api.dashboard.summary(false);
          setData(next);
          const after = next?.last_scan?.completed_at ?? null;
          if (after && after !== before) {
            scanCompleted = true;
            // Se completou mas não encontrou páginas, avisa o usuário
            if ((next?.total_pages_scanned ?? 0) === 0) {
              setScanError(
                "O scan terminou mas nenhuma página foi analisada. Verifique se a URL está correta e acessível publicamente."
              );
            }
            break;
          }
        } catch {
          // polling best-effort
        }
      }
      if (!scanCompleted) {
        setScanError("O scan está demorando mais que o esperado. Tente novamente em alguns minutos.");
      }
    } catch (err: unknown) {
      setScanError(err instanceof Error ? err.message : "Erro ao atualizar");
    } finally {
      setLoading(false);
    }
  }, [connected, hasActiveSubscription, data?.last_scan?.completed_at, data?.total_pages_scanned]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Recém-conectado (ex.: redirect de Integrações): o site ainda não tem
  // nenhuma página escaneada, mas um scan inicial já foi disparado em
  // background pelo backend no momento da conexão. Sem isso, o usuário só
  // via um banner estático pedindo pra clicar em "Analisar agora" — sem
  // nenhum sinal de que uma análise já estava rodando. Dispara
  // (no máximo uma vez) o mesmo fluxo de refresh+polling do botão manual;
  // se já houver um scan em andamento, o backend só reaproveita e o
  // polling detecta o término normalmente.
  const autoScanTriggeredRef = useRef(false);
  useEffect(() => {
    if (
      data?.connected &&
      (data.total_pages_scanned ?? 0) === 0 &&
      !loading &&
      !autoScanTriggeredRef.current
    ) {
      autoScanTriggeredRef.current = true;
      handleRefresh();
    }
  }, [data, loading, handleRefresh]);

  // Oportunidades com filtros inteligentes
  const [oportunidades, setOportunidades] = useState<Oportunidade[]>([]);
  const [filtrosDisponiveis, setFiltrosDisponiveis] = useState<FiltroDisponivel[]>([]);
  // Set vazio = "Todos" (sem filtro)
  const [filtrosAtivos, setFiltrosAtivos] = useState<Set<string>>(new Set());

  const fetchOportunidades = useCallback(async () => {
    if (!hasActiveSubscription) return;
    try {
      const ativos = [...filtrosAtivos];
      const impactos = ativos.filter(f => IMPACTO_IDS.includes(f));
      // Tudo que não é impacto/otimização/"todos" é um filtro de tipo de issue
      const tipos = ativos.filter(f => !IMPACTO_IDS.includes(f) && !OTIMIZADO_IDS.includes(f) && f !== "todos");
      // Filtros de status de otimização: só aplica se exatamente um deles estiver ativo
      const naoOtim = filtrosAtivos.has("nao_otimizados");
      const jaOtim = filtrosAtivos.has("ja_otimizados");
      const otimizados = naoOtim && !jaOtim ? "nao" : jaOtim && !naoOtim ? "sim" : undefined;
      const result = await api.dashboard.oportunidades({
        impactos: impactos.join(","),
        tipos: tipos.join(","),
        otimizados,
      });
      setOportunidades((result?.oportunidades as Oportunidade[]) || []);
      if (result?.filtros_disponiveis) setFiltrosDisponiveis(result.filtros_disponiveis);
    } catch {
      // API protegida — lista permanece vazia
    }
  }, [filtrosAtivos, hasActiveSubscription]);

  useEffect(() => {
    if (data?.connected) fetchOportunidades();
  }, [data?.connected, fetchOportunidades]);

  const toggleFiltro = (id: string) => {
    setFiltrosAtivos(prev => {
      // "Todos" limpa todos os filtros
      if (id === "todos") return new Set();
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // Sem nenhuma página escaneada ainda, os KPIs (Saúde SEO 0/100, Potencial
  // etc.) não têm dado real por trás — mostrá-los ao lado do banner "site
  // ainda não foi analisado" é uma contradição visual (ex.: Saúde SEO
  // vermelho "0/100" ao mesmo tempo que Potencial SEO verde "ALTO").
  const notYetAnalyzed = !!(data && data.connected && data.total_pages_scanned === 0);

  const saudeSeo = data?.saude_seo ?? data?.store_score ?? 0;
  const visibilidade = data?.visibilidade_seo ?? data?.visibility_pct ?? 0;
  const potencialLabel = data?.potencial_seo_label ?? "--";
  const potencialColor = data?.potencial_seo_color ?? "cinza";
  const oportunidadesCount = data?.oportunidades_encontradas ?? 0;
  const cliques = data?.cliques_organicos ?? 0;
  const termos = data?.termos_count ?? 0;

  if (billingLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!hasActiveSubscription) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/15">
            <Lock className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-foreground">
            Sua conta foi criada com sucesso.
          </h2>
          <p className="mx-auto mb-6 max-w-lg text-sm leading-relaxed text-muted-foreground">
            Para acessar todos os recursos da plataforma — categorias, integrações,
            análise e demais funcionalidades — é necessário possuir uma assinatura ativa.
          </p>
          <Button
            className="btn-gradient font-semibold text-primary-foreground"
            onClick={() => {
              window.location.assign(subscribeUrl);
            }}
          >
            Ver planos e assinar
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SaudeSeoCard score={0} />
          <VisibilidadeCard pct={0} />
          <PotencialSEO label="--" color="cinza" />
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <OportunidadesEncontradas total={0} />
          <CliquesOrganicos total={0} />
          <TermosMonitorados total={0} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Loading overlay for first scan */}
      {loading && !data && connected && (
        <div className="rounded-xl bg-card border border-border p-8 flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
          <p className="text-sm text-muted-foreground">Carregando dados...</p>
        </div>
      )}

      {/* Site recém-conectado: scan inicial disparado automaticamente (em
          andamento via handleRefresh acima) — sinaliza analisando, sem pedir
          ação do usuário. */}
      {data && data.connected && data.total_pages_scanned === 0 && loading && (
        <div className="rounded-xl bg-card border border-border p-8 flex flex-col items-center gap-4 text-center">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
          <div>
            <h3 className="text-lg font-semibold mb-1">Estamos analisando seu site...</h3>
            <p className="text-sm text-muted-foreground">
              Isso pode levar alguns minutos. Você pode navegar livremente enquanto isso.
            </p>
          </div>
        </div>
      )}

      {/* Empty state: site cadastrado mas sem páginas analisadas ainda, e
          nenhum scan em andamento no momento (falha no auto-scan, timeout,
          ou usuário quer tentar de novo manualmente). */}
      {data && data.connected && data.total_pages_scanned === 0 && !loading && (
        <div className="rounded-xl bg-card border border-border p-8 flex flex-col items-center gap-4 text-center">
          <Sparkles className="w-10 h-10 text-primary" />
          <div>
            <h3 className="text-lg font-semibold mb-1">Seu site ainda não foi analisado</h3>
            <p className="text-sm text-muted-foreground">
              Rode a primeira análise para começar a ver insights de SEO.
            </p>
            {scanError && (
              <p className="text-sm text-red-400 mt-3 max-w-md">{scanError}</p>
            )}
          </div>
          <Button onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Analisar meu site agora
          </Button>
        </div>
      )}

      {/* Header com botão de atualização */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Panorama da sua loja</h2>
        </div>
        {connected && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2 border-primary/30 text-primary hover:bg-primary/10"
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Atualizar panorama
          </Button>
        )}
      </div>

      {/* KPIs só fazem sentido quando já existe pelo menos um scan concluído —
          enquanto isso, só o banner "ainda não foi analisado" é exibido. */}
      {!notYetAnalyzed && (
        <>
      {/* LINHA 1: Saúde SEO | Visibilidade SEO | Potencial SEO */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SaudeSeoCard score={saudeSeo} />
        <VisibilidadeCard pct={visibilidade} />
        <PotencialSEO label={potencialLabel} color={potencialColor} />
      </div>

      {/* LINHA 2: Oportunidades Encontradas | Cliques Orgânicos | Termos Monitorados */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <OportunidadesEncontradas total={oportunidadesCount} />
        <CliquesOrganicos total={cliques} />
        <TermosMonitorados total={termos} />
      </div>

      {/* LINHA 3: Volumetria Produtos | Volumetria Páginas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <VolumetriaCard
          tipo="Produtos"
          score={data?.volumetria_produtos?.score ?? 0}
          analisados={data?.volumetria_produtos?.analisados ?? 0}
        />
        <VolumetriaCard
          tipo="Páginas"
          score={data?.volumetria_paginas?.score ?? 0}
          analisados={data?.volumetria_paginas?.analisados ?? 0}
        />
      </div>
        </>
      )}

      {/* Principais Oportunidades (substitui o Checklist da Loja) */}
      <div className="rounded-xl bg-card border border-border p-6">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <CheckSquare className="w-4 h-4 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Principais Oportunidades</h2>
        </div>

        {connected ? (
          <div>
            <FiltrosRapidos
              filtros={filtrosDisponiveis}
              ativos={filtrosAtivos}
              onToggle={toggleFiltro}
            />
            {oportunidades.length > 0 ? (
              <div className="space-y-3">
                {oportunidades.map((op, i) => (
                  <OportunidadeCard key={`${op.page_id}_${op.issue_code}_${i}`} op={op} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4">
                Nenhuma oportunidade encontrada com os filtros selecionados.
              </p>
            )}
          </div>
        ) : (
          /* Empty state  - illustration left, text right */
          <div className="flex items-center justify-center gap-6 py-6">
            <img
              src="/illustrations/connect.png"
              alt="Conecte sua loja"
              className="w-[340px] h-auto object-contain flex-shrink-0"
            />
            <p className="text-xl font-semibold text-foreground text-center leading-relaxed">
              Conecte sua loja/site em<br />
              <button
                onClick={() => navigate("/integracoes")}
                className="text-primary font-semibold hover:underline"
              >
                Integrações
              </button>{" "}
              para<br />
              visualizar os dados
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
