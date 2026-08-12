"use client";

import {
  useCallback,
  useRef,
  type CSSProperties,
  type PointerEvent,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

export type GlowCardProps = {
  children?: ReactNode;
  className?: string;
  /** Spotlight / border glow color. Defaults to brand orange. */
  glowColor?: string;
  /** Soft fill spotlight under the cursor. */
  spotlightColor?: string;
  size?: "sm" | "md" | "lg";
  width?: string | number;
  height?: string | number;
  /** When true, ignore size presets and use className / width / height. */
  customSize?: boolean;
};

const sizeMap: Record<NonNullable<GlowCardProps["size"]>, string> = {
  sm: "min-h-[16rem]",
  md: "min-h-[20rem]",
  lg: "min-h-[24rem]",
};

/**
 * Card with mouse-tracking border glow (Linear / EaseMize spotlight pattern).
 * Brand default: #ff751a.
 */
export function GlowCard({
  children,
  className = "",
  glowColor = "rgba(255, 117, 26, 0.95)",
  spotlightColor = "rgba(255, 117, 26, 0.1)",
  size = "md",
  width,
  height,
  customSize = true,
}: GlowCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handlePointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    card.style.setProperty("--glow-x", `${event.clientX - rect.left}px`);
    card.style.setProperty("--glow-y", `${event.clientY - rect.top}px`);
    card.style.setProperty("--glow-opacity", "1");
  }, []);

  const handlePointerLeave = useCallback(() => {
    cardRef.current?.style.setProperty("--glow-opacity", "0");
  }, []);

  const dimensionStyles: CSSProperties = {
    ["--glow-color" as string]: glowColor,
    ["--spotlight-color" as string]: spotlightColor,
  };

  if (width !== undefined) {
    dimensionStyles.width = typeof width === "number" ? `${width}px` : width;
  }
  if (height !== undefined) {
    dimensionStyles.height = typeof height === "number" ? `${height}px` : height;
  }

  return (
    <div
      ref={cardRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      style={dimensionStyles}
      className={cn(
        "glow-card relative flex h-full flex-col overflow-hidden rounded-2xl",
        !customSize && sizeMap[size],
        className,
      )}
    >
      <div className="glow-card__spotlight" aria-hidden />
      <div className="glow-card__border" aria-hidden />
      <div className="relative z-10 flex h-full flex-col">{children}</div>
    </div>
  );
}
