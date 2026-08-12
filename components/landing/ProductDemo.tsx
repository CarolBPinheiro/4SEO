"use client";

import { ContainerScroll } from "@/components/ui/container-scroll-animation";

export function ProductDemo() {
  return (
    <section
      id="produto"
      className="relative scroll-mt-24 overflow-hidden"
      aria-labelledby="product-demo-heading"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[#050506]"
      />
      <div
        aria-hidden
        className="ray-hero-grid pointer-events-none absolute inset-0 opacity-70"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute top-[22%] left-[12%] h-64 w-64 rounded-full bg-[rgba(255,117,26,0.045)] blur-[100px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute right-[10%] bottom-[18%] h-72 w-72 rounded-full bg-[rgba(255,138,61,0.03)] blur-[120px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(5,5,6,0)_30%,rgba(5,5,6,0.55)_85%,rgba(5,5,6,0.9)_100%)]"
      />

      <div className="relative flex flex-col overflow-hidden">
        <ContainerScroll
          titleComponent={
            <div className="mx-auto mb-4 max-w-5xl px-4">
              <h2
                id="product-demo-heading"
                className="text-[clamp(1.5rem,4.2vw,3.25rem)] font-bold leading-[1.1] tracking-[-0.02em] text-white"
              >
                <span className="block whitespace-nowrap">
                  Otimize e acompanhe o ranking
                </span>
                <span className="mt-1.5 block whitespace-nowrap font-semibold tracking-[-0.015em] text-white/75">
                  em um só fluxo.
                </span>
              </h2>
              <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed tracking-[-0.01em] text-white/65 sm:text-lg">
                Veja a plataforma em ação: do catálogo conectado às otimizações
                prontas para aplicar.
              </p>
            </div>
          }
        >
          <video
            className="mx-auto h-full w-full rounded-2xl object-cover object-left-top"
            src="/videos/4SEO.mp4"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            aria-label="Demonstração da plataforma 4SEO"
          />
        </ContainerScroll>
      </div>
    </section>
  );
}
