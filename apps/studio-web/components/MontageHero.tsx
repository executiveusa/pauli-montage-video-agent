"use client";

import { useEffect, useRef, useState } from "react";

export function MontageHero() {
  const film = useRef<HTMLVideoElement>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    const video = film.current;
    if (!video) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compactViewport = window.matchMedia("(max-width: 620px)");
    const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
    let started = false;
    const suspend = () => video.pause();
    const onPlay = () => { started = true; };
    const onVisibility = () => { if (document.hidden) suspend(); };
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) { suspend(); return; }
      // Start only once: scrolling back must never override a manual pause.
      if (!started && !reducedMotion.matches && !compactViewport.matches && !connection?.saveData && !document.hidden) {
        started = true;
        void video.play().catch(() => { /* Native controls remain available. */ });
      }
    }, { threshold: 0.25 });
    observer.observe(video);
    video.addEventListener("play", onPlay);
    reducedMotion.addEventListener("change", suspend);
    compactViewport.addEventListener("change", suspend);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      observer.disconnect();
      video.removeEventListener("play", onPlay);
      reducedMotion.removeEventListener("change", suspend);
      compactViewport.removeEventListener("change", suspend);
      document.removeEventListener("visibilitychange", onVisibility);
      suspend();
    };
  }, []);

  return (
    <section className="brand-hero brand-film-hero" aria-labelledby="brand-hero-title">
      <div className="brand-hero-content">
        <p className="brand-hero-kicker">AI-assisted video editing · Private beta</p>
        <img className="montage-hero-wordmark" src="/brand/montage-wordmark-white.svg" width="900" height="220" alt="Montage" />
        <h1 id="brand-hero-title">Turn hours of raw footage into one finished story.</h1>
        <p className="brand-promise">Review transcripts and indexed scene evidence. Build selects, edit reversibly, and export verified versions while your source masters stay protected.</p>
        <div className="brand-hero-actions">
          <a className="brand-primary-action" href="#waitlist">Request beta access <span aria-hidden="true">→</span></a>
          <a className="brand-secondary-action" href="#proof">See the product path</a>
        </div>
      </div>
      <figure className="montage-brand-film">
        <video ref={film} controls muted playsInline loop preload="none"
          poster="/brand/montage-hero-poster.jpg" width="1920" height="1080"
          aria-label="Montage brand film. Play or pause with the video controls."
          aria-describedby="montage-film-caption" onError={() => setUnavailable(true)}>
          <source src="/brand/montage-hero-30s.mp4" type="video/mp4" />
          <track kind="captions" src="/brand/montage-hero.vtt" srcLang="en" label="English" />
          <a href="/brand/montage-hero-30s.mp4">Watch the Montage brand film</a>
        </video>
        <figcaption id="montage-film-caption">
          <span>Montage / 30-second brand film · Illustrated workflow</span>
          <a href="/brand/montage-hero-30s.mp4" download>Download film</a>
        </figcaption>
        {unavailable && <p role="status">The film could not load. You can still explore Montage below.</p>}
      </figure>
    </section>
  );
}
