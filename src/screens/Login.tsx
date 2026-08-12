import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogIn, UserPlus, ArrowLeft, Mail, Lock, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { getMarketingUrl } from "@/lib/site";
import {
  claimPendingCheckout,
  persistBillingRef,
  readPendingBillingRef,
} from "@/lib/billingClaim";

type AuthMode = "login" | "register" | "forgot";

export default function Login() {
  const navigate = useNavigate();
  const { signIn, signUp, resetPassword, user, loading: authLoading } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const ref = readPendingBillingRef();
    if (ref) {
      persistBillingRef(ref);
    }
  }, []);

  useEffect(() => {
    if (!user || authLoading) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        await claimPendingCheckout();
      } catch {
        // best-effort
      }
      if (!cancelled) {
        navigate("/dashboard", { replace: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, authLoading, navigate]);

  if (user && !authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050506] text-sm text-zinc-400">
        Preparando sua conta…
      </div>
    );
  }

  const finishAuthAndClaim = async () => {
    try {
      await claimPendingCheckout();
    } catch {
      // Claim é best-effort; usuário ainda entra no app
    }
    navigate("/dashboard");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await signIn(email, password);
    setLoading(false);
    if (result.error) {
      setError(result.error);
    } else {
      await finishAuthAndClaim();
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await signUp(email, password);
    setLoading(false);
    if (result.error) {
      setError(result.error);
    } else {
      setMessage(
        "Conta criada com sucesso. Verifique seu e-mail para confirmar e faça login. " +
          "Para usar os recursos da plataforma, é necessário uma assinatura ativa."
      );
      setMode("login");
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await resetPassword(email);
    setLoading(false);
    if (result.error) {
      setError(result.error);
    } else {
      setMessage("Link de recuperação enviado para seu e-mail.");
      setMode("login");
    }
  };

  const goToMarketing = () => {
    window.location.assign(getMarketingUrl());
  };

  const title =
    mode === "login"
      ? "Olá, que bom ver você de volta!"
      : mode === "register"
        ? "Crie sua conta na 4SEO"
        : "Recupere o acesso";

  const subtitle =
    mode === "login"
      ? "Acesse sua conta para acompanhar o SEO da sua loja."
      : mode === "register"
        ? "Qualquer pessoa pode criar uma conta. Os recursos da plataforma liberam com assinatura ativa."
        : "Informe seu e-mail para receber o link de recuperação.";

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#050506] text-white">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,117,26,0.2),transparent_55%),radial-gradient(ellipse_at_bottom,rgba(255,255,255,0.04),transparent_50%)]"
      />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-12">
        <div className="w-full max-w-[420px]">
          <div className="mb-10 flex flex-col items-center text-center">
            <p className="text-sm font-semibold tracking-[0.18em] text-[#ff8a3d] uppercase">
              4SEO
            </p>
            <img src="/logo.png" alt="4SEO" className="mt-3 h-14 w-auto" />
            <p className="mt-3 text-xs font-medium tracking-wide text-zinc-500 uppercase">
              Minha Conta
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-8 shadow-[0_24px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
            <h1 className="mb-2 text-center text-[1.65rem] font-bold leading-tight tracking-tight">
              {title}
            </h1>
            <p className="mb-8 text-center text-sm leading-relaxed text-zinc-400">
              {subtitle}
            </p>

            {error && (
              <div className="mb-4 rounded-xl border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}
            {message && (
              <div className="mb-4 rounded-xl border border-green-500/25 bg-green-500/10 p-3 text-sm text-green-400">
                {message}
              </div>
            )}

            {mode === "login" && (
              <>
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="sr-only">
                      E-mail
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="Endereço de e-mail"
                        autoComplete="email"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password" className="sr-only">
                      Senha
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Senha"
                        autoComplete="current-password"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10 pr-11"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                        aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    <div className="pt-1 text-center">
                      <button
                        type="button"
                        onClick={() => {
                          setMode("forgot");
                          setError("");
                          setMessage("");
                        }}
                        className="text-sm font-semibold text-white underline underline-offset-4 hover:text-[#ff8a3d]"
                      >
                        Esqueceu sua senha?
                      </button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="btn-gradient mt-2 h-12 w-full rounded-xl font-semibold text-primary-foreground"
                    size="lg"
                    disabled={loading}
                  >
                    <LogIn className="mr-2 h-4 w-4" />
                    {loading ? "Entrando..." : "Fazer login"}
                  </Button>
                </form>

                <p className="mt-8 text-center text-sm text-zinc-400">
                  Não tem uma conta?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("register");
                      setError("");
                      setMessage("");
                    }}
                    className="font-semibold text-[#ff8a3d] hover:underline"
                  >
                    Criar conta
                  </button>
                </p>
              </>
            )}

            {mode === "register" && (
              <>
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="reg-email" className="sr-only">
                      E-mail
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="reg-email"
                        type="email"
                        placeholder="Endereço de e-mail"
                        autoComplete="email"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-password" className="sr-only">
                      Senha
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="reg-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Crie uma senha (mín. 6 caracteres)"
                        autoComplete="new-password"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10 pr-11"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={6}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                        aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="btn-gradient h-12 w-full rounded-xl font-semibold text-primary-foreground"
                    size="lg"
                    disabled={loading}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    {loading ? "Criando..." : "Criar conta"}
                  </Button>
                </form>

                <p className="mt-8 text-center text-sm text-zinc-400">
                  Já tem uma conta?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("login");
                      setError("");
                    }}
                    className="font-semibold text-[#ff8a3d] hover:underline"
                  >
                    Fazer login
                  </button>
                </p>
              </>
            )}

            {mode === "forgot" && (
              <>
                <form onSubmit={handleForgot} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="forgot-email" className="sr-only">
                      E-mail
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="forgot-email"
                        type="email"
                        placeholder="Endereço de e-mail"
                        autoComplete="email"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="btn-gradient h-12 w-full rounded-xl font-semibold text-primary-foreground"
                    size="lg"
                    disabled={loading}
                  >
                    <Mail className="mr-2 h-4 w-4" />
                    {loading ? "Enviando..." : "Enviar link de recuperação"}
                  </Button>
                </form>

                <p className="mt-8 text-center text-sm text-zinc-400">
                  Lembrou a senha?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("login");
                      setError("");
                    }}
                    className="font-semibold text-[#ff8a3d] hover:underline"
                  >
                    Voltar ao login
                  </button>
                </p>
              </>
            )}
          </div>

          <div className="mt-6 flex justify-center">
            <Button
              type="button"
              variant="ghost"
              className="text-zinc-400 hover:bg-white/5 hover:text-white"
              onClick={goToMarketing}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar ao site
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
