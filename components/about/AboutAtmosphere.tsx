"use client";

import { AboutFourMark } from "@/components/about/AboutFourMark";
import { cn } from "@/lib/utils";

type AboutAtmosphereProps = {
  /**
   * `grid` — only grid + grain.
   * `mark` — faint logo watermark.
   * `strong` — larger logo (hero / 4Scale).
   */
  intensity?: "grid" | "mark" | "strong";
  /** Show brand glow blob. */
  glow?: boolean;
  /** Glow placement hint. */
  glowPosition?: "center" | "right" | "left";
  className?: string;
};

export function AboutAtmosphere({
  intensity = "grid",
  glow = false,
  glowPosition = "center",
  className,
}: AboutAtmosphereProps) {
  const glowClass =
    glowPosition === "right"
      ? "right-[4%] top-[30%] left-auto -translate-x-0"
      : glowPosition === "left"
        ? "left-[8%] top-[28%] -translate-x-0"
        : "left-1/2 top-[22%] -translate-x-1/2";

  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}
    >
      <div className="absolute inset-0 bg-[var(--background)]" />

      <div className="about-grid absolute inset-0" />

      <div className="about-grid-mask absolute inset-0" />

      {glow ? (
        <div
          className={cn(
            "absolute h-72 w-72 rounded-full blur-[110px] sm:h-80 sm:w-80",
            "bg-[rgba(255,117,26,0.05)]",
            glowClass,
          )}
        />
      ) : null}

      {intensity === "mark" || intensity === "strong" ? (
        <AboutFourMark intensity={intensity} />
      ) : null}

      <div className="about-grain absolute inset-0" />
    </div>
  );
}
