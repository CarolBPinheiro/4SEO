"use client";

import {
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "framer-motion";
import { useEffect, useRef, useState } from "react";

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

type Metric =
  | {
      kind: "count";
      value: number;
      prefix?: string;
      suffix?: string;
      label: string;
    }
  | {
      kind: "text";
      display: string;
      label: string;
    };

const METRICS: readonly Metric[] = [
  {
    kind: "count",
    value: 5,
    label: "Anos de experiência em MarTech",
  },
  {
    kind: "count",
    value: 100,
    prefix: "+",
    label: "Clientes nacionais",
  },
  {
    kind: "text",
    display: "Milhões",
    label: "De visitas analisadas",
  },
  {
    kind: "count",
    value: 20,
    suffix: "+",
    label: "Tecnologias utilizadas em nossos projetos",
  },
] as const;

function AnimatedCount({
  value,
  prefix = "",
  suffix = "",
  active,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  active: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, {
    stiffness: 60,
    damping: 28,
    mass: 0.8,
  });
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!active) return;

    if (reduceMotion) {
      motionValue.set(value);
      return;
    }

    motionValue.set(0);
    const frame = window.requestAnimationFrame(() => {
      motionValue.set(value);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [active, motionValue, reduceMotion, value]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (latest) => {
      if (!ref.current) return;
      ref.current.textContent = `${prefix}${Math.round(latest)}${suffix}`;
    });
    return unsubscribe;
  }, [prefix, spring, suffix]);

  return (
    <span ref={ref} className="about-metrics__value tabular-nums">
      {prefix}
      {reduceMotion || !active ? value : 0}
      {suffix}
    </span>
  );
}

function MetricItem({
  metric,
  index,
  isActive,
  onActivate,
}: {
  metric: Metric;
  index: number;
  isActive: boolean;
  onActivate: () => void;
}) {
  const itemRef = useRef<HTMLLIElement>(null);
  const inView = useInView(itemRef, { once: true, amount: 0.3 });

  return (
    <motion.li
      ref={itemRef}
      className={
        isActive
          ? "about-metrics__item about-metrics__item--active"
          : "about-metrics__item"
      }
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{
        duration: 0.6,
        ease: EASE_OUT_EXPO,
        delay: 0.08 * index,
      }}
    >
      <button
        type="button"
        className="about-metrics__trigger"
        onMouseEnter={onActivate}
        onFocus={onActivate}
      >
        <span className="about-metrics__edge about-metrics__edge--left" aria-hidden />
        <span className="about-metrics__edge about-metrics__edge--right" aria-hidden />
        <span className="about-metrics__edge about-metrics__edge--top" aria-hidden />
        <span className="about-metrics__edge about-metrics__edge--bottom" aria-hidden />

        <span className="about-metrics__content">
          {metric.kind === "count" ? (
            <AnimatedCount
              value={metric.value}
              prefix={metric.prefix}
              suffix={metric.suffix}
              active={inView}
            />
          ) : (
            <span className="about-metrics__value">{metric.display}</span>
          )}
          <span className="about-metrics__label">{metric.label}</span>
        </span>
      </button>
    </motion.li>
  );
}

export function AboutMetrics() {
  const [activeIndex, setActiveIndex] = useState<number | null>(0);

  return (
    <section className="about-metrics" aria-label="Métricas da 4Scale">
      <div className="about-metrics__band about-glow-edges">
        <ul
          className={
            activeIndex === null
              ? "about-metrics__grid"
              : "about-metrics__grid about-metrics__grid--has-active"
          }
          onMouseLeave={() => setActiveIndex(null)}
        >
          {METRICS.map((metric, index) => (
            <MetricItem
              key={metric.label}
              metric={metric}
              index={index}
              isActive={activeIndex === index}
              onActivate={() => setActiveIndex(index)}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}
