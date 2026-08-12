import { useState, useEffect, useCallback } from "react";
import { useStore } from "@/contexts/StoreContext";
import { api } from "@/lib/apiClient";
import {
  CheckSquare,
  TrendingUp,
  Search,
  Flame,
  Zap,
  MinusCircle,
  Plus,
  Trash2,
  RefreshCw,
  Loader2,
  ArrowUpRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SearchTerm {
  id: string;
  term: string;
  chance: "alta" | "moderada" | "baixa";
  conversion_estimate: string;
  searches_per_month: string;
  current_interest: number;
  average_interest: number;
}

interface TrendingItem {
  position: number;
  query: string;
  search_volume: number;
  percentage_increase: number;
  categories: string[];
  keywords: string[];
  is_active: boolean;
  start_date?: string | null;
}

const CATEGORY_LABELS: Record<string, string> = {
  shopping: "Compras",
  technology: "Tecnologia",
  entertainment: "Entretenimento",
  sports: "Esportes",
  business_and_finance: "Negócios",
  beauty_and_fashion: "Moda e beleza",
  food_and_drink: "Comida e bebida",
  health: "Saúde",
  games: "Games",
  travel_and_transportation: "Viagens",
  politics: "Política",
  other: "Outros",
};

function formatVolume(n: number): string {
  if (!n || n <= 0) return "—";
  if (n >= 1_000_000) {
    const v = n / 1_000_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)} mi`;
  }
  if (n >= 1_000) {
    const v = n / 1_000;
    return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)} mil`;
  }
  return n.toLocaleString("pt-BR");
}

function ChanceBadge({ chance }: { chance: SearchTerm["chance"] }) {
  if (chance === "alta") {
    return (
      <Badge className="bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/20 gap-1">
        <Flame className="w-3 h-3" />
        Alta chance de venda
      </Badge>
    );
  }
  if (chance === "moderada") {
    return (
      <Badge className="bg-green-500/20 text-green-400 border-green-500/30 hover:bg-green-500/20 gap-1">
        <Zap className="w-3 h-3" />
        Chance moderada
      </Badge>
    );
  }
  return (
    <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/30 hover:bg-orange-500/20 gap-1">
      <MinusCircle className="w-3 h-3" />
      Baixa chance de venda
    </Badge>
  );
}

function chanceDescription(chance: string, interest: number): string {
  if (chance === "alta") return `Interesse atual ${interest}/100 — ótimo para vender`;
  if (chance === "moderada") return `Interesse atual ${interest}/100 — potencial moderado`;
  return `Interesse atual ${interest}/100 — baixa demanda no momento`;
}

function categoryLabel(raw: string): string {
  return CATEGORY_LABELS[raw] || raw.replace(/_/g, " ");
}

