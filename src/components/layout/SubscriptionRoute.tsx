import { Navigate } from "react-router-dom";
import { useBilling } from "@/contexts/BillingContext";

/**
 * Rotas que exigem assinatura ativa (categorias / recursos da plataforma).
 * Conta autenticada sem assinatura é redirecionada ao dashboard zerado.
 */
export default function SubscriptionRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { hasActiveSubscription, loading } = useBilling();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!hasActiveSubscription) {
    return <Navigate to="/dashboard" replace state={{ subscriptionRequired: true }} />;
  }

  return <>{children}</>;
}
