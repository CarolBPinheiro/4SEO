"use client";

import { ArrowRight } from "lucide-react";
import { HeroBeams } from "@/components/landing/HeroBeams";
import { Parallax, ParallaxTarget } from "@/components/ui/parallax-scrolling";

/**
 * Hero Precision AI — dark + bronze, tipografia e CTAs alinhados à logo.
 * Fundo: barras em movimento (vídeo) via HeroBeams. Navbar permanece intacta.
 */
export function Hero() {
  return (
    <section className="relative flex min-h-[min(100svh,880px)] flex-col items-center justify-center overflow-hidden pb-16 sm:pb-24">
      <Parallax
        className="pointer-events-none absolute inset-0 overflow-hidden"
        start={0}
        end={28}
        scrollStart="top top"
        scrollEnd="bottom top"
        scrub
        disable="mobile"
      >
        <ParallaxTarget className="absolute top-0 left-0 h-[130%] w-full">
          <HeroBeams />
        </ParallaxTarget>
      </Parallax>

      <div aria-hidden className="ray-hero-bottom-fade" />

      <Parallax
        className="ray-hero-text relative z-10 flex w-full max-w-5xl flex-col items-center px-4 text-center will-change-transform"
        start={4}
        end={-6}
        scrollStart="top top"
        scrollEnd="bottom top"
        scrub={0.55}
        disable="mobile"
      >
        <p className="ray-fade-in mb-6 text-xs font-medium tracking-[0.18em] text-brand uppercase sm:mb-7 sm:text-[13px]">
          SEO Automático Inteligente
        </p>

        <h1 className="ray-fade-in text-[clamp(2.25rem,5.5vw,4.75rem)] font-bold leading-[1.08] tracking-[-0.02em] text-white">
          <span className="block">
            O SEO do seu e{"\u2011"}commerce
          </span>
          <span className="mt-2 block font-semibold tracking-[-0.015em] text-white/75">
            impulsionado por IA.
          </span>
        </h1>

        <p className="ray-fade-in-stagger mt-8 max-w-[40rem] text-[17px] leading-relaxed tracking-[-0.01em] text-white/65 text-balance sm:mt-9 sm:text-lg">
          Otimize produtos, supere concorrentes e alcance o topo das buscas —
          em um só lugar.
        </p>

        <div className="ray-fade-in-stagger mt-11 flex w-full flex-col items-center gap-3 sm:mt-12">
          <div className="flex w-full flex-col items-center gap-3 sm:w-auto sm:flex-row sm:gap-3.5">
            <a href="#planos" className="btn-hero-primary w-full sm:w-auto">
              Testar 7 dias grátis
              <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
            <a href="#produto" className="btn-hero-secondary w-full sm:w-auto">
              Ver demonstração
            </a>
          </div>
          <p className="text-[13px] tracking-tight text-muted">
            Sem cartão de crédito
          </p>
        </div>
      </Parallax>
    </section>
  );
}
