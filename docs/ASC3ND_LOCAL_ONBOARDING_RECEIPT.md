# ASC3ND local onboarding receipt

Status: implementation candidate — awaiting CI/review and owner laptop execution.

This slice removes the setup friction between the production Montage browser UI and real ASC3ND footage stored on the operator's Windows E: drive.

Implemented:

- one-time Windows setup script with E-drive defaults;
- isolated E-drive Python runtime;
- automatic Python/FFmpeg dependency checks with winget fallback;
- Faster-Whisper install and model prewarm;
- one-click Start-Montage launcher;
- loopback-only worker startup;
- production Studio auto-open;
- Windows script syntax/contract CI gates;
- ASC3ND Phase 3 quickstart using `vc(1).mp4`.

Existing large-file path remains intentionally local: the browser posts the selected File directly to `127.0.0.1:4788/assets`; the worker streams it to the configured workspace in bounded chunks. Media bytes do not traverse Vercel.

Acceptance cannot be marked PASS until the owner laptop runs the installer, the worker reports FFmpeg/ffprobe/Whisper ready, real `vc(1).mp4` imports successfully, and the Aug 12 local proof begins.
