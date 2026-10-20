"""Durable render worker entrypoint: canonical services on the existing queue."""
from __future__ import annotations

from .factory import create_runtime
from .render_queue import register_render_worker
from .worker import run


def main() -> None:
    runtime = create_runtime()
    register_render_worker(runtime)
    run(on_idle=lambda: runtime.rendering.recover_stale())


if __name__ == "__main__":
    main()
