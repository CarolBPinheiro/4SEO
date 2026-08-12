"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

type AboutHeroLampProps = {
  className?: string;
};

const EASE_CINEMA: [number, number, number, number] = [0.22, 1, 0.36, 1];

const LOGO_SRC = "/brands/4scale-four.png";

/** Premium neon tube: baked core + layered low-intensity outer glow. */
const LOGO_LIT = [
  "brightness(1.08)",
  "contrast(1.06)",
  "drop-shadow(0 0 0.5px rgba(255,250,240,0.7))",
  "drop-shadow(0 0 1.5px rgba(255,220,180,0.45))",
  "drop-shadow(0 0 4px rgba(255,170,100,0.28))",
  "drop-shadow(0 0 10px rgba(255,140,60,0.16))",
  "drop-shadow(0 0 22px rgba(255,117,26,0.1))",
].join(" ");
const LOGO_DIM = "brightness(0.38) drop-shadow(0 0 0 transparent)";

const VIEWPORT = { once: true, amount: 0.25 } as const;

/**
 * Cinematic LED lamp over the About hero mark.
 *
 * Layers (independent absolute elements):
 * 1 Background → 2 LED bar → 3 Hotspot → 4 Cone →
 * 5 Ambient → 6 Logo → 7 Bloom
 */
export function AboutHeroLamp({ className }: AboutHeroLampProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      aria-hidden
      className={cn("about-hero__mark about-hero-lamp", className)}
    >
      <div className="about-hero-lamp__stage">
        {/* Layer 1 — Background */}
        <div className="about-hero-lamp__background">
          <div className="about-hero-lamp__grid" />
          <div className="about-hero-lamp__vignette" />
        </div>

        {/* Layer 2 — LED Bar */}
        <div className="about-hero-lamp__bar-anchor">
          <motion.div
            className="about-hero-lamp__bar-wrap"
            initial={
              reduceMotion
                ? { opacity: 1, scaleX: 1 }
                : { opacity: 0, scaleX: 0.35 }
            }
            whileInView={{ opacity: 1, scaleX: 1 }}
            viewport={VIEWPORT}
            transition={{ duration: 0.7, ease: EASE_CINEMA, delay: 0 }}
          >
            <div className="about-hero-lamp__bar-glow" />
            <div className="about-hero-lamp__bar" />
          </motion.div>
        </div>

        {/* Layer 3 — Hotspot (light origin, separate from cone) */}
        <div className="about-hero-lamp__hotspot-anchor">
          <motion.div
            className="about-hero-lamp__hotspot"
            initial={
              reduceMotion
                ? { opacity: 1, scale: 1 }
                : { opacity: 0, scale: 0.4 }
            }
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={VIEWPORT}
            transition={{ duration: 0.65, ease: EASE_CINEMA, delay: 0.28 }}
          />
        </div>

        {/* Layer 4 — Light Cone */}
        <div className="about-hero-lamp__cone-anchor">
          <motion.div
            className="about-hero-lamp__cone"
            initial={
              reduceMotion
                ? { opacity: 0.42, scaleY: 1, scaleX: 1 }
                : { opacity: 0, scaleY: 0.35, scaleX: 0.72 }
            }
            whileInView={{ opacity: 0.42, scaleY: 1, scaleX: 1 }}
            viewport={VIEWPORT}
            transition={{ duration: 1.05, ease: EASE_CINEMA, delay: 0.48 }}
          />
        </div>

        {/* Layer 5 — Ambient Glow (reflected light behind logo) */}
        <div className="about-hero-lamp__ambient-anchor">
          <motion.div
            className="about-hero-lamp__ambient"
            initial={
              reduceMotion
                ? { opacity: 1, scale: 1 }
                : { opacity: 0, scale: 0.7 }
            }
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={VIEWPORT}
            transition={{ duration: 0.9, ease: EASE_CINEMA, delay: 0.85 }}
          />
        </div>

        {/* Layers 6–7 — Logo + Bloom */}
        <div className="about-hero-lamp__mark-stack">
          <motion.img
            src={LOGO_SRC}
            alt=""
            className="about-hero-lamp__bloom"
            draggable={false}
            initial={
              reduceMotion
                ? { opacity: 0.08, scale: 1.03 }
                : { opacity: 0, scale: 1.01 }
            }
            whileInView={{ opacity: 0.08, scale: 1.03 }}
            viewport={VIEWPORT}
            transition={{ duration: 0.85, ease: EASE_CINEMA, delay: 1.35 }}
          />

          <motion.img
            src={LOGO_SRC}
            alt=""
            className="about-hero-lamp__img"
            draggable={false}
            initial={
              reduceMotion
                ? { opacity: 1, filter: LOGO_LIT }
                : { opacity: 0.22, filter: LOGO_DIM }
            }
            whileInView={{ opacity: 1, filter: LOGO_LIT }}
            viewport={VIEWPORT}
            transition={{ duration: 0.9, ease: EASE_CINEMA, delay: 1.1 }}
          />
        </div>
      </div>
    </div>
  );
}
