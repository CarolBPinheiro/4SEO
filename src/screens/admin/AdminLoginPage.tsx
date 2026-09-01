import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock, Mail, Radio, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/apiClient";
import { getAdminToken, setAdminSession } from "@/lib/adminSession";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getAdminToken()) return;
    let cancelled = false;
    void (async () => {
      try {
        await api.admin.me();
        if (!cancelled) navigate("/admin", { replace: true });
      } catch {
        /* sessão inválida — permanece no login */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await api.admin.login(email.trim(), password);
      setAdminSession(result.token, result.email);
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login administrativo");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#050506] px-4 text-white">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,117,26,0.16),transparent_48%)]" />
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-black/60 p-8 backdrop-blur-xl">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-10 w-8 items-center justify-center rounded-lg bg-[#ff751a]/15 text-[#ff8a3d]">
            <Radio className="h-4 w-4" />
          </span>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#ff8a3d]">
              4SEO Admin
            </p>
            <p className="text-sm text-zinc-400">Área interna da plataforma</p>
          </div>
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Acesso administrativo</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Esta tela é exclusiva da operação. Não usa a conta de assinante.
        </p>
        <form className="mt-6 space-y-4" onSubmit={(event) => void submit(event)}>
          <div className="space-y-2">
            <Label htmlFor="admin-email">E-mail</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <Input
                id="admin-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="border-white/10 bg-white/5 pl-10"
                required
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="admin-password">Senha</Label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <Input
                id="admin-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-white/10 bg-white/5 px-10"
                required
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {error ? (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="btn-gradient w-full" disabled={loading}>
            <Shield className="mr-2 h-4 w-4" />
            {loading ? "Entrando…" : "Entrar no painel"}
          </Button>
        </form>
      </div>
    </div>
  );
}
