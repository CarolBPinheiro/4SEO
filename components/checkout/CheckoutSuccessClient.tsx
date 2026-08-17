"use client";

import { useEffect, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";
import { Button } from "@/components/ui/Button";

const BILLING_REF_KEY = "4seo_billing_ref";

function getAppLoginUrl(ref: string | null): string {
  const base =
    (process.env.NEXT_PUBLIC_APP_URL || "http://localhost:8080").replace(
      /\/+$/,
      "",
    ) + "/login";
  if (!ref) {
    return base;
  }
  const params = new URLSearchParams({ billingRef: ref });
  return `${base}?${params.toString()}`;
}

export function CheckoutSuccessClient() {
  const searchParams = useSearchParams();
  const ref = useMemo(() => {
    const value = searchParams.get("ref")?.trim() || "";
    return value.startsWith("4seo_") ? value : null;
  }, [searchParams]);

  useEffect(() => {
    if (!ref) {
      return;
    }
    try {
      sessionStorage.setItem(BILLING_REF_KEY, ref);
    } catch {
      // sessionStorage indisponível
    }
  }, [ref]);

  return (
    <CheckoutShell
      title="Pagamento recebido"
      description={
        ref
          ? "Pagamento recebido. Crie sua conta ou faça login para vincular a assinatura. O acesso aos recursos só libera com assinatura confirmada."
          : "Pagamento recebido. Em instantes a assinatura pode ser ativada. Faça login na sua conta para acessar a plataforma."
      }
      tone="success"
      actions={
        <Button
          href={getAppLoginUrl(ref)}
          variant="primary"
          className="rounded-full"
        >
          Entrar no 4SEO
        </Button>
      }
    />
  );
}
