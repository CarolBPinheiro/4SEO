import { useState, useEffect, useCallback } from "react";
import { useStore } from "@/contexts/StoreContext";
import { api } from "@/lib/apiClient";
import {
  FileText, TrendingUp, BarChart3, Globe, Search, Eye, MousePointer,
  Target, AlertTriangle, CheckCircle, Loader2, RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line,
} from "recharts";

const PIE_COLORS = ["hsl(142,76%,50%)", "hsl(45,100%,55%)", "hsl(24,100%,55%)", "hsl(0,70%,50%)"];

const ISSUE_LABELS: Record<string, string> = {
  missing_title: "Título ausente",
  title_length: "Título fora do ideal",
  missing_meta_description: "Meta description ausente",
  missing_h1: "H1 ausente",
  missing_img_alt: "Imagens sem alt",
  missing_canonical: "Canonical ausente",
  missing_og_tags: "Open Graph ausente",
  missing_schema: "Schema ausente",
};

export default function PanoramaSEO() {
  const { connected } = useStore();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  const fetchPanorama = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.panorama.get();
      setData(result);
    } catch (e: any) {
      console.error("Panorama:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setScanning(true);
    try {
      // Dispara o scan em background
      await api.dashboard.summary(true);

      // Polling até ter páginas ou timeout de 90s
      const maxAttempts = 18;
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 5000));
        const result = await api.panorama.get();
        setData(result);
        if ((result?.total_pages ?? 0) > 0) break;
      }
    } catch (e: any) {
      console.error("Panorama refresh:", e);
    } finally {
      setLoading(false);
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    if (connected) fetchPanorama();
  }, [connected, fetchPanorama]);

  if (!connected || (!data && !loading)) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl bg-card border border-border p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <FileText className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">Panorama SEO</h1>
          </div>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-28 h-28 rounded-full bg-muted/20 flex items-center justify-center mb-6">
              <BarChart3 className="w-14 h-14 text-primary/50" />
            </div>
            <p className="text-lg text-muted-foreground mb-1">
              Conecte sua loja para ver o panorama SEO
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  // Prepare chart data
  const issueChartData = Object.entries(data?.issue_distribution || {})
    .map(([key, count]) => ({ name: ISSUE_LABELS[key] || key, count: count as number }))
    .sort((a, b) => b.count - a.count);

  const scoreDistData = [
    { name: "Excelente \u2014 SEO impecável (80\u2013100)", value: data?.score_distribution?.excellent || 0 },
    { name: "Bom \u2014 pequenos ajustes (60\u201379)", value: data?.score_distribution?.good || 0 },
    { name: "Regular \u2014 vários problemas (40\u201359)", value: data?.score_distribution?.fair || 0 },
    { name: "Ruim \u2014 crítico, requer atenção (0\u201339)", value: data?.score_distribution?.poor || 0 },
  ].filter((d) => d.value > 0);

  const snapshotChart = (data?.snapshots || []).map((s: any) => ({
    date: new Date(s.date + "T12:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
    Impressões: s.impressions,
    Cliques: s.clicks,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">Panorama SEO</h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={loading}
          className="gap-2 border-primary/30 text-primary hover:bg-primary/10"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {scanning ? "Escaneando..." : "Atualizar"}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl bg-card border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Score Médio</span>
          </div>
          <p className="text-2xl font-bold">{data?.avg_score || 0}<span className="text-sm text-muted-foreground">/100</span></p>
        </div>
        <div className="rounded-xl bg-card border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Eye className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Impressões</span>
          </div>
          <p className="text-2xl font-bold">{(data?.impressions || 0).toLocaleString("pt-BR")}</p>
        </div>
        <div className="rounded-xl bg-card border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <MousePointer className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Cliques</span>
          </div>
          <p className="text-2xl font-bold">{(data?.clicks || 0).toLocaleString("pt-BR")}</p>
        </div>
        <div className="rounded-xl bg-card border border-border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Páginas</span>
          </div>
          <p className="text-2xl font-bold">{data?.total_pages || 0}</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Issue Distribution */}
        {issueChartData.length > 0 && (
          <div className="rounded-xl bg-card border border-border p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Problemas por tipo
            </h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={issueChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,12%,20%)" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="hsl(240,12%,40%)" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={130} stroke="hsl(240,12%,40%)" />
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(240,12%,10%)", border: "1px solid hsl(240,12%,20%)", borderRadius: 8, color: "#fff" }}
                  itemStyle={{ color: "#fff" }}
                  labelStyle={{ color: "#fff" }}
                />
                <Bar dataKey="count" fill="hsl(24,100%,55%)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Score Distribution Pie */}
        {scoreDistData.length > 0 && (
          <div className="rounded-xl bg-card border border-border p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              Distribuição de scores
            </h2>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={220}>
                <PieChart>
                  <Pie data={scoreDistData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                    {scoreDistData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(240,12%,10%)", border: "1px solid hsl(240,12%,20%)", borderRadius: 8, color: "#fff" }}
                    itemStyle={{ color: "#fff" }}
                    labelStyle={{ color: "#fff" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {scoreDistData.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-xs text-white">{d.name}</span>
                    <span className="text-xs font-semibold text-white ml-auto">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Historical Chart */}
      {snapshotChart.length > 1 && (
        <div className="rounded-xl bg-card border border-border p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Performance orgânica (últimos 30 dias)
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={snapshotChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,12%,20%)" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="hsl(240,12%,40%)" />
              <YAxis tick={{ fontSize: 12 }} stroke="hsl(240,12%,40%)" />
              <Tooltip
                contentStyle={{ backgroundColor: "hsl(240,12%,10%)", border: "1px solid hsl(240,12%,20%)", borderRadius: 8, color: "#fff" }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#fff" }}
              />
              <Line type="monotone" dataKey="Impressões" stroke="hsl(24,100%,55%)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Cliques" stroke="hsl(142,76%,50%)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top Queries */}
      {data?.top_queries?.length > 0 && (
        <div className="rounded-xl bg-card border border-border p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Search className="w-5 h-5 text-primary" />
            Top consultas no Google
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Consulta</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Cliques</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Impressões</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">CTR</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Posição</th>
                </tr>
              </thead>
              <tbody>
                {data.top_queries.map((q: any, i: number) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/10">
                    <td className="py-2.5 px-2 font-medium">{q.query}</td>
                    <td className="py-2.5 px-2 text-right">{q.clicks}</td>
                    <td className="py-2.5 px-2 text-right">{q.impressions}</td>
                    <td className="py-2.5 px-2 text-right">
                      <Badge variant="outline">{q.ctr}%</Badge>
                    </td>
                    <td className="py-2.5 px-2 text-right">{q.position}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info bar */}
      <div className="rounded-xl bg-muted/10 border border-border p-4 flex items-center gap-4 text-sm text-muted-foreground">
        <Globe className="w-5 h-5 text-primary flex-shrink-0" />
        <span>
          Plataforma: <span className="font-semibold text-foreground">{data?.platform || "--"}</span>
          {" · "}
          Tarefas pendentes: <span className="font-semibold text-foreground">{data?.tasks_pending || 0}</span>
          {" · "}
          Termos monitorados: <span className="font-semibold text-foreground">{data?.termos_count || 0}</span>
          {data?.last_scan_at && (
            <>
              {" · "}
              Último scan: <span className="font-semibold text-foreground">
                {new Date(data.last_scan_at).toLocaleDateString("pt-BR")}
              </span>
            </>
          )}
        </span>
      </div>
    </div>
  );
}
