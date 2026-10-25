"""Synthetic test images (no client media): an asymmetric colour pattern so rotations and flips change pixels."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw


def make_image(width: int = 300, height: int = 200, fmt: str = "PNG") -> bytes:
    im = Image.new("RGB", (width, height), (200, 80, 40))
    d = ImageDraw.Draw(im)
    for x in range(0, width, 30):
        d.rectangle([x, 0, x + 14, height // 2], fill=(20, 60 + (x * 150 // max(width, 1)), 200))
    if height >= 60 and width >= 60:
        d.ellipse([width // 6, height // 2 + 10, width // 2, height - 10], fill=(250, 250, 0))
    buf = io.BytesIO()
    im.save(buf, format=fmt, **({"quality": 92} if fmt == "JPEG" else {}))
    return buf.getvalue()
