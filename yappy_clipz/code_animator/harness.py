"""Browser-side harness: deterministic canvas runtime for draw(ctx, t, env)."""
from __future__ import annotations

import json

from .spec import AnimationSpec

# Runs before any page script. Everything time- or randomness-related is a pure function of (seed, t).
INIT_JS = r"""
(() => {
  const CFG = __CFG__;
  let frozenMs = 0;
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  let rng = mulberry32(CFG.seed);
  Object.defineProperty(Math, 'random', { value: () => rng(), writable: false, configurable: false });
  const RealDate = Date;
  class FrozenDate extends RealDate {
    constructor(...args) { if (args.length === 0) super(frozenMs); else super(...args); }
    static now() { return frozenMs; }
  }
  window.Date = FrozenDate;
  performance.now = () => frozenMs;
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, k) => a + (b - a) * k;
  const progress = (t, a, b) => clamp((t - a) / (b - a || 1e-9), 0, 1);
  const ease = {
    linear: k => k,
    inQuad: k => k * k, outQuad: k => 1 - (1 - k) * (1 - k),
    inOutQuad: k => k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2,
    outCubic: k => 1 - Math.pow(1 - k, 3),
    inOutCubic: k => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2,
    outBack: k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
    outExpo: k => k === 1 ? 1 : 1 - Math.pow(2, -10 * k),
  };
  function fitText(ctx, text, maxW, px, family, weight) {
    let size = px;
    ctx.font = (weight || 'normal') + ' ' + size + 'px ' + family;
    while (size > 8 && ctx.measureText(text).width > maxW) {
      size -= 2; ctx.font = (weight || 'normal') + ' ' + size + 'px ' + family;
    }
    return size;
  }
  const env = Object.freeze({
    w: CFG.w, h: CFG.h, fps: CFG.fps, duration: CFG.duration, seed: CFG.seed,
    beats: CFG.beats, palette: CFG.palette, title: CFG.title,
    clamp, lerp, progress, ease, fitText,
    rand: () => Math.random(),
  });
  window.__animator = {
    errors: [],
    ready() { return typeof window.draw === 'function'; },
    frame(t, index) {
      frozenMs = Math.round(t * 1000);
      rng = mulberry32((CFG.seed ^ Math.imul(index + 1, 2654435761)) >>> 0);
      const canvas = document.getElementById('c');
      const ctx = canvas.getContext('2d');
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
      ctx.shadowBlur = 0; ctx.shadowColor = 'rgba(0,0,0,0)';
      ctx.fillStyle = CFG.palette.bg; ctx.fillRect(0, 0, CFG.w, CFG.h);
      ctx.save();
      try { window.draw(ctx, t, env); } finally { ctx.restore(); }
      return canvas.toDataURL('image/png').slice(22);
    },
  };
})();
"""

PAGE_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<style>html,body{{margin:0;background:#000}}canvas{{display:block}}</style></head>"
    "<body><canvas id='c' width='{w}' height='{h}'></canvas></body></html>"
)


def init_script(spec: AnimationSpec, palette: dict) -> str:
    cfg = {
        "w": spec.width, "h": spec.height, "fps": spec.fps, "duration": spec.duration_seconds,
        "seed": spec.seed, "title": spec.title, "palette": palette,
        "beats": [{"id": b.id, "t": b.t, "label": b.label} for b in spec.beats],
    }
    return INIT_JS.replace("__CFG__", json.dumps(cfg))


def page_html(spec: AnimationSpec) -> str:
    return PAGE_HTML.format(w=spec.width, h=spec.height)
