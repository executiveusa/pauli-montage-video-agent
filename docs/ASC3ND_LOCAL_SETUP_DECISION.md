# ASC3ND local setup decision

Decision: use the existing hosted Montage browser Studio plus the owner-controlled loopback worker. Do not build a browser extension for the Phase 3 proof.

Reasons:

1. The Studio already posts selected local files directly to `127.0.0.1:4788`.
2. The worker streams large uploads to the E-drive workspace instead of proxying them through Vercel.
3. FFmpeg, ffprobe and Faster-Whisper already execute locally.
4. A browser extension would create a second permission/security surface without solving a current acceptance blocker.
5. The one-click Windows setup/launcher is the smallest path from raw ASC3ND footage to a verified local Reel.

Revisit an extension or approved-root filesystem linker only after the real ASC3ND Phase 3 proof identifies a concrete need.
