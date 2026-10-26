"""Style presets: palette + a starter draw(ctx, t, env) per preset. Data only."""
from __future__ import annotations

from typing import Any

_CLEAN = r"""
function draw(ctx, t, env) {
  const { w, h, palette: p, ease, progress, fitText } = env;
  const cx = w / 2, cy = h / 2, vertical = h > w;
  const a = ease.outCubic(progress(t, 0.2, 1.4));
  const b = ease.outCubic(progress(t, 0.9, 2.1));
  const c = ease.outCubic(progress(t, 1.6, 2.8));
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const fam = p.font;
  const size = fitText(ctx, env.title, w * 0.82, vertical ? 120 : 110, fam, '600');
  ctx.globalAlpha = a; ctx.fillStyle = p.ink;
  ctx.fillText(env.title, cx, cy - 20 + (1 - a) * 40);
  ctx.globalAlpha = 1; ctx.fillStyle = p.accent;
  const ruleW = Math.min(w * 0.3, 420) * b;
  ctx.fillRect(cx - ruleW / 2, cy + size * 0.55, ruleW, 4);
  ctx.globalAlpha = c * 0.85; ctx.fillStyle = p.ink;
  fitText(ctx, env.beats.length ? env.beats[env.beats.length - 1].label : '', w * 0.7, 42, fam, '400');
  ctx.fillText(env.beats.length ? env.beats[env.beats.length - 1].label : '', cx, cy + size * 0.55 + 70);
}
"""

_KINETIC = r"""
function draw(ctx, t, env) {
  const { w, h, palette: p, ease, progress, clamp } = env;
  const words = env.title.split(/\s+/).filter(Boolean);
  const per = Math.max(0.35, (env.duration * 0.6) / Math.max(1, words.length));
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const size = Math.min(h * 0.16, w * 0.16);
  ctx.font = '800 ' + size + 'px ' + p.font;
  const lineH = size * 1.15;
  const top = h / 2 - ((words.length - 1) * lineH) / 2;
  words.forEach((word, i) => {
    const k = ease.outBack(progress(t, i * per * 0.6, i * per * 0.6 + 0.6));
    ctx.save();
    ctx.translate(w / 2, top + i * lineH);
    ctx.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k);
    ctx.globalAlpha = clamp(k, 0, 1);
    ctx.fillStyle = i % 2 ? p.accent : p.ink;
    ctx.fillText(word, 0, 0);
    ctx.restore();
  });
}
"""

_PARTICLES = r"""
function draw(ctx, t, env) {
  const { w, h, palette: p, ease, progress, seed } = env;
  // Particle starts come from a PRNG seeded by (seed, i), so every frame agrees on them.
  function pr(i, k) { let x = (seed * 374761393 + i * 668265263 + k * 2147483647) | 0; x = Math.imul(x ^ (x >>> 13), 1274126177); return ((x ^ (x >>> 16)) >>> 0) / 4294967296; }
  const n = 220, land = ease.outCubic(progress(t, 0.2, 2.6));
  ctx.fillStyle = p.accent;
  for (let i = 0; i < n; i++) {
    const tx = w / 2 + (pr(i, 1) - 0.5) * w * 0.5, ty = h / 2 + (pr(i, 2) - 0.5) * h * 0.08;
    const sx = pr(i, 3) * w, sy = pr(i, 4) * h;
    const x = sx + (tx - sx) * land, y = sy + (ty - sy) * land;
    ctx.globalAlpha = 0.25 + 0.75 * land;
    ctx.beginPath(); ctx.arc(x, y, 2 + 3 * (1 - land), 0, Math.PI * 2); ctx.fill();
  }
  const a = ease.outCubic(progress(t, 2.2, 3.4));
  ctx.globalAlpha = a; ctx.fillStyle = p.ink; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  env.fitText(ctx, env.title, w * 0.8, 96, p.font, '600');
  ctx.fillText(env.title, w / 2, h / 2 + (1 - a) * 24);
}
"""

PRESETS: dict[str, dict[str, Any]] = {
    "clean-title": {
        "label": "Clean title", "description": "Title, accent rule and subtitle on a calm background.",
        "palette": {"bg": "#0b0d12", "ink": "#f4f1ea", "accent": "#c9a86a", "font": "sans-serif"},
        "starter": _CLEAN,
    },
    "kinetic-type": {
        "label": "Kinetic type", "description": "Words pop in one by one with an overshoot.",
        "palette": {"bg": "#101010", "ink": "#ffffff", "accent": "#ff5a36", "font": "sans-serif"},
        "starter": _KINETIC,
    },
    "particles-reveal": {
        "label": "Particles reveal", "description": "Seeded particles converge, then the title lands.",
        "palette": {"bg": "#070b14", "ink": "#e8f0ff", "accent": "#5fa8ff", "font": "sans-serif"},
        "starter": _PARTICLES,
    },
}


def style_ids() -> tuple[str, ...]:
    return tuple(PRESETS)


def preset(style: str) -> dict[str, Any]:
    return PRESETS[style]


def list_presets() -> list[dict[str, Any]]:
    return [{"id": key, "label": v["label"], "description": v["description"], "palette": v["palette"]} for key, v in PRESETS.items()]
