# ASC3ND local footage quickstart

This is the shortest path for proving Montage Phase 3 with the real ASC3ND interview footage on Windows.

## Architecture

The hosted Montage Studio is only the control surface. Large media is sent directly from the browser to the owner-controlled loopback worker at `http://127.0.0.1:4788`; it does not upload through Vercel.

The worker streams uploads to disk in chunks and stores source media as immutable project assets under the configured workspace. Editing/transcription runs locally with FFmpeg/ffprobe and Faster-Whisper.

## One-time setup

From an extracted/cloned Montage repository, open PowerShell and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_montage_windows.ps1 -Workspace "E:\MONTAGE_MEDIA" -RuntimeRoot "E:\MONTAGE_RUNTIME"
```

The setup script:

1. creates the E-drive media/runtime directories;
2. verifies or installs Python 3.12 using winget;
3. verifies or installs FFmpeg/ffprobe using winget;
4. tries to create an isolated Python virtual environment on E:;
5. if Windows `venv/ensurepip` fails, automatically removes only the incomplete `E:\MONTAGE_RUNTIME\.venv` directory and falls back to an isolated `E:\MONTAGE_RUNTIME\python-packages` directory using the working system Python;
6. installs Faster-Whisper;
7. downloads/prewarms the `base` Whisper model into the E-drive model cache;
8. creates `E:\MONTAGE_RUNTIME\Start-Montage.cmd`.

No cloud transcription key is required.

## Start Montage

Double-click:

```text
E:\MONTAGE_RUNTIME\Start-Montage.cmd
```

Keep the terminal window open while editing. The launcher opens the production Montage Studio automatically.

## Troubleshooting a partial virtual environment

Rerun the latest setup script after `git pull origin main`. The installer now detects an incomplete `.venv`, removes only `E:\MONTAGE_RUNTIME\.venv`, preserves the rest of `E:\MONTAGE_RUNTIME`, and retries using the fallback package directory on E:. Do not manually delete source footage.

## ASC3ND Phase 3 proof

1. Open/create the ASC3ND project.
2. Open the Footage Factory.
3. Click **Connect**. Confirm FFmpeg and ffprobe show ready; Whisper should show ready after setup.
4. Click **Choose footage** and select `vc(1).mp4` from the E: drive.
5. Wait for the local import/probe to complete. Large files remain on the same computer; Vercel does not receive the media bytes.
6. Click **Transcribe locally**.
7. Reproduce the approved/reviewed Aug 12 **Why We Started** cut.
8. Reframe to 1080x1920.
9. Generate SRT and rendered captions.
10. Verify the active output.
11. Close the Studio tab, reopen the project, and confirm project/edit state survives.
12. Repeat the same workflow for Aug 19 and Aug 26.

## Phase 3 acceptance

PASS requires real ASC3ND footage, local transcript, reversible edit operations, 9:16 output, captions, verified MP4/SRT, reopen persistence, and $0 paid editor/Descript AI credits for the local production path.

## Storage note

The current MVP copies the selected source into the Montage workspace so the immutable source/project boundary is explicit. Because the workspace is on E:, the copy never consumes the constrained system drive. A future approved-root/link mode can eliminate the duplicate copy after the Phase 3 proof without changing StudioProject ownership.
