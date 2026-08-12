"use client";

import { Clock, TrendingDown, Layers, type LucideIcon } from "lucide-react";
import { Parallax } from "@/components/ui/parallax-scrolling";
import { Reveal } from "@/components/ui/Reveal";
import { GlowCard } from "@/components/ui/spotlight-card";

type PainPoint = {
  label: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

const PAIN_POINTS: PainPoint[] = [
  {
    label: "FIG 01",
    title: "Produtos sem otimização em escala",
    description:
      "Atualizar títulos, descrições e metadados de centenas de SKUs manualmente consome tempo e gera inconsistência.",
    icon: Layers,
  },
  {
    label: "FIG 02",
    title: "Concorrentes ganhando posição",
    description:
      "Sem visibilidade do mercado, oportunidades de ranking passam despercebidas enquanto rivais sobem nas buscas.",
    icon: TrendingDown,
  },
  {
    label: "FIG 03",
    title: "SEO manual lento e caro",
    description:
      "Processos fragmentados atrasam decisões e dificultam acompanhar o que realmente move o tráfego orgânico.",
    icon: Clock,
  },
];

export function Problem() {
  return (
    <section
      id="por-que"
      className="relative scroll-mt-28 overflow-hidden px-4 py-20 lg:py-28"
      aria-labelledby="problem-heading"
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
            <h2 id="problem-heading" className="section-heading max-w-4xl">
              <span className="block">O SEO do e-commerce</span>
              <span className="section-heading__muted">
                não deveria ser um gargalo.
              </span>
            </h2>
            <p className="section-lead">
              Enquanto você opera a loja, oportunidades de ranking se perdem em
              tarefas manuais e dados dispersos.
            </p>
          </Parallax>
        </Reveal>

        <div className="mt-14 grid grid-cols-1 items-stretch gap-4 md:grid-cols-3 md:gap-5">
          {PAIN_POINTS.map((point, index) => {
            const Icon = point.icon;
            return (
              <Reveal key={point.title} delay={0.08 + index * 0.06} className="h-full">
                <Parallax
                  start={14}
                  end={-14}
                  disable="mobileLandscape"
                  scrub={0.7}
                  className="h-full will-change-transform"
                >
                  <GlowCard className="min-h-[280px] p-6 sm:min-h-[320px] sm:p-7">
                    <article className="flex h-full flex-col">
                      <p className="text-[11px] font-medium tracking-[0.16em] text-white/35 uppercase">
                        {point.label}
                      </p>
                      <div className="flex flex-1 items-center justify-center py-10">
                        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03]">
                          <Icon className="h-6 w-6 text-white/55" aria-hidden />
                        </div>
                      </div>
                      <div className="mt-auto">
                        <h3 className="text-lg font-semibold tracking-tight text-white sm:text-xl">
                          {point.title}
                        </h3>
                        <p className="mt-2 text-[15px] leading-relaxed tracking-[-0.01em] text-white/55 sm:text-[17px]">
                          {point.description}
                        </p>
                      </div>
                    </article>
                  </GlowCard>
                </Parallax>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
