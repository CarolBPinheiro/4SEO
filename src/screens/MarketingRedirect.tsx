import { useEffect } from "react";
import { getMarketingUrl } from "@/lib/site";

/**
 * A landing pública vive no site Next.js (UX/UI atual).
 * Esta rota no app autenticado apenas redireciona para o marketing.
 */
export default function MarketingRedirect() {
  const marketingUrl = getMarketingUrl();

  useEffect(() => {
    window.location.replace(marketingUrl);
  }, [marketingUrl]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <p className="text-sm text-muted-foreground" role="status">
        Redirecionando para o site 4SEO…
      </p>
    </div>
  );
}
