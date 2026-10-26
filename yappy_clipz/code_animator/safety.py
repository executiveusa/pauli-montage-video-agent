"""Static checks for model/agent-supplied draw(t) code.

This is defense in depth only. The security boundary is the render browser:
a fresh context per render, every network request aborted, no file access, a
whole-render timeout enforced by killing the isolated render process, and one
render at a time. The denylist exists to fail fast with a readable message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .spec import MAX_CODE_BYTES

_DENY = [
    (r"\bfetch\s*\(", "fetch"),
    (r"\bimport\s*[\(\{\w\*\"']", "import"),
    (r"\beval\s*\(", "eval"),
    (r"\bFunction\s*\(", "Function constructor"),
    (r"\bXMLHttpRequest\b", "XMLHttpRequest"),
    (r"\bWebSocket\b", "WebSocket"),
    (r"\bEventSource\b", "EventSource"),
    (r"\bsendBeacon\b", "sendBeacon"),
    (r"\bimportScripts\b", "importScripts"),
    (r"\bServiceWorker\b|\bnavigator\.serviceWorker\b", "service workers"),
    (r"\bdocument\.cookie\b|\blocalStorage\b|\bsessionStorage\b|\bindexedDB\b", "storage"),
    (r"\bwindow\.open\b|\blocation\s*=|\blocation\.(href|assign|replace)\b", "navigation"),
    (r"\bnew\s+Worker\b|\bSharedWorker\b", "workers"),
    (r"\bgetContext\s*\(\s*['\"](webgl|webgl2|experimental-webgl|bitmaprenderer)", "WebGL (canvas 2D only)"),
    (r"\bsetTimeout\b|\bsetInterval\b|\brequestAnimationFrame\b", "timers (draw must be a pure function of t)"),
    (r"\bMath\.random\s*=", "overriding Math.random"),
]
_COMPILED = [(re.compile(pattern), label) for pattern, label in _DENY]


@dataclass(frozen=True)
class LintResult:
    ok: bool
    problems: tuple[str, ...]
    bytes: int
    has_draw: bool

    def to_dict(self) -> dict:
        return {"ok": self.ok, "problems": list(self.problems), "bytes": self.bytes, "hasDraw": self.has_draw}


def _strip_comments_and_strings(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    code = re.sub(r"(^|[^:\\])//[^\n]*", r"\1", code)
    return code


def lint_code(code: str) -> LintResult:
    problems: list[str] = []
    size = len(code.encode("utf-8"))
    if not isinstance(code, str) or not code.strip():
        return LintResult(False, ("code is empty",), size, False)
    if size > MAX_CODE_BYTES:
        problems.append(f"code is {size} bytes; the limit is {MAX_CODE_BYTES}")
    stripped = _strip_comments_and_strings(code)
    for pattern, label in _COMPILED:
        if pattern.search(stripped):
            problems.append(f"not allowed: {label}")
    has_draw = bool(re.search(r"\bfunction\s+draw\s*\(|\b(window\.)?draw\s*=\s*(function|\(|async)", stripped))
    if not has_draw:
        problems.append("code must define draw(ctx, t, env)")
    return LintResult(not problems, tuple(problems), size, has_draw)
