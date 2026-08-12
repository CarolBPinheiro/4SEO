import type { Metadata } from "next";
import { Suspense } from "react";
import { CheckoutInitiator } from "@/components/checkout/CheckoutInitiator";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";

export const metadata: Metadata = {
  title: "Checkout | 4SEO",
  description: "Finalize sua assinatura 4SEO com pagamento seguro via Asaas.",
  robots: {
    index: false,
    follow: false,
  },
};

function CheckoutFallback() {
  return (
    <CheckoutShell
      title="Preparando seu checkout"
      description="Validando o plano selecionado…"
    />
  );
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={<CheckoutFallback />}>
      <CheckoutInitiator />
    </Suspense>
  );
}
