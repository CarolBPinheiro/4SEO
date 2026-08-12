import type { Metadata } from "next";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "Checkout expirado | 4SEO",
  description: "Esta sessão de pagamento expirou. Inicie um novo checkout para continuar.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function CheckoutExpiredPage() {
  return (
    <CheckoutShell
      title="Sessão expirada"
      description="O link de pagamento expirou por segurança. Selecione o plano novamente para gerar um novo checkout."
      tone="danger"
      actions={
        <Button href="/#planos" variant="primary" className="rounded-full">
          Gerar novo checkout
        </Button>
      }
    />
  );
}
