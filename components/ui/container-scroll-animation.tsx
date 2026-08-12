"use client";

import React, { useEffect, useRef, useState, type ReactNode } from "react";
import {
  motion,
  useScroll,
  useTransform,
  type MotionValue,
} from "framer-motion";

type ContainerScrollProps = {
  titleComponent: string | ReactNode;
  children: ReactNode;
};

export function ContainerScroll({
  titleComponent,
  children,
}: ContainerScrollProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
  });
  const [isMobile, setIsMobile] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    const mediaReduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncReduced = () => {
      setReducedMotion(mediaReduced.matches);
    };

    checkMobile();
    syncReduced();
    window.addEventListener("resize", checkMobile);
    mediaReduced.addEventListener("change", syncReduced);

    return () => {
      window.removeEventListener("resize", checkMobile);
      mediaReduced.removeEventListener("change", syncReduced);
    };
  }, []);

  const scaleRange = isMobile ? [0.7, 0.9] : [1.05, 1];
  const rotate = useTransform(
    scrollYProgress,
    [0, 1],
    reducedMotion ? [0, 0] : [20, 0],
  );
  const scale = useTransform(
    scrollYProgress,
    [0, 1],
    reducedMotion ? [1, 1] : scaleRange,
  );
  const translate = useTransform(
    scrollYProgress,
    [0, 1],
    reducedMotion ? [0, 0] : [0, -100],
  );

  return (
    <div
      ref={containerRef}
      className="relative flex h-[60rem] items-center justify-center p-2 md:h-[80rem] md:p-20"
    >
      <div
        className="relative w-full py-10 md:py-40"
        style={{ perspective: "1000px" }}
      >
        <Header translate={translate} titleComponent={titleComponent} />
        <Card rotate={rotate} scale={scale}>
          {children}
        </Card>
      </div>
    </div>
  );
}

function Header({
  translate,
  titleComponent,
}: {
  translate: MotionValue<number>;
  titleComponent: string | ReactNode;
}) {
  return (
    <motion.div
      style={{ translateY: translate }}
      className="mx-auto max-w-5xl text-center"
    >
      {titleComponent}
    </motion.div>
  );
}

function Card({
  rotate,
  scale,
  children,
}: {
  rotate: MotionValue<number>;
  scale: MotionValue<number>;
  children: ReactNode;
}) {
  return (
    <motion.div
      style={{
        rotateX: rotate,
        scale,
        boxShadow:
          "0 0 #0000004d, 0 9px 20px #0000004a, 0 37px 37px #00000042, 0 84px 50px #00000026, 0 149px 60px #0000000a, 0 233px 65px #00000003",
      }}
      className="mx-auto mt-6 h-[30rem] w-full max-w-5xl rounded-[30px] border-4 border-[#6C6C6C] bg-[#222222] p-2 shadow-2xl md:mt-8 md:h-[40rem] md:p-6"
    >
      <div className="h-full w-full overflow-hidden rounded-2xl bg-black md:rounded-2xl">
        {children}
      </div>
    </motion.div>
  );
}
