"""Redis-backed asynchronous job worker with explicit handler registration."""

from __future__ import annotations

import json
import logging
import os
import signal
from collections.abc import Callable
from typing import Any

from redis import Redis

LOG = logging.getLogger("yappy_clipz.worker")
QUEUE = "yappy:jobs:ready"
RESULT_PREFIX = "yappy:jobs:result:"
MAX_PAYLOAD_BYTES = 256_000
_STOP = False
JobHandler = Callable[[dict[str, Any]], dict[str, Any]]
_HANDLERS: dict[str, JobHandler] = {}


def register_handler(name: str, handler: JobHandler) -> None:
    if not name or name in _HANDLERS:
        raise ValueError("handler name must be unique")
    _HANDLERS[name] = handler


def _request_stop(*_: object) -> None:
    global _STOP
    _STOP = True


def process_payload(raw: bytes) -> tuple[str, dict[str, Any]]:
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("job payload too large")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("job payload must be an object")
    job_id = payload.get("job_id")
    job_type = payload.get("type")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("job_id is required")
    if not isinstance(job_type, str) or job_type not in _HANDLERS:
        raise ValueError("unsupported job type")
    return job_id, _HANDLERS[job_type](payload)


def run() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    client = Redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    client.ping()
    LOG.info("worker ready")
    while not _STOP:
        item = client.blpop(QUEUE, timeout=5)
        if item is None:
            continue
        _, raw = item
        job_id = "unknown"
        try:
            job_id, result = process_payload(raw)
            envelope = {"status": "succeeded", "result": result}
        except Exception as exc:
            LOG.exception("job failed")
            envelope = {"status": "failed", "error": str(exc)}
        client.setex(f"{RESULT_PREFIX}{job_id}", 86_400, json.dumps(envelope))
    LOG.info("worker stopped")


if __name__ == "__main__":
    run()
