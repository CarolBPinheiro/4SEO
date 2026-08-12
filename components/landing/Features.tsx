"use client";

import {
  Gauge,
  Layers,
  ShieldCheck,
  Timer,
  type LucideIcon,
} from "lucide-react";
import { Parallax } from "@/components/ui/parallax-scrolling";
import { Reveal } from "@/components/ui/Reveal";
import { GlowCard } from "@/components/ui/spotlight-card";

type Outcome = {
  label: string;
  title: string;
  description: string;
  icon: LucideIcon;
  className: string;
  featured?: boolean;
};

const OUTCOMES: Outcome[] = [
  {
    label: "FIG 01",
    title: "Menos tempo em SEO manual",
    description:
      "Troque horas de ajuste repetitivo por um fluxo guiado — você foca em vender, não em formatar metadados.",
    icon: Timer,
    className: "lg:col-start-1 lg:row-start-1",
  },
  {
    label: "FIG 02",
    title: "Prioridade com impacto",
    description:
      "Em vez de uma lista infinita de tarefas, você vê o que corrigir primeiro para mover o orgânico.",
    icon: Gauge,
    className: "lg:col-start-2 lg:row-start-1",
  },
  {
    label: "FIG 03",
    title: "Escala no catálogo",
    description:
      "Otimize centenas ou milhares de produtos sem aumentar equipe nem abrir planilha produto a produto.",
    icon: Layers,
    className:
      "md:col-span-2 lg:col-span-1 lg:col-start-3 lg:row-start-1 lg:row-span-2",
    featured: true,
  },
  {
    label: "FIG 04",
    title: "IA com você no controle",
    description:
      "Sugestões prontas para revisar e aplicar. Nada sobe no catálogo sem a sua aprovação.",
    icon: ShieldCheck,
    className: "md:col-span-2 lg:col-span-2 lg:col-start-1 lg:row-start-2",
  },
];

export function Features() {
  return (
    <section
      id="resultados"
      className="relative scroll-mt-28 overflow-hidden px-4 py-20 lg:py-28"
      aria-labelledby="outcomes-heading"
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
            <h2 id="outcomes-heading" className="section-heading max-w-4xl">
              <span className="block">O que muda</span>
              <span className="section-heading__muted">na operação da loja</span>
            </h2>
            <p className="section-lead">
              Não é só mais um relatório. É SEO que cabe no dia a dia do
              e-commerce — com escala, prioridade e controle.
            </p>
          </Parallax>
        </Reveal>

        <div className="mt-14 grid auto-rows-fr grid-cols-1 items-stretch gap-4 md:grid-cols-2 md:gap-5 lg:grid-cols-3 lg:grid-rows-2">
          {OUTCOMES.map((outcome, index) => {
            const Icon = outcome.icon;
            return (
              <Reveal
                key={outcome.title}
                delay={0.08 + index * 0.06}
                className={["h-full", outcome.className].join(" ")}
              >
                <GlowCard
                  className={[
                    "h-full p-6 sm:p-7",
                    outcome.featured
                      ? "min-h-[320px] lg:min-h-full"
                      : "min-h-[240px]",
                  ].join(" ")}
                >
                  <article className="flex h-full flex-col">
                    <p className="text-[11px] font-medium tracking-[0.16em] text-white/35 uppercase">
                      {outcome.label}
                    </p>
                    <div
                      className={[
                        "flex flex-1 items-center justify-center",
                        outcome.featured ? "py-12" : "py-8",
                      ].join(" ")}
                    >
                      <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03]">
                        <Icon
                          className={[
                            "h-6 w-6",
                            outcome.featured
                              ? "text-brand-light"
                              : "text-white/55",
                          ].join(" ")}
                          aria-hidden
                        />
                      </div>
                    </div>
                    <div className="mt-auto">
                      <h3 className="text-lg font-semibold tracking-tight text-white sm:text-xl">
                        {outcome.title}
                      </h3>
                      <p
                        className={[
                          "mt-2 leading-relaxed tracking-[-0.01em] text-white/55",
                          outcome.featured
                            ? "text-[15px] sm:text-[17px]"
                            : "text-[15px] sm:text-base",
                        ].join(" ")}
                      >
                        {outcome.description}
                      </p>
                    </div>
                  </article>
                </GlowCard>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
