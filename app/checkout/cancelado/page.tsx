import type { Metadata } from "next";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "Checkout cancelado | 4SEO",
  description: "O checkout foi cancelado. Você pode escolher outro plano quando quiser.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function CheckoutCanceledPage() {
  return (
    <CheckoutShell
      title="Checkout cancelado"
      description="Nenhuma cobrança foi realizada. Quando quiser, escolha um plano novamente e retome o pagamento."
      tone="warning"
      actions={
        <Button href="/#planos" variant="primary" className="rounded-full">
          Escolher plano
        </Button>
      }
    />
  );
}
