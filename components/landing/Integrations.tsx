"use client";

import { CustomersSection, type CustomerLogo } from "@/components/ui/customers-section";
import { Parallax } from "@/components/ui/parallax-scrolling";
import { Reveal } from "@/components/ui/Reveal";

const PLATFORMS: CustomerLogo[] = [
  {
    src: "https://cdn.simpleicons.org/shopify/ffffff",
    alt: "Shopify",
    name: "Shopify",
    height: 36,
  },
  {
    src: "/brands/nuvemshop.svg",
    alt: "Nuvemshop",
    name: "Nuvemshop",
    height: 36,
  },
  {
    src: "https://cdn.simpleicons.org/vtex/ffffff",
    alt: "VTEX",
    name: "VTEX",
    height: 36,
  },
  {
    src: "/brands/lojaintegrada.svg",
    alt: "Loja Integrada",
    name: "Loja Integrada",
    height: 36,
  },
];

export function Integrations() {
  return (
    <section
      id="integracoes"
      className="relative scroll-mt-28 overflow-hidden px-4 py-20 lg:py-28"
      aria-labelledby="integrations-heading"
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[#050506]" />

      <div className="relative">
        <Reveal>
          <Parallax
            start={8}
            end={-8}
            disable="mobile"
            scrub={0.55}
            className="will-change-transform"
          >
            <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
              <h2 id="integrations-heading" className="section-heading">
                <span className="block">Integrado com as</span>
                <span className="section-heading__muted">
                  maiores plataformas.
                </span>
              </h2>
              <p className="section-lead mx-auto">
                Conecte sua loja e deixe a IA cuidar do SEO enquanto você foca em
                vender.
              </p>
            </div>
          </Parallax>
        </Reveal>

        <Reveal delay={0.12}>
          <Parallax
            start={8}
            end={-8}
            disable="mobileLandscape"
            scrub={0.75}
            className="relative mt-12 w-screen max-w-[100vw] -translate-x-1/2 left-1/2 will-change-transform sm:mt-14 lg:mt-16"
          >
            <div
              aria-hidden
              className="pointer-events-none absolute top-1/2 left-1/2 h-56 w-[min(100%,48rem)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[rgba(255,117,26,0.06)] blur-[100px]"
            />

            <CustomersSection
              customers={PLATFORMS}
              className="relative w-full"
              aria-label="Plataformas compatíveis"
            />
          </Parallax>
        </Reveal>
      </div>
    </section>
  );
}
