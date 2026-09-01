import { useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { clearAdminSession, getAdminToken } from "@/lib/adminSession";
import AdminLoginPage from "@/screens/admin/AdminLoginPage";

/**
 * Protege /admin com sessão própria (e-mail/senha do .env).
 * Não usa o login de cliente em /login.
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"loading" | "ok" | "login">("loading");

  useEffect(() => {
    if (!getAdminToken()) {
      setState("login");
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        await api.admin.me();
        if (!cancelled) setState("ok");
      } catch {
        clearAdminSession();
        if (!cancelled) setState("login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050506]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (state === "login") {
    return <AdminLoginPage />;
  }

  return <>{children}</>;
}