export default function TermosPesquisa() {
  const { connected } = useStore();
  const [terms, setTerms] = useState<SearchTerm[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [newTerm, setNewTerm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [trendingLoading, setTrendingLoading] = useState(false);
  const [trendingError, setTrendingError] = useState<string | null>(null);

  const fetchTerms = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.termos.list();
      setTerms(data.terms || []);
      setCount(data.count || 0);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar termos";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTrending = useCallback(async () => {
    setTrendingLoading(true);
    setTrendingError(null);
    try {
      const data = await api.termos.trending();
      setTrending((data.trends || []).slice(0, 6));
      if (data.error && (!data.trends || data.trends.length === 0)) {
        setTrendingError(data.error);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar pesquisas em alta";
      setTrendingError(msg);
      setTrending([]);
    } finally {
      setTrendingLoading(false);
    }
  }, []);

  useEffect(() => {
    if (connected) {
      fetchTerms();
      fetchTrending();
    }
  }, [connected, fetchTerms, fetchTrending]);

  const handleAdd = async () => {
    const trimmed = newTerm.trim();
    if (!trimmed) return;
    setAdding(true);
    setError(null);
    try {
      await api.termos.add(trimmed);
      setNewTerm("");
      await fetchTerms();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao adicionar termo";
      setError(msg);
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await api.termos.remove(id);
      await fetchTerms();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao remover termo";
      setError(msg);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await api.termos.refresh();
      await fetchTerms();
      await fetchTrending();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao atualizar dados";
      setError(msg);
    } finally {
      setRefreshing(false);
    }
  };

  const useTrendingTerm = (query: string) => {
    if (count >= 5) {
      setError("Limite de 5 termos atingido. Remova um antes de adicionar.");
      return;
    }
    setNewTerm(query);
    setError(null);
    document.getElementById("termo-monitorado-input")?.focus();
  };

  if (!connected) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl bg-card border border-border p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <CheckSquare className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">Termos de Pesquisa</h1>
          </div>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-28 h-28 rounded-full bg-muted/20 flex items-center justify-center mb-6">
              <Search className="w-14 h-14 text-primary/50" />
            </div>
            <p className="text-lg text-muted-foreground">
              Conecte sua loja para monitorar termos de pesquisa
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <CheckSquare className="w-4 h-4 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">Termos de Pesquisa</h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="gap-2 border-primary/30 text-primary hover:bg-primary/10"
        >
          {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Atualizar dados
        </Button>
      </div>

      {/* 6 cards — pesquisas em alta (BR, 24h) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold">Pesquisas em alta</h2>
          </div>
          <p className="text-xs text-muted-foreground">Brasil · últimas 24h</p>
        </div>

        {trendingLoading && trending.length === 0 && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        )}

        {trendingError && trending.length === 0 && !trendingLoading && (
          <div className="rounded-xl bg-card border border-border p-6 text-center">
            <p className="text-sm text-muted-foreground">{trendingError}</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={fetchTrending}>
              Tentar novamente
            </Button>
          </div>
        )}

        {!trendingLoading && !trendingError && trending.length === 0 && (
          <div className="rounded-xl bg-card border border-border p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Nenhuma pesquisa em alta disponível no momento.
            </p>
          </div>
        )}

        {trending.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {trending.map((item, idx) => (
              <button
                key={`${item.position}-${item.query}`}
                type="button"
                onClick={() => useTrendingTerm(item.query)}
                title="Usar este termo no monitoramento"
                className="rounded-xl border border-border bg-card p-5 text-left hover:border-primary/40 hover:bg-card/80 transition-colors group"
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <span className="text-xs font-medium text-muted-foreground">
                    #{item.position || idx + 1}
                  </span>
                  <ArrowUpRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <h3 className="text-sm font-semibold leading-snug mb-3 line-clamp-2">
                  {item.query}
                </h3>
                <div className="flex items-end justify-between gap-2">
                  <div>
                    <p className="text-[10px] text-muted-foreground">Volume est.</p>
                    <p className="text-sm font-semibold">{formatVolume(item.search_volume)}</p>
                  </div>
                  {item.percentage_increase > 0 && (
                    <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/15 gap-1">
                      <TrendingUp className="w-3 h-3" />
                      +{item.percentage_increase}%
                    </Badge>
                  )}
                </div>
                {item.categories[0] && (
                  <p className="text-[10px] text-muted-foreground mt-3 capitalize">
                    {categoryLabel(item.categories[0])}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Monitoramento (persistido) */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Meus termos monitorados</h2>

        <div className="rounded-xl bg-card border border-border p-5">
          <div className="flex items-center gap-3">
            <Input
              id="termo-monitorado-input"
              placeholder="Digite um termo para monitorar..."
              value={newTerm}
              onChange={(e) => setNewTerm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              disabled={adding || count >= 5}
              className="flex-1"
              maxLength={100}
            />
            <Button onClick={handleAdd} disabled={adding || !newTerm.trim() || count >= 5} className="gap-2">
              {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Adicionar
            </Button>
          </div>
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-muted-foreground">{count}/5 termos monitorados</p>
            <div className="flex gap-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full ${i < count ? "bg-primary" : "bg-muted/30"}`}
                />
              ))}
            </div>
          </div>
          {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
        </div>

        {loading && terms.length === 0 && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        )}

        {terms.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {terms.map((term) => (
              <div
                key={term.id}
                className="rounded-xl border border-border bg-card p-5 flex flex-col justify-between"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold">{term.term}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {chanceDescription(term.chance, term.current_interest)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <TrendingUp
                      className={`w-5 h-5 ${
                        term.chance === "alta"
                          ? "text-green-500"
                          : term.chance === "moderada"
                            ? "text-yellow-500"
                            : "text-orange-500"
                      }`}
                    />
                    <button
                      onClick={() => handleRemove(term.id)}
                      className="text-muted-foreground hover:text-red-400 transition-colors"
                      title="Remover termo"
                      type="button"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="mb-4">
                  <ChanceBadge chance={term.chance} />
                </div>

                <div className="flex gap-4">
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 flex-1">
                    <div className="w-4 h-4 text-muted-foreground">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <circle cx="8" cy="8" r="6" />
                        <path d="M8 4v4l3 2" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Conversão est.</p>
                      <p className="text-sm font-semibold">{term.conversion_estimate}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 flex-1">
                    <Search className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-[10px] text-muted-foreground">Buscas por mês</p>
                      <p className="text-sm font-semibold">{term.searches_per_month}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && terms.length === 0 && (
          <div className="rounded-xl bg-card border border-border p-8 text-center">
            <Search className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">
              Adicione termos acima para começar a monitorar buscas no Google
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
