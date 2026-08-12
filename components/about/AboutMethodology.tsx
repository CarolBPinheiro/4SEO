"use client";

import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";
import { useRef } from "react";
import { AboutAtmosphere } from "@/components/about/AboutAtmosphere";
import { GlowCard } from "@/components/ui/spotlight-card";
import { Reveal } from "@/components/ui/Reveal";

const PILLARS = [
  {
    title: "Aquisição",
    description:
      "Atrair as pessoas certas através de mídias, conteúdo e SEO.",
  },
  {
    title: "Conversão",
    description:
      "Transformar tráfego em oportunidades e vendas com funis otimizados.",
  },
  {
    title: "Retenção",
    description:
      "Fortalecer relacionamento e recompra com CRM e automações.",
  },
  {
    title: "Escala",
    description:
      "Ampliar resultados com dados, tecnologia e mensuração precisa.",
  },
] as const;

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

export function AboutMethodology() {
  const sectionRef = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start 70%", "end 40%"],
  });

  const lineProgress = useTransform(
    scrollYProgress,
    [0, 1],
    reduceMotion ? [1, 1] : [0, 1],
  );

  return (
    <section
      ref={sectionRef}
      className="about-methodology about-glow-edges about-glow-edges--bottom-only"
      aria-labelledby="about-methodology-heading"
    >
      <AboutAtmosphere intensity="strong" glow glowPosition="right" />

      <div className="about-methodology__inner">
        <Reveal y={20} transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}>
          <h2
            id="about-methodology-heading"
            className="section-heading max-w-3xl"
          >
            <span className="block">A Metodologia 4Scale</span>
            <span className="section-heading__muted">
              Um sistema interligado de crescimento
            </span>
          </h2>
          <p className="section-lead">
            Aquisição flui para conversão, retenção e escala — quatro etapas
            conectadas, não blocos isolados.
          </p>
        </Reveal>

        <div className="about-methodology__track">
          <div className="about-methodology__line" aria-hidden>
            <motion.div
              className="about-methodology__line-progress about-methodology__line-progress--x"
              style={{ scaleX: lineProgress }}
            />
            <motion.div
              className="about-methodology__line-progress about-methodology__line-progress--y"
              style={{ scaleY: lineProgress }}
            />
          </div>

          <ol className="about-methodology__steps">
            {PILLARS.map((pillar, index) => (
              <li key={pillar.title} className="about-methodology__step">
                <Reveal
                  y={24}
                  transition={{
                    duration: 0.7,
                    ease: EASE_OUT_EXPO,
                    delay: 0.06 * index,
                  }}
                  className="about-methodology__step-inner"
                >
                  <div className="about-methodology__node" aria-hidden>
                    <span className="about-methodology__node-dot" />
                  </div>
                  <GlowCard
                    className="about-methodology__card !rounded-[12px]"
                    customSize
                  >
                    <p className="about-methodology__index">
                      {String(index + 1).padStart(2, "0")}
                    </p>
                    <h3 className="about-methodology__title">{pillar.title}</h3>
                    <p className="about-methodology__desc">
                      {pillar.description}
                    </p>
                  </GlowCard>
                </Reveal>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
