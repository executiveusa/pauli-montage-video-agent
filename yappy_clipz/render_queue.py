"""Redis dispatch glue for the canonical render pipeline.

RenderService.submit persists the durable operations job; this module publishes
that same job onto the existing worker queue (yappy:jobs:ready) so the durable
worker executes it through RenderService.execute. No competing job system: the
operations store stays the source of truth and Redis is only the wake-up transport.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .worker import QUEUE


class RedisRenderPublisher:
    """Publishes persisted render jobs to the durable worker queue."""

    def __init__(self, redis_url: str) -> None:
        from redis import Redis  # lazy import: only required when a queue is configured

        self._client = Redis.from_url(redis_url)

    def publish_render_job(self, *, tenant_id: str, job_id: str) -> None:
        payload = json.dumps({"type": "render.execute", "job_id": job_id, "tenant_id": tenant_id})
        self._client.rpush(QUEUE, payload)


def render_execute_handler(runtime: Any, *, worker_id: str):
    """Build the worker handler that executes one persisted render job."""

    def _handle(payload: dict[str, Any]) -> dict[str, Any]:
        job_id = payload.get("job_id")
        tenant_id = payload.get("tenant_id")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("render.execute payload requires job_id")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise ValueError("render.execute payload requires tenant_id")
        result = runtime.rendering.execute(tenant_id=tenant_id, job_id=job_id, worker_id=worker_id)
        job = result["job"]
        return {"jobId": job["id"], "state": job["state"], "outputRefs": list(job.get("outputRefs") or [])}

    return _handle


def register_render_worker(runtime: Any, *, worker_id: str | None = None) -> str:
    """Register render.execute on the durable worker registry; returns the worker id."""
    from . import worker

    resolved = worker_id or os.environ.get("YAPPY_WORKER_ID") or f"worker-{os.uname().nodename}"
    worker.register_handler("render.execute", render_execute_handler(runtime, worker_id=resolved))
    return resolved
