import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/apiClient";

/**
 * Protege /admin: exige sessão + allowlist no backend (ADMIN_EMAILS).
 * Sem RBAC — um único tipo de administrador.
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [state, setState] = useState<"loading" | "ok" | "denied">("loading");

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setState("denied");
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        await api.admin.me();
        if (!cancelled) setState("ok");
      } catch {
        if (!cancelled) setState("denied");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, authLoading]);

  if (authLoading || state === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050506]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (state === "denied") {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
