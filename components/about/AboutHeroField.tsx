"use client";

import { BackgroundRippleEffect } from "@/components/ui/background-ripple-effect";
import { Parallax, ParallaxTarget } from "@/components/ui/parallax-scrolling";
import { cn } from "@/lib/utils";

type AboutHeroFieldProps = {
  className?: string;
};

/**
 * Fundo interativo do hero Sobre — wireframe em perspectiva,
 * glow laranja da marca, grid ripple e parallax sutil da malha (~0.2×).
 */
export function AboutHeroField({ className }: AboutHeroFieldProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        className,
      )}
    >
      <div className="absolute inset-0 bg-[var(--background)]" />

      <div className="about-hero-field__glow" />

      <Parallax
        start={8}
        end={-8}
        disable="mobile"
        scrub={1.2}
        className="absolute inset-0 will-change-transform"
      >
        <ParallaxTarget className="absolute inset-0">
          <div className="about-hero-field__room">
            <div className="about-hero-field__plane about-hero-field__plane--ceiling" />
            <div className="about-hero-field__plane about-hero-field__plane--floor" />
            <div className="about-hero-field__plane about-hero-field__plane--left" />
            <div className="about-hero-field__plane about-hero-field__plane--right" />
            <div className="about-hero-field__plane about-hero-field__plane--back" />
          </div>
        </ParallaxTarget>
      </Parallax>

      <div className="about-hero-field__ripple pointer-events-auto absolute inset-0">
        <BackgroundRippleEffect
          tone="brand"
          rows={14}
          cols={28}
          cellSize={52}
          gridClassName="about-hero-field__grid mask-radial-from-15% mask-radial-at-center"
        />
      </div>

      <div className="about-hero-field__vignette" />
      <div className="about-grain absolute inset-0 opacity-60" />
    </div>
  );
}
