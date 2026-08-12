"use client";

import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { Parallax, ParallaxTarget } from "@/components/ui/parallax-scrolling";
import { cn } from "@/lib/utils";

type AboutFourMarkProps = {
  /** `strong` matches the 4Scale section watermark. */
  intensity?: "mark" | "strong";
  className?: string;
};

/**
 * Marca “4” outline cobre — watermark absoluto com fade-in e rotação sutil no scroll.
 */
export function AboutFourMark({
  intensity = "strong",
  className,
}: AboutFourMarkProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const rotate = useTransform(
    scrollYProgress,
    [0, 1],
    reduceMotion ? [0, 0] : [-3, 3],
  );

  const markOpacity = intensity === "strong" ? 0.075 : 0.045;
  const markSize =
    intensity === "strong"
      ? "h-[min(92vw,40rem)] w-[min(92vw,40rem)]"
      : "h-[min(80vw,30rem)] w-[min(80vw,30rem)]";

  return (
    <div
      ref={containerRef}
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 z-[2] overflow-hidden",
        className,
      )}
    >
      <Parallax
        start={12}
        end={-18}
        disable="mobile"
        scrub={1.4}
        className="absolute inset-0 will-change-transform"
      >
        <ParallaxTarget className="absolute inset-0">
          <motion.img
            src="/brands/4scale-four.png"
            alt=""
            initial={{ opacity: 0 }}
            animate={{ opacity: markOpacity }}
            transition={{ duration: reduceMotion ? 0 : 1.5, ease: "easeOut" }}
            style={{ rotate }}
            className={cn(
              "absolute top-1/2 right-[-8%] -translate-y-1/2 select-none sm:right-[-4%] lg:right-[2%]",
              markSize,
            )}
            draggable={false}
          />
        </ParallaxTarget>
      </Parallax>
    </div>
  );
}
