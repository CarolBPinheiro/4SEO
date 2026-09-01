import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  LifeBuoy,
  HeartPulse,
  ScrollText,
  LogOut,
  Radio,
} from "lucide-react";
import { clearAdminSession, getAdminEmail } from "@/lib/adminSession";

const groups = [
  {
    title: "Operação",
    items: [
      { to: "/admin", end: true, label: "Visão geral", icon: LayoutDashboard },
      { to: "/admin/users", label: "Assinantes", icon: Users },
      { to: "/admin/subscriptions", label: "Planos", icon: CreditCard },
    ],
  },
  {
    title: "Suporte",
    items: [{ to: "/admin/tickets", label: "Chamados", icon: LifeBuoy }],
  },
  {
    title: "Sistema",
    items: [
      { to: "/admin/health", label: "Saúde", icon: HeartPulse },
      { to: "/admin/audit", label: "Audit log", icon: ScrollText },
    ],
  },
];

export default function AdminLayout() {
  const navigate = useNavigate();
  const email = getAdminEmail();

  return (
    <div className="min-h-screen bg-[#050506] text-white">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(255,117,26,0.12),transparent_42%)]" />
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[248px] flex-col border-r border-white/10 bg-black/70 backdrop-blur-xl">
        <div className="px-5 pb-5 pt-6">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ff751a]/15 text-[#ff8a3d]">
              <Radio className="h-4 w-4" />
            </span>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#ff8a3d]">
                Centro de controle
              </p>
              <p className="text-sm font-semibold">4SEO Admin</p>
            </div>
          </div>
          <p className="mt-3 truncate text-xs text-zinc-500">{email}</p>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
          {groups.map((group) => (
            <div key={group.title}>
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                {group.title}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
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
              </div>
            </div>
          ))}
        </nav>
        <div className="space-y-1 border-t border-white/10 px-3 py-4">
          <button
            type="button"
            onClick={() => {
              clearAdminSession();
              navigate("/admin/login");
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-zinc-400 hover:bg-white/5 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </div>
      </aside>
      <main className="relative ml-[248px] min-h-screen p-8">
        <Outlet />
      </main>
    </div>
  );
}
