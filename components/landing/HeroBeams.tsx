"use client";

import { useEffect, useRef, useState } from "react";

const HERO_VIDEO_SRC = "/videos/4SEO.mp4";

/** Velocidade do loop — abaixo de 1 deixa o movimento das barras mais calmo. */
const HERO_VIDEO_PLAYBACK_RATE = 0.55;

/**
 * Fundo da Hero — barras em movimento via vídeo (desktop) + fallback leve (mobile / reduced motion).
 * Paleta e vinheta alinhadas à identidade Precision AI (dark + bronze).
 */
export function HeroBeams() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [useVideo, setUseVideo] = useState(false);

  useEffect(() => {
    const mediaDesktop = window.matchMedia("(min-width: 768px)");
    const mediaReduced = window.matchMedia("(prefers-reduced-motion: reduce)");

    const syncMode = () => {
      setUseVideo(mediaDesktop.matches && !mediaReduced.matches);
    };

    syncMode();
    mediaDesktop.addEventListener("change", syncMode);
    mediaReduced.addEventListener("change", syncMode);

    return () => {
      mediaDesktop.removeEventListener("change", syncMode);
      mediaReduced.removeEventListener("change", syncMode);
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    const container = containerRef.current;
    if (!useVideo || !video || !container) return;

    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.playbackRate = HERO_VIDEO_PLAYBACK_RATE;
    video.defaultPlaybackRate = HERO_VIDEO_PLAYBACK_RATE;

    const applyRate = () => {
      if (video.playbackRate !== HERO_VIDEO_PLAYBACK_RATE) {
        video.playbackRate = HERO_VIDEO_PLAYBACK_RATE;
      }
    };

    const tryPlay = () => {
      applyRate();
      void video.play().catch(() => {
        /* autoplay pode falhar em políticas do browser — fallback visual permanece */
      });
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) return;
        if (entry.isIntersecting) {
          tryPlay();
        } else {
          video.pause();
        }
      },
      { threshold: 0.08 },
    );

    video.addEventListener("play", applyRate);
    observer.observe(container);
    tryPlay();

    return () => {
      observer.disconnect();
      video.removeEventListener("play", applyRate);
      video.pause();
    };
  }, [useVideo]);

  return (
    <div ref={containerRef} aria-hidden className="ray-hero-background">
      {useVideo ? (
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full scale-[1.02] object-cover brightness-[0.75] contrast-[1.05]"
          src={HERO_VIDEO_SRC}
          autoPlay
          loop
          muted
          playsInline
          preload="metadata"
          disablePictureInPicture
          disableRemotePlayback
        />
      ) : null}

      <div className="ray-hero-mobile-fallback absolute inset-0 md:hidden">
        <div className="absolute top-[20%] left-[10%] h-64 w-64 rounded-full bg-[rgba(255,117,26,0.05)] blur-[100px]" />
        <div className="absolute right-[10%] bottom-[30%] h-80 w-80 rounded-full bg-[rgba(255,138,61,0.035)] blur-[120px]" />
        <div className="ray-hero-grid absolute inset-0" />
      </div>

      {!useVideo ? (
        <div className="pointer-events-none absolute inset-0 hidden md:block">
          <div className="absolute top-[18%] left-[12%] h-72 w-72 rounded-full bg-[rgba(255,117,26,0.04)] blur-[110px]" />
          <div className="absolute right-[14%] bottom-[22%] h-96 w-96 rounded-full bg-[rgba(255,138,61,0.03)] blur-[130px]" />
          <div className="ray-hero-grid absolute inset-0 opacity-80" />
        </div>
      ) : null}

      <div className="ray-hero-background-mask" />
    </div>
  );
}
