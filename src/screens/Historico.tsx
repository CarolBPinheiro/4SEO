import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "@/contexts/StoreContext";
import { api } from "@/lib/apiClient";
import { CheckSquare, RefreshCw, Loader2, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface Snapshot {
  id: string;
  date: string;
  impressions: number;
  clicks: number;
  ctr: number;
  position_avg: number;
  pages_count: number;
}

export default function Historico() {
  const navigate = useNavigate();
  const { connected } = useStore();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshots = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.historico.list(days);
      setSnapshots(data.snapshots || []);
    } catch (e: any) {
      console.error("Historico:", e);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    if (connected) fetchSnapshots();
  }, [connected, fetchSnapshots]);

  const handleSnapshot = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.historico.snapshot();
      await fetchSnapshots();
    } catch (e: any) {
      setError(e?.message || "Erro ao salvar snapshot");
    } finally {
      setSaving(false);
    }
  };

  const chartData = snapshots.map((s) => ({
    date: new Date(s.date + "T12:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
    Impressões: s.impressions,
    Cliques: s.clicks,
    CTR: s.ctr,
  }));

  // Empty state
  if (!connected || (snapshots.length === 0 && !loading)) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl bg-card border border-border p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
              <CheckSquare className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">Histórico</h1>
          </div>

          <div className="flex flex-col items-center justify-center py-12 text-center">
            <img
              src="/illustrations/history-img.png"
              alt="Histórico vazio"
              className="w-80 h-64 mb-8 object-contain"
            />

            {connected ? (
              <>
                <p className="text-lg text-muted-foreground mb-4">
                  Nenhum snapshot registrado ainda.
                </p>
                <Button onClick={handleSnapshot} disabled={saving} className="gap-2">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calendar className="w-4 h-4" />}
                  Gerar primeiro snapshot
                </Button>
                {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
              </>
            ) : (
              <>
                <p className="text-lg text-muted-foreground mb-1">
                  OPS! Parece que não há nada por aqui.
                </p>
                <p className="text-muted-foreground">
                  Seu histórico será gerado após fazer{" "}
                  <br />
                  alterações na{" "}
                  <button
                    onClick={() => navigate("/analise")}
                    className="text-primary font-semibold hover:underline"
                  >
                    análise
                  </button>
                  .
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 flex items-center justify-center">
            <CheckSquare className="w-4 h-4 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">Histórico</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {[30, 60, 90].map((d) => (
              <Button
                key={d}
                variant={days === d ? "default" : "outline"}
                size="sm"
                onClick={() => setDays(d)}
              >
                {d}d
              </Button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSnapshot}
            disabled={saving}
            className="gap-2 border-primary/30 text-primary hover:bg-primary/10"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Salvar snapshot
          </Button>
        </div>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}

      {loading && (
        <div className="flex justify-center py-8">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="rounded-xl bg-card border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Evolução orgânica</h2>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(240,12%,20%)" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="hsl(240,12%,40%)" />
              <YAxis tick={{ fontSize: 12 }} stroke="hsl(240,12%,40%)" />
              <Tooltip
                contentStyle={{ backgroundColor: "hsl(240,12%,10%)", border: "1px solid hsl(240,12%,20%)", borderRadius: 8 }}
                labelStyle={{ color: "hsl(240,12%,80%)" }}
              />
              <Legend />
              <Line type="monotone" dataKey="Impressões" stroke="hsl(24,100%,55%)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Cliques" stroke="hsl(142,76%,50%)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      {snapshots.length > 0 && (
        <div className="rounded-xl bg-card border border-border p-6">
          <h2 className="text-lg font-semibold mb-4">Snapshots diários</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Data</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Impressões</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Cliques</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">CTR</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Posição média</th>
                  <th className="text-right py-3 px-2 text-muted-foreground font-medium">Páginas</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.slice().reverse().map((s) => (
                  <tr key={s.id} className="border-b border-border/50 hover:bg-muted/10">
                    <td className="py-2.5 px-2">
                      {new Date(s.date + "T12:00:00").toLocaleDateString("pt-BR")}
                    </td>
                    <td className="py-2.5 px-2 text-right font-medium">
                      {s.impressions.toLocaleString("pt-BR")}
                    </td>
                    <td className="py-2.5 px-2 text-right font-medium">{s.clicks}</td>
                    <td className="py-2.5 px-2 text-right">
                      <Badge variant="outline">{s.ctr}%</Badge>
                    </td>
                    <td className="py-2.5 px-2 text-right">{s.position_avg}</td>
                    <td className="py-2.5 px-2 text-right">{s.pages_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
