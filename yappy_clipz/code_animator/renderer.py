"""Frame-function renderer: Playwright (system chromium) draws frames, FFmpeg stitches them.

Rendering always runs in an isolated child process (run_isolated) so a stuck or
hostile draw(t) can be killed on timeout without touching the API process.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from .harness import init_script, page_html
from .presets import preset
from .safety import lint_code
from .spec import AnimationSpec, parse_spec

_RENDER_LOCK = threading.Semaphore(1)  # one chromium at a time on a small box
DEFAULT_TIMEOUT_SECONDS = 600
CHROMIUM_ARGS = [
    "--no-sandbox",  # known limitation: see docs/CODE-ANIMATOR.md
    "--disable-gpu", "--disable-3d-apis", "--disable-dev-shm-usage",
    "--font-render-hinting=none", "--disable-lcd-text", "--force-color-profile=srgb", "--hide-scrollbars",
]


class AnimatorRenderError(RuntimeError):
    """Raised when rendering fails; message is safe to show to the caller."""


def chromium_path() -> str:
    explicit = os.environ.get("YAPPY_ANIMATOR_CHROMIUM")
    if explicit and os.path.isfile(explicit):
        return explicit
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    raise AnimatorRenderError("no chromium executable found (set YAPPY_ANIMATOR_CHROMIUM)")


def renderer_available() -> bool:
    try:
        chromium_path()
        import playwright  # noqa: F401
        return shutil.which("ffmpeg") is not None
    except (AnimatorRenderError, ImportError):
        return False


def _frame_times(spec: AnimationSpec) -> list[tuple[int, float]]:
    return [(i, i / spec.fps) for i in range(spec.frame_count)]


class _Session:
    """One browser context with the draw code loaded and the network shut."""

    def __init__(self, spec: AnimationSpec, code: str) -> None:
        from playwright.sync_api import sync_playwright

        self.spec = spec
        self.blocked: list[str] = []
        self.page_errors: list[str] = []
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(executable_path=chromium_path(), args=CHROMIUM_ARGS)
            context = self._browser.new_context(
                viewport={"width": spec.width, "height": spec.height}, service_workers="block",
                accept_downloads=False, permissions=[], bypass_csp=False,
            )
            context.route("**/*", self._abort)
            context.add_init_script(init_script(spec, preset(spec.style)["palette"]))
            self.page = context.new_page()
            self.page.on("pageerror", lambda exc: self.page_errors.append(str(exc)[:300]))
            self.page.set_content(page_html(spec))
            self.page.add_script_tag(content=code)
            if not self.page.evaluate("window.__animator.ready()"):
                raise AnimatorRenderError("draw is not defined as a function after loading the code")
        except Exception:
            self.close()
            raise

    def _abort(self, route: Any) -> None:
        url = route.request.url
        if not url.startswith(("data:", "about:", "blob:")):
            self.blocked.append(url[:200])
        route.abort()

    def frame_png(self, t: float, index: int) -> bytes:
        try:
            data = self.page.evaluate("([t, i]) => window.__animator.frame(t, i)", [t, index])
        except Exception as exc:
            detail = self.page_errors[-1] if self.page_errors else str(exc)
            raise AnimatorRenderError(f"draw(t) failed at t={t:.3f}s: {detail[:300]}") from exc
        return base64.b64decode(data)

    def close(self) -> None:
        for closer in (getattr(self, "_browser", None), getattr(self, "_pw", None)):
            try:
                if closer is not None:
                    closer.close() if hasattr(closer, "close") else closer.stop()
            except Exception:
                pass
        try:
            self._pw.stop()
        except Exception:
            pass


def _ffmpeg_cmd(spec: AnimationSpec, out: Path) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(spec.fps), "-c:v", "png", "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", str(spec.fps), "-movflags", "+faststart", str(out),
    ]


def render_stills(spec: AnimationSpec, code: str, times: list[float], out_dir: Path) -> dict[str, Any]:
    """Render the frames nearest to each time. Used for storyboards and contact sheets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    session = _Session(spec, code)
    files = []
    try:
        for t in times:
            index = min(spec.frame_count - 1, max(0, int(round(t * spec.fps))))
            png = session.frame_png(index / spec.fps, index)
            path = out_dir / f"still_{index:05d}.png"
            path.write_bytes(png)
            files.append({"t": round(index / spec.fps, 3), "index": index, "path": str(path),
                          "sha256": hashlib.sha256(png).hexdigest()})
        return {"stills": files, "blockedRequests": session.blocked, "pageErrors": session.page_errors}
    finally:
        session.close()


