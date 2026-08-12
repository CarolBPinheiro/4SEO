import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useBilling } from "@/contexts/BillingContext";
import { useStore } from "@/contexts/StoreContext";
import {
  LayoutGrid,
  TrendingUp,
  Hourglass,
  Puzzle,
  ScanSearch,
  FileText,
  HelpCircle,
  LogOut,
  Store,
  CheckCircle,
  XCircle,
  Lock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutGrid, requiresSubscription: false },
  { to: "/termos", label: "Termos de Pesquisa", icon: TrendingUp, requiresSubscription: true },
  { to: "/historico", label: "Histórico", icon: Hourglass, requiresSubscription: true },
  { to: "/integracoes", label: "Integrações", icon: Puzzle, requiresSubscription: true },
  { to: "/analise", label: "Análise", icon: ScanSearch, requiresSubscription: true },
  { to: "/panorama", label: "Panorama SEO", icon: FileText, requiresSubscription: true },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const { hasActiveSubscription, loading: billingLoading, subscribeUrl } = useBilling();
  const { store, connected } = useStore();

  const handleSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-background">
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[220px] flex-shrink-0 flex-col border-r border-border bg-[#050506]">
        <div className="px-5 pb-4 pt-6">
          <div className="mb-2 text-xs font-semibold tracking-[0.18em] text-[#ff8a3d] uppercase">
            4SEO
          </div>
          <img src="/logo.png" alt="4SEO" className="h-12 w-auto" />
        </div>

        <nav className="flex-1 space-y-1 px-3 py-2">
          {navItems.map((item) => {
            const locked =
              item.requiresSubscription && !billingLoading && !hasActiveSubscription;

            if (locked) {
              return (
                <a
                  key={item.to}
                  href={subscribeUrl}
                  title="Requer assinatura ativa"
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground/55 transition-all hover:bg-muted/30"
                >
                  <item.icon className="h-[18px] w-[18px]" />
                  <span className="flex-1">{item.label}</span>
                  <Lock className="h-3.5 w-3.5 opacity-70" aria-hidden />
                </a>
              );
            }

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                    isActive
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`
                }
              >
                <item.icon className="h-[18px] w-[18px]" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="space-y-1 px-3 pb-4">
          <button
            type="button"
            onClick={() => {}}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-muted/50 hover:text-foreground"
          >
            <HelpCircle className="h-[18px] w-[18px]" />
            Ajuda e Suporte
          </button>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-muted/50 hover:text-foreground"
          >
            <LogOut className="h-[18px] w-[18px]" />
            Sair
          </button>
          <div className="mt-2 px-3">
            <Badge variant="outline" className="text-[10px] font-normal">
              v:2.1
            </Badge>
          </div>
        </div>
      </aside>

      <div className="ml-[220px] flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15">
              <Store className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                {hasActiveSubscription
                  ? connected
                    ? store?.name || "Loja"
                    : "Loja não conectada"
                  : "Conta sem assinatura"}
              </p>
              <p className="text-xs text-muted-foreground">
                {hasActiveSubscription
                  ? connected
                    ? store?.url
                    : "Conecte sua loja"
                  : "Recursos bloqueados até ativar o plano"}
              </p>
            </div>
          </div>

          {hasActiveSubscription ? (
            connected ? (
              <Badge className="gap-1.5 rounded-lg border-green-500 bg-green-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-600">
                <CheckCircle className="h-4 w-4" />
                Conectada
              </Badge>
            ) : (
              <Badge className="gap-1.5 rounded-lg border-red-500/40 bg-red-500/20 px-4 py-1.5 text-sm font-medium text-red-400 hover:bg-red-500/25">
                <XCircle className="h-4 w-4" />
                Desconectada
              </Badge>
            )
          ) : (
            <Badge className="gap-1.5 rounded-lg border-primary/40 bg-primary/15 px-4 py-1.5 text-sm font-medium text-primary">
              <Lock className="h-4 w-4" />
              Assinatura necessária
            </Badge>
          )}
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
