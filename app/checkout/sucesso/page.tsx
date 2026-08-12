import type { Metadata } from "next";
import { Suspense } from "react";
import { CheckoutSuccessClient } from "@/components/checkout/CheckoutSuccessClient";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";

export const metadata: Metadata = {
  title: "Assinatura confirmada | 4SEO",
  description: "Seu pagamento foi processado. Bem-vindo ao 4SEO.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function CheckoutSuccessPage() {
  return (
    <Suspense
      fallback={
        <CheckoutShell
          title="Pagamento recebido"
          description="Confirmando sua assinatura…"
          tone="success"
        />
      }
    >
      <CheckoutSuccessClient />
    </Suspense>
  );
}
