import { Navigate } from "react-router-dom";
import { useBilling } from "@/contexts/BillingContext";

type Props = {
  children: React.ReactNode;
  /** full = assinatura paga; trial = full ou avaliação */
  level?: "full" | "trial";
};

/**
 * full → recursos pagos (Termos, Histórico, Panorama…)
 * trial → Dashboard, Análise e Integrações (pago ou avaliação)
 */
export default function SubscriptionRoute({ children, level = "full" }: Props) {
  const { hasFullAccess, canUseAppPreview, loading } = useBilling();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (level === "trial") {
    if (!canUseAppPreview) {
      return <Navigate to="/trial" replace />;
    }
    return <>{children}</>;
  }

  if (!hasFullAccess) {
    return (
      <Navigate
        to={canUseAppPreview ? "/dashboard" : "/trial"}
        replace
        state={{ subscriptionRequired: true }}
      />
    );
  }

  return <>{children}</>;
}
