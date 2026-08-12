import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  HeartPulse,
  ScrollText,
  Info,
  LogOut,
  ArrowLeft,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const nav = [
  { to: "/admin", end: true, label: "Visão geral", icon: LayoutDashboard },
  { to: "/admin/users", label: "Usuários", icon: Users },
  { to: "/admin/subscriptions", label: "Assinaturas", icon: CreditCard },
  { to: "/admin/health", label: "Saúde", icon: HeartPulse },
  { to: "/admin/audit", label: "Audit log", icon: ScrollText },
  { to: "/admin/conteudo", label: "Conteúdo", icon: Info },
];

export default function AdminLayout() {
  const navigate = useNavigate();
  const { signOut, user } = useAuth();

  return (
    <div className="flex min-h-screen bg-[#050506] text-white">
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[230px] flex-col border-r border-white/10 bg-black/60">
        <div className="px-5 pb-4 pt-6">
          <p className="text-xs font-semibold tracking-[0.18em] text-[#ff8a3d] uppercase">
            4SEO Admin
          </p>
          <p className="mt-2 truncate text-xs text-zinc-500">{user?.email}</p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-2">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-zinc-400 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="space-y-1 border-t border-white/10 px-3 py-4">
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar ao app
          </button>
          <button
            type="button"
            onClick={async () => {
              await signOut();
              navigate("/login");
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </div>
      </aside>
      <main className="ml-[230px] flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
