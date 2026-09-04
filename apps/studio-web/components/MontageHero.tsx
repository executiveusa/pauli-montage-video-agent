"use client";

import Link from "next/link";
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

export function MontageHero() {
  const [slide, setSlide] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setSlide((value) => (value + 1) % arrangements.length), 6500);
    return () => window.clearInterval(timer);
  }, []);

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
        <p className="brand-hero-kicker">Many moments. One story.</p>
        <h1 id="brand-hero-title">Montage</h1>
        <div className="brand-definition">
          <p className="brand-pronunciation">/mänˈtäZH/</p>
          <p>A montage is <strong>an artistic technique or process of combining multiple separate images, video clips, or pieces of media into a single, unified composition.</strong></p>
        </div>
        <p className="brand-promise">Turn raw clips into social-ready stories, walkthroughs, reels, and highlight edits. Compress a big idea into a powerful 30-second video.</p>
        <div className="brand-hero-actions">
          <Link className="brand-primary-action" href="/sign-in">Start a Montage <span aria-hidden="true">→</span></Link>
          <a className="brand-secondary-action" href="#proof">Watch how it works</a>
        </div>
      </div>

      <div className="brand-output-row" aria-label="Common Montage outputs">
        <span>9:16 Reels</span><span>16:9 Video</span><span>1:1 Social</span><span>Captions</span><span>Highlights</span><span>Walkthroughs</span>
      </div>

      <div className="brand-hero-controls" aria-label="Hero slides">
        <button type="button" onClick={() => setSlide((slide - 1 + arrangements.length) % arrangements.length)} aria-label="Previous montage">←</button>
        <span>{String(slide + 1).padStart(2, "0")} / {String(arrangements.length).padStart(2, "0")}</span>
        <div className="brand-hero-dots" aria-hidden="true">
          {arrangements.map((_, index) => <i key={index} className={index === slide ? "active" : ""} />)}
        </div>
        <button type="button" onClick={() => setSlide((slide + 1) % arrangements.length)} aria-label="Next montage">→</button>
      </div>

      <div className="brand-workflow-rail" id="flow">
        <div><b>01</b><span><strong>Bring in your clips</strong><small>Drive, OneDrive, local footage.</small></span></div>
        <div><b>02</b><span><strong>Find the best moments</strong><small>Search, transcript, scenes, selects.</small></span></div>
        <div><b>03</b><span><strong>Build the montage</strong><small>Sequence, captions, sound, review.</small></span></div>
        <div><b>04</b><span><strong>Export anywhere</strong><small>Social, walkthroughs, highlights.</small></span></div>
      </div>
    </section>
  );
}
