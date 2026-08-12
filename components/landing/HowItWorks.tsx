"use client";

import { Link2, BrainCircuit, Rocket, type LucideIcon } from "lucide-react";
import { Parallax } from "@/components/ui/parallax-scrolling";
import { Reveal } from "@/components/ui/Reveal";
import { GlowCard } from "@/components/ui/spotlight-card";

type Step = {
  label: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

const STEPS: Step[] = [
  {
    label: "FIG 01",
    title: "Conecte sua loja",
    description:
      "Shopify, Nuvemshop, VTEX ou Loja Integrada. Sincronize o catálogo em minutos — sem migração complexa e sem depender de agência.",
    icon: Link2,
  },
  {
    label: "FIG 02",
    title: "Veja o que priorizar",
    description:
      "A IA organiza o cenário da loja e aponta o que move o ranking primeiro — sem planilha e sem achismo.",
    icon: BrainCircuit,
  },
  {
    label: "FIG 03",
    title: "Execute e acompanhe",
    description:
      "Aplique as melhorias no catálogo e acompanhe a evolução enquanto a loja continua vendendo.",
    icon: Rocket,
  },
];

export function HowItWorks() {
  return (
    <section
      id="como-funciona"
      className="relative scroll-mt-28 overflow-hidden px-4 py-20 lg:py-28"
      aria-labelledby="how-it-works-heading"
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[#050506]" />

      <div className="relative mx-auto max-w-6xl">
        <Reveal>
          <Parallax
            start={8}
            end={-8}
            disable="mobile"
            scrub={0.55}
            className="will-change-transform"
          >
            <h2 id="how-it-works-heading" className="section-heading max-w-4xl">
              <span className="block">Como o 4SEO funciona</span>
              <span className="section-heading__muted">em três passos.</span>
            </h2>
            <p className="section-lead">
              Um fluxo simples: conectar, priorizar e executar — sem transformar
              SEO em um segundo emprego.
            </p>
          </Parallax>
        </Reveal>

        <ol className="mt-14 grid list-none grid-cols-1 items-stretch gap-4 p-0 md:grid-cols-3 md:gap-5">
          {STEPS.map((item, index) => {
            const Icon = item.icon;
            return (
              <li key={item.label} className="list-none h-full">
                <Reveal delay={0.08 + index * 0.07} className="h-full">
                  <Parallax
                    start={14}
                    end={-14}
                    disable="mobileLandscape"
                    scrub={0.75}
                    className="h-full will-change-transform"
                  >
                    <GlowCard className="min-h-[280px] p-6 sm:min-h-[320px] sm:p-7">
                      <article className="flex h-full flex-col">
                        <p className="text-[11px] font-medium tracking-[0.16em] text-white/35 uppercase">
                          {item.label}
                        </p>
                        <div className="flex flex-1 items-center justify-center py-10">
                          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03]">
                            <Icon className="h-6 w-6 text-white/55" aria-hidden />
                          </div>
                        </div>
                        <div className="mt-auto">
                          <h3 className="text-lg font-semibold tracking-tight text-white sm:text-xl">
                            {item.title}
                          </h3>
                          <p className="mt-2 text-[15px] leading-relaxed tracking-[-0.01em] text-white/55 sm:text-[17px]">
                            {item.description}
                          </p>
                        </div>
                      </article>
                    </GlowCard>
                  </Parallax>
                </Reveal>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
