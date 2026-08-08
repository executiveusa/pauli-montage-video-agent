#!/usr/bin/env python3
"""Download/initialize the configured Faster-Whisper model for Montage local editing."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prewarm a Faster-Whisper model for Montage.")
    parser.add_argument("--model", default="base")
    parser.add_argument("--cache", required=True)
    args = parser.parse_args()

    cache = Path(args.cache).expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True)
    model_dir = cache / args.model

    try:
        from faster_whisper import WhisperModel
        from faster_whisper.utils import download_model
    except ImportError as exc:
        raise SystemExit("faster-whisper is not installed in this Python environment") from exc

    # Use Faster-Whisper's explicit output directory instead of the Hugging Face
    # blob/snapshot cache. On Windows external drives this avoids symlink creation
    # entirely and gives Montage one stable local model directory on E:.
    model_path = Path(download_model(args.model, output_dir=str(model_dir))).resolve()
    WhisperModel(str(model_path), device="cpu", compute_type="int8")
    print(f"Montage Whisper model ready: {args.model}")
    print(f"Model path: {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
