"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AboutAtmosphere } from "@/components/about/AboutAtmosphere";
import { AboutHeroField } from "@/components/about/AboutHeroField";
import { AboutHeroLamp } from "@/components/about/AboutHeroLamp";
import { AboutClients } from "@/components/about/AboutClients";
import { AboutMetrics } from "@/components/about/AboutMetrics";
import { AboutMethodology } from "@/components/about/AboutMethodology";
import { Button } from "@/components/ui/Button";
import { Reveal } from "@/components/ui/Reveal";

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

export function AboutContent() {
  const reduceMotion = useReducedMotion();

  return (
    <main className="overflow-x-clip">
      <section className="about-hero">
        <AboutHeroField />

        <div className="about-hero__grid">
          <div className="flex w-full min-w-0 items-center">
            <div className="about-hero__copy">
              <motion.p
                className="about-hero__eyebrow"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.6,
                  ease: EASE_OUT_EXPO,
                }}
              >
                Sobre nós
              </motion.p>
              <motion.h1
                className="about-hero__title"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.6,
                  ease: EASE_OUT_EXPO,
                  delay: reduceMotion ? 0 : 0.08,
                }}
              >
                <span>Escalando seu negócio</span>
                <span className="about-hero__title-muted">
                  de forma inteligente.
                </span>
              </motion.h1>
              <motion.div
                className="about-hero__body"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: reduceMotion ? 0 : 0.6,
                  ease: EASE_OUT_EXPO,
                  delay: reduceMotion ? 0 : 0.28,
                }}
              >
                <p>
                  A 4Scale Marketing e Tecnologia é uma empresa brasileira
                  especializada em desenvolver soluções que unem estratégia,
                  criatividade e tecnologia para impulsionar o crescimento de
                  empresas. Acreditamos que resultados consistentes são
                  construídos por meio de decisões inteligentes, processos
                  eficientes e inovação contínua.
                </p>
                <p>
                  Com atuação em marketing digital, inteligência artificial,
                  automação, desenvolvimento de software, business intelligence
                  e integrações, criamos ecossistemas capazes de transformar
                  desafios em oportunidades e operações em máquinas de
                  crescimento.
                </p>
                <p>
                  Mais do que entregar serviços, construímos soluções escaláveis
                  que ajudam nossos clientes a otimizar processos, aumentar a
                  performance e acelerar seus resultados em um mercado cada vez
                  mais digital.
                </p>
              </motion.div>
            </div>
          </div>

          <AboutHeroLamp />
        </div>
      </section>

      <AboutMetrics />
      <AboutMethodology />

      <section className="about-cta about-glow-edges about-glow-edges--top-only">
        <AboutAtmosphere intensity="grid" glow glowPosition="left" />

        <div className="about-cta__inner">
          <Reveal
            y={20}
            transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
            className="w-full max-w-3xl"
          >
            <h2 className="section-heading">
              <span className="block">Pronto para crescer</span>
              <span className="section-heading__muted">com inteligência?</span>
            </h2>
            <p className="section-lead">
              Conheça a equipe por trás da 4SEO e descubra como transformamos
              marketing, tecnologia e dados em soluções que impulsionam o
              crescimento de empresas pelo Brasil.
            </p>
          </Reveal>

          <AboutClients />

          <Reveal
            y={16}
            transition={{ duration: 0.55, ease: EASE_OUT_EXPO, delay: 0.08 }}
            className="w-full max-w-3xl"
          >
            <div className="about-cta__actions">
              <Button
                href="https://4scale.com.br/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-7 py-3"
              >
                Conheça a 4Scale
              </Button>
            </div>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
