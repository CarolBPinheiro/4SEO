"use client";

import { FAQSection } from "@/components/ui/faqsection";
import { getAppTrialUrl } from "@/lib/site";

const faqsLeft = [
  {
    question: "Preciso cadastrar cartão para o teste gratuito?",
    answer:
      "Não. O teste de 7 dias não exige cartão de crédito. Você pode explorar a plataforma e cancelar a qualquer momento.",
  },
  {
    question: "Com quais plataformas o 4SEO se integra?",
    answer:
      "Atualmente suportamos Shopify, Nuvemshop, VTEX e Loja Integrada. Conecte a loja e sincronize o catálogo para começar a otimizar.",
  },
  {
    question: "Quanto tempo leva para começar a usar?",
    answer:
      "Na maioria dos casos, a conexão da loja e a primeira análise levam poucos minutos. Depois disso, você já pode revisar sugestões e acompanhar métricas.",
  },
];

const faqsRight = [
  {
    question: "A IA altera meus produtos automaticamente?",
    answer:
      "As sugestões de otimização ficam sob o seu controle. Você revisa e aplica as melhorias conforme a estratégia da loja.",
  },
  {
    question: "Posso trocar de plano depois?",
    answer:
      "Sim. Os planos Start, Pro e Scale variam por volume de produtos e pesquisas. Há opções mensal, trimestral, semestral e anual, e você pode ajustar conforme o crescimento do catálogo.",
  },
  {
    question: "Como funciona o cancelamento?",
    answer:
      "Não há fidelidade nem multa. Cancele quando quiser pelo painel; o acesso permanece até o fim do ciclo já pago.",
  },
];

export function FAQ() {
  return (
    <FAQSection
      title="Perguntas frequentes"
      subtitle="Suporte & Dúvidas"
      description="Respostas objetivas antes de começar o teste gratuito."
      buttonLabel="Começar teste grátis →"
      buttonHref={getAppTrialUrl()}
      faqsLeft={faqsLeft}
      faqsRight={faqsRight}
    />
  );
}
