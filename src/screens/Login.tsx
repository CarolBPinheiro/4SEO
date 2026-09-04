import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  LogIn,
  UserPlus,
  ArrowLeft,
  Mail,
  Lock,
  Eye,
  EyeOff,
  KeyRound,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { getMarketingUrl } from "@/lib/site";
import {
  claimPendingCheckout,
  persistBillingRef,
  readPendingBillingRef,
} from "@/lib/billingClaim";
import { fetchSubscription } from "@/contexts/BillingContext";
import { resolvePostAuthPath } from "@/lib/subscriptionAccess";
import { getValidationErrors, newPasswordSchema } from "@/lib/validation";

type AuthMode = "login" | "register" | "forgot" | "reset";

export default function Login() {
  const navigate = useNavigate();
  const {
    signIn,
    signUp,
    resetPassword,
    updatePassword,
    clearPasswordRecovery,
    signOut,
    user,
    loading: authLoading,
    passwordRecovery,
  } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [sessionCheck, setSessionCheck] = useState(true);
  const hasBillingRef = useMemo(() => !!readPendingBillingRef(), []);
  /** Evita resetar a sessão logo após login/cadastro bem-sucedido. */
  const continueAfterAuthRef = useRef(false);

  useEffect(() => {
    const ref = readPendingBillingRef();
    if (ref) {
      persistBillingRef(ref);
      setMode("register");
      return;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("intent") === "trial") {
      setMode("register");
    }
  }, []);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    // Link de recuperação: manter a sessão e exibir formulário de nova senha
    if (passwordRecovery) {
      setSessionCheck(false);
      setMode("reset");
      setError("");
      setMessage("");
      return;
    }

    if (!user) {
      setSessionCheck(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      // Fluxo Dropbox: cadastro/login acabou de autenticar → seguir para /trial ou app
      if (continueAfterAuthRef.current) {
        try {
          await claimPendingCheckout();
        } catch {
          // best-effort
        }
        let level: string | null = "none";
        try {
          const sub = await fetchSubscription();
          level = sub.accessLevel || "none";
        } catch {
          level = "none";
        }
        if (!cancelled) {
          navigate(resolvePostAuthPath(level), { replace: true });
        }
        return;
      }

      // Voltou à página inicial (Minha Conta /login) com sessão antiga:
      // - com trial/assinatura → dashboard
      // - sem trial → encerra sessão e mostra login limpo
      try {
        await claimPendingCheckout();
      } catch {
        // best-effort
      }
      let level: string | null = "none";
      try {
        const sub = await fetchSubscription();
        level = sub.accessLevel || "none";
      } catch {
        level = "none";
      }

      if (cancelled) {
        return;
      }

      if (level === "full" || level === "trial") {
        navigate("/dashboard", { replace: true });
        return;
      }

      await signOut();
      if (!cancelled) {
        setSessionCheck(false);
        setMode("login");
        setMessage("");
        setError("");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user, authLoading, passwordRecovery, navigate, signOut]);

  const showSessionGate =
    authLoading ||
    (sessionCheck && !!user && !passwordRecovery) ||
    continueAfterAuthRef.current;

  if (showSessionGate) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050506] text-sm text-zinc-400">
        {continueAfterAuthRef.current
          ? "Preparando sua conta…"
          : "Carregando…"}
      </div>
    );
  }

  const finishAuthAndClaim = async () => {
    try {
      await claimPendingCheckout();
    } catch {
      // best-effort
    }
    let level: string | null = "none";
    try {
      const sub = await fetchSubscription();
      level = sub.accessLevel || "none";
    } catch {
      level = "none";
    }
    navigate(resolvePostAuthPath(level), { replace: true });
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    // Marca antes do signIn para o useEffect não fazer signOut da sessão nova
    continueAfterAuthRef.current = true;
    const result = await signIn(email, password);
    setLoading(false);
    if (result.error) {
      setError(result.error);
      continueAfterAuthRef.current = false;
    } else {
      await finishAuthAndClaim();
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    continueAfterAuthRef.current = true;
    const result = await signUp(email, password);
    setLoading(false);

    if (result.error && !result.sessionCreated) {
      continueAfterAuthRef.current = false;
      if (result.reason === "existing_user") {
        setError(result.error);
        setMode("login");
        return;
      }
      if (result.reason === "email_confirmation") {
        setMessage(result.error);
        setMode("login");
        return;
      }
      setError(result.error);
      return;
    }

    if (result.error) {
      continueAfterAuthRef.current = false;
      setError(result.error);
      return;
    }

    await finishAuthAndClaim();
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

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");

    const parsed = newPasswordSchema.safeParse({ password, confirmPassword });
    if (!parsed.success) {
      const fieldErrors = getValidationErrors(parsed.error);
      setError(
        fieldErrors.confirmPassword ||
          fieldErrors.password ||
          "Verifique os campos da nova senha.",
      );
      return;
    }

    setLoading(true);
    continueAfterAuthRef.current = true;
    const result = await updatePassword(parsed.data.password);
    setLoading(false);

    if (result.error) {
      continueAfterAuthRef.current = false;
      setError(result.error);
      return;
    }

    setPassword("");
    setConfirmPassword("");
    setMessage("Senha atualizada com sucesso.");
    await finishAuthAndClaim();
  };

  const goToMarketing = () => {
    window.location.assign(getMarketingUrl());
  };

  const title =
    mode === "login"
      ? "Olá, que bom ver você de volta!"
      : mode === "register"
        ? "Comece sua jornada na 4SEO"
        : mode === "reset"
          ? "Defina sua nova senha"
          : "Recupere o acesso";

  const subtitle =
    mode === "login"
      ? "Entre na sua conta. O acesso aos recursos depende de uma assinatura ativa."
      : mode === "register"
        ? hasBillingRef
          ? "Finalize seu acesso para vincular o pagamento ao seu usuário."
          : "Crie sua conta e escolha o plano de avaliação em seguida."
        : mode === "reset"
          ? "Escolha uma senha forte para concluir a recuperação do acesso."
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
            <img src="/logo.png" alt="4SEO" className="h-14 w-auto" />
            <p className="mt-3 text-xs font-medium tracking-wide text-white uppercase">
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
                    className="h-12 w-full rounded-xl border border-white/15 bg-white/[0.06] font-semibold text-white hover:bg-white/10"
                    size="lg"
                    disabled={loading}
                    variant="ghost"
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    {loading
                      ? "Criando..."
                      : hasBillingRef
                        ? "Criar conta e vincular assinatura"
                        : "Continuar"}
                  </Button>
                </form>

                <p className="mt-8 text-center text-sm text-zinc-400">
                  Já tem uma conta?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("login");
                      setError("");
                      setMessage("");
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

            {mode === "reset" && (
              <>
                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-password" className="sr-only">
                      Nova senha
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="new-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Nova senha"
                        autoComplete="new-password"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10 pr-11"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
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
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password" className="sr-only">
                      Confirmar nova senha
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                      <Input
                        id="confirm-password"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="Confirmar nova senha"
                        autoComplete="new-password"
                        className="h-12 rounded-xl border-white/10 bg-white/[0.06] pl-10 pr-11"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        minLength={8}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                        aria-label={
                          showConfirmPassword ? "Ocultar senha" : "Mostrar senha"
                        }
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                  <p className="text-xs leading-relaxed text-zinc-500">
                    Use no mínimo 8 caracteres, com letras maiúsculas e minúsculas,
                    número e caractere especial.
                  </p>

                  <Button
                    type="submit"
                    className="btn-gradient mt-2 h-12 w-full rounded-xl font-semibold text-primary-foreground"
                    size="lg"
                    disabled={loading}
                  >
                    <KeyRound className="mr-2 h-4 w-4" />
                    {loading ? "Atualizando..." : "Atualizar senha"}
                  </Button>
                </form>

                <p className="mt-8 text-center text-sm text-zinc-400">
                  Link expirado?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      clearPasswordRecovery();
                      void signOut();
                      setMode("forgot");
                      setPassword("");
                      setConfirmPassword("");
                      setError("");
                      setMessage("");
                    }}
                    className="font-semibold text-[#ff8a3d] hover:underline"
                  >
                    Solicitar novo link
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
