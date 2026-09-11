"use client";

import { useEffect, useState } from "react";

const scenes = [
  {
    label: "Travel / place",
    image: "https://images.unsplash.com/photo-1762374008579-c883ef74267a?auto=format&fit=crop&fm=jpg&q=82&w=1800",
  },
  {
    label: "Human detail",
    image: "https://images.unsplash.com/photo-1761026971307-87becc9de54c?auto=format&fit=crop&fm=jpg&q=82&w=1800",
  },
  {
    label: "Action / motion",
    image: "https://images.unsplash.com/photo-1769816325408-844127c6191f?auto=format&fit=crop&fm=jpg&q=82&w=1800",
  },
  {
    label: "City / scale",
    image: "https://images.unsplash.com/photo-1569411562533-cbbd6efd207f?auto=format&fit=crop&fm=jpg&q=82&w=1800",
  },
  {
    label: "Music / energy",
    image: "https://images.unsplash.com/photo-1666548891460-6d8ea09d2a2a?auto=format&fit=crop&fm=jpg&q=82&w=1800",
  },
] as const;

const arrangements = [
  [0, 1, 2, 3, 4],
  [3, 0, 4, 1, 2],
  [2, 4, 1, 0, 3],
  [1, 3, 0, 4, 2],
] as const;

const proofPoints = [
  "Transcript + scene evidence",
  "Protected source masters",
  "Reversible edits",
  "Verified exports",
] as const;

export function MontageHero() {
  const [slide, setSlide] = useState(0);
  const [paused, setPaused] = useState(false);
  const [autoAdvanceAllowed, setAutoAdvanceAllowed] = useState(false);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compactViewport = window.matchMedia("(max-width: 620px)");
    const updateMotionPolicy = () => setAutoAdvanceAllowed(!reducedMotion.matches && !compactViewport.matches);

    updateMotionPolicy();
    reducedMotion.addEventListener("change", updateMotionPolicy);
    compactViewport.addEventListener("change", updateMotionPolicy);

    return () => {
      reducedMotion.removeEventListener("change", updateMotionPolicy);
      compactViewport.removeEventListener("change", updateMotionPolicy);
    };
  }, []);

  useEffect(() => {
    if (paused || !autoAdvanceAllowed) return;
    const timer = window.setInterval(() => setSlide((value) => (value + 1) % arrangements.length), 6500);
    return () => window.clearInterval(timer);
  }, [paused, autoAdvanceAllowed]);

  const ordered = arrangements[slide].map((index) => scenes[index]);

  return (
    <section className="brand-hero" aria-labelledby="brand-hero-title">
      <div className="brand-hero-media" aria-hidden="true">
        {ordered.map((scene, index) => (
          <div
            className={`brand-hero-scene brand-hero-scene-${index + 1}`}
            key={`${slide}-${scene.label}`}
            style={{ backgroundImage: `url(${scene.image})` }}
          >
            <span>{scene.label}</span>
          </div>
        ))}
        <div className="brand-hero-veil" />
      </div>

      <div className="brand-hero-content">
        <p className="brand-hero-kicker">AI-assisted video editing · Private beta</p>
        <p className="brand-hero-name" aria-hidden="true">Montage</p>
        <h1 id="brand-hero-title">Turn hours of raw footage into one finished story.</h1>
        <p className="brand-promise">
          Review transcripts and indexed scene evidence. Build selects, edit reversibly, and export verified versions while your source masters stay protected.
        </p>
        <div className="brand-hero-actions">
          <a className="brand-primary-action" href="#waitlist">Request beta access <span aria-hidden="true">→</span></a>
          <a className="brand-secondary-action" href="#proof">See the product path</a>
        </div>
        <div className="brand-definition" aria-label="Montage brand definition">
          <p className="brand-pronunciation">Montage /mänˈtäZH/</p>
          <p><strong>Many moments. One story.</strong> Separate clips, scenes, and media assembled into one coherent composition.</p>
        </div>
      </div>

      <div className="brand-output-row" aria-label="Verified Montage workflow qualities">
        {proofPoints.map((point) => <span key={point}>{point}</span>)}
      </div>

      <div className="brand-hero-controls" aria-label="Hero slides">
        <button type="button" onClick={() => setSlide((slide - 1 + arrangements.length) % arrangements.length)} aria-label="Previous montage">←</button>
        <span>{String(slide + 1).padStart(2, "0")} / {String(arrangements.length).padStart(2, "0")}</span>
        {autoAdvanceAllowed && (
          <button
            className="brand-hero-pause"
            type="button"
            aria-pressed={paused}
            aria-label={paused ? "Resume hero montage" : "Pause hero montage"}
            onClick={() => setPaused((value) => !value)}
          >
            {paused ? "Play" : "Pause"}
          </button>
        )}
        <button type="button" onClick={() => setSlide((slide + 1) % arrangements.length)} aria-label="Next montage">→</button>
        <div className="brand-hero-dots" aria-hidden="true">
          {arrangements.map((_, index) => <i key={index} className={index === slide ? "active" : ""} />)}
        </div>
      </div>

      <div className="brand-workflow-rail" aria-label="Montage workflow">
        <div><b>01</b><span><strong>Bring in your footage</strong><small>Drive, OneDrive, or local sources.</small></span></div>
        <div><b>02</b><span><strong>Find the moments</strong><small>Review transcripts, scene evidence, and selects.</small></span></div>
        <div><b>03</b><span><strong>Shape the story</strong><small>Sequence, captions, sound, and review.</small></span></div>
        <div><b>04</b><span><strong>Verify the export</strong><small>Review the result before calling it finished.</small></span></div>
      </div>
    </section>
  );
}
