# Montage brand film

30 seconds of original SVG/GSAP motion graphics, reconstructed from the October 20 composition record after temporary source files disappeared. The approved direction 01 logo is preserved. This reconstruction is not byte-identical to the lost film. No MotionVideo pack or stock media is used.

The diagrammatic edit and output sequences are explicitly illustrated, not captured product evidence. Public playback is silent by default; the user may enable the original synthesized score using native controls. Captions describe all on-screen text.

## Rebuild

Requires Python 3, numpy, fonttools, Node 22+, FFmpeg, and the pinned HyperFrames CLI (which installs its browser when needed).

```sh
python author.py
ffmpeg -y -i assets/hero-score-raw.wav -af loudnorm=I=-17:TP=-2:LRA=9 -ar 48000 -c:a pcm_s16le assets/hero-score.wav
npm run check
npm run render
ffmpeg -y -i renders/montage-hero-30s.mp4 -vf 'scale=1280:720,fps=30' -c:v libx264 -crf 22 -preset medium -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart ../../apps/studio-web/public/brand/montage-hero-30s.mp4
ffmpeg -y -ss 2.25 -i renders/montage-hero-30s.mp4 -frames:v 1 -q:v 2 ../../apps/studio-web/public/brand/montage-hero-poster.jpg
```

The font license is in assets/OFL-Inter.txt. GSAP's upstream copyright/license notice remains in the vendored script. The exact outlined logo is served from apps/studio-web/public/brand; it needs no installed font. The hero video uses a local URL, preserves the complete 16:9 frame, offers native controls and a download link, respects reduced motion and data saver for autoplay, and pauses when offscreen or the tab is hidden.