def render_video(spec: AnimationSpec, code: str, out: Path, *, max_frames: int | None = None) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    session = _Session(spec, code)
    ff = subprocess.Popen(_ffmpeg_cmd(spec, out), stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    hashes: list[str] = []
    try:
        # Order-independence probe: frame N, then frame 0, then frame N again must hash the same.
        mid = spec.frame_count // 2
        first = hashlib.sha256(session.frame_png(mid / spec.fps, mid)).hexdigest()
        session.frame_png(0.0, 0)
        again = hashlib.sha256(session.frame_png(mid / spec.fps, mid)).hexdigest()
        if first != again:
            raise AnimatorRenderError("draw(t) is not deterministic: the same t produced different frames")
        for index, t in _frame_times(spec)[: max_frames or spec.frame_count]:
            png = session.frame_png(t, index)
            hashes.append(hashlib.sha256(png).hexdigest())
            assert ff.stdin is not None
            ff.stdin.write(png)
        assert ff.stdin is not None
        ff.stdin.close()
        err = ff.stderr.read().decode("utf-8", "replace") if ff.stderr else ""
        if ff.wait() != 0:
            raise AnimatorRenderError("ffmpeg failed: " + err[-300:])
    except BrokenPipeError as exc:
        err = ff.stderr.read().decode("utf-8", "replace") if ff.stderr else ""
        raise AnimatorRenderError("ffmpeg closed the pipe: " + err[-300:]) from exc
    finally:
        session.close()
        if ff.poll() is None:
            ff.kill()
    digest = hashlib.sha256("".join(hashes).encode()).hexdigest()
    return {
        "output": str(out), "bytes": out.stat().st_size, "frames": len(hashes),
        "frameHashDigest": "sha256:" + digest, "probeFrameSha256": first,
        "blockedRequests": session.blocked, "pageErrors": session.page_errors,
    }


def _child_main() -> None:
    job = json.loads(sys.stdin.read())
    spec = parse_spec(job["spec"])
    code = job["code"]
    lint = lint_code(code)
    if not lint.ok:
        raise AnimatorRenderError("code rejected: " + "; ".join(lint.problems))
    if job["op"] == "stills":
        result = render_stills(spec, code, [float(t) for t in job["times"]], Path(job["outDir"]))
    elif job["op"] == "video":
        result = render_video(spec, code, Path(job["out"]))
    else:
        raise AnimatorRenderError("unknown operation")
    sys.stdout.write("\n@@RESULT@@" + json.dumps(result) + "\n")


# Repo root = the directory holding the yappy_clipz package, wherever the server was started from.
_APP_ROOT = str(Path(__file__).resolve().parents[2])


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = _APP_ROOT + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def run_isolated(job: dict[str, Any], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run one render in a child process group; kill it all on timeout."""
    with _RENDER_LOCK:
        proc = subprocess.Popen(
            [sys.executable, "-m", "yappy_clipz.code_animator.renderer"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, cwd=_APP_ROOT, env=_child_env(),
        )
        try:
            stdout, stderr = proc.communicate(json.dumps(job).encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise AnimatorRenderError(f"render exceeded {timeout}s and was killed") from None
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
    text = stdout.decode("utf-8", "replace")
    if proc.returncode != 0 or "@@RESULT@@" not in text:
        tail = (stderr.decode("utf-8", "replace").strip().splitlines() or ["render failed"])[-1]
        raise AnimatorRenderError(tail[:400])
    return json.loads(text.rsplit("@@RESULT@@", 1)[1].strip())


if __name__ == "__main__":
    try:
        _child_main()
    except AnimatorRenderError as exc:
        sys.stderr.write(str(exc) + "\n")
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        sys.exit(1)
