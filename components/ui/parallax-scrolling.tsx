"use client";

import {
  useEffect,
  useRef,
  type CSSProperties,
  type ReactNode,
} from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import "lenis/dist/lenis.css";

gsap.registerPlugin(ScrollTrigger);

type ParallaxDisable = "mobile" | "mobileLandscape" | "tablet";

type ParallaxProps = {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  /** Vertical by default; use horizontal for xPercent. */
  direction?: "vertical" | "horizontal";
  /** Start yPercent/xPercent. Default: 20 */
  start?: number;
  /** End yPercent/xPercent. Default: -20 */
  end?: number;
  /** ScrollTrigger start. Default: "top bottom" */
  scrollStart?: string;
  /** ScrollTrigger end. Default: "bottom top" */
  scrollEnd?: string;
  /** Scrub: true or seconds to catch up. Default: true */
  scrub?: boolean | number;
  /** Disable parallax below a breakpoint. */
  disable?: ParallaxDisable;
};

type ParallaxTargetProps = {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
};

type ParallaxComponentProps = {
  children: ReactNode;
  className?: string;
};

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function initGlobalParallax(): () => void {
  const mm = gsap.matchMedia();

  mm.add(
    {
      isMobile: "(max-width:479px)",
      isMobileLandscape: "(max-width:767px)",
      isTablet: "(max-width:991px)",
      isDesktop: "(min-width:992px)",
    },
    (context) => {
      const { isMobile, isMobileLandscape, isTablet } = context.conditions ?? {};

      const ctx = gsap.context(() => {
        document
          .querySelectorAll<HTMLElement>('[data-parallax="trigger"]')
          .forEach((trigger) => {
            const disable = trigger.getAttribute("data-parallax-disable");
            if (
              (disable === "mobile" && isMobile) ||
              (disable === "mobileLandscape" && isMobileLandscape) ||
              (disable === "tablet" && isTablet)
            ) {
              return;
            }

            const target =
              trigger.querySelector<HTMLElement>('[data-parallax="target"]') ??
              trigger;

            const direction =
              trigger.getAttribute("data-parallax-direction") || "vertical";
            const prop = direction === "horizontal" ? "xPercent" : "yPercent";

            const scrubAttr = trigger.getAttribute("data-parallax-scrub");
            const scrub = scrubAttr ? Number.parseFloat(scrubAttr) : true;

            const startAttr = trigger.getAttribute("data-parallax-start");
            const startVal =
              startAttr !== null ? Number.parseFloat(startAttr) : 20;

            const endAttr = trigger.getAttribute("data-parallax-end");
            const endVal = endAttr !== null ? Number.parseFloat(endAttr) : -20;

            const scrollStartRaw =
              trigger.getAttribute("data-parallax-scroll-start") ||
              "top bottom";
            const scrollStart = `clamp(${scrollStartRaw})`;

            const scrollEndRaw =
              trigger.getAttribute("data-parallax-scroll-end") || "bottom top";
            const scrollEnd = `clamp(${scrollEndRaw})`;

            gsap.fromTo(
              target,
              { [prop]: startVal },
              {
                [prop]: endVal,
                ease: "none",
                scrollTrigger: {
                  trigger,
                  start: scrollStart,
                  end: scrollEnd,
                  scrub,
                },
              },
            );
          });
      });

      return () => ctx.revert();
    },
  );

  return () => {
    mm.revert();
  };
}

/**
 * Osmo-style global parallax + Lenis smooth scroll for the whole page.
 * Based on: https://www.osmo.supply/resource/global-parallax-setup
 */
export function ParallaxComponent({
  children,
  className = "",
}: ParallaxComponentProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReducedMotion()) {
      return;
    }

    const html = document.documentElement;
    const previousScrollBehavior = html.style.scrollBehavior;
    html.style.scrollBehavior = "auto";
    html.classList.add("lenis", "lenis-smooth");

    const lenis = new Lenis({
      lerp: 0.1,
      smoothWheel: true,
      syncTouch: false,
      anchors: true,
    });

    lenis.on("scroll", ScrollTrigger.update);

    const onTick = (time: number) => {
      lenis.raf(time * 1000);
    };
    gsap.ticker.add(onTick);
    gsap.ticker.lagSmoothing(0);

    // Wait one frame so client sections finish layout before measuring triggers.
    let disposeParallax: (() => void) | undefined;
    const initId = window.requestAnimationFrame(() => {
      disposeParallax = initGlobalParallax();
      ScrollTrigger.refresh();
    });

    const onResize = () => {
      ScrollTrigger.refresh();
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.cancelAnimationFrame(initId);
      window.removeEventListener("resize", onResize);
      disposeParallax?.();
      gsap.ticker.remove(onTick);
      gsap.ticker.lagSmoothing(500, 33);
      lenis.destroy();
      html.style.scrollBehavior = previousScrollBehavior;
      html.classList.remove("lenis", "lenis-smooth");
      ScrollTrigger.getAll().forEach((trigger) => {
        trigger.kill();
      });
    };
  }, []);

  return (
    <div
      ref={rootRef}
      className={["parallax-root", className].filter(Boolean).join(" ")}
    >
      {children}
    </div>
  );
}

/** Marks an element as a parallax trigger (and target by default). */
export function Parallax({
  children,
  className = "",
  style,
  direction = "vertical",
  start = 20,
  end = -20,
  scrollStart = "top bottom",
  scrollEnd = "bottom top",
  scrub = true,
  disable,
}: ParallaxProps) {
  return (
    <div
      className={className}
      style={style}
      data-parallax="trigger"
      data-parallax-direction={direction}
      data-parallax-start={String(start)}
      data-parallax-end={String(end)}
      data-parallax-scroll-start={scrollStart}
      data-parallax-scroll-end={scrollEnd}
      {...(typeof scrub === "number"
        ? { "data-parallax-scrub": String(scrub) }
        : {})}
      {...(disable ? { "data-parallax-disable": disable } : {})}
    >
      {children}
    </div>
  );
}

/** Child target inside a trigger mask (e.g. taller image wrapper). */
export function ParallaxTarget({
  children,
  className = "",
  style,
}: ParallaxTargetProps) {
  return (
    <div className={className} style={style} data-parallax="target">
      {children}
    </div>
  );
}
