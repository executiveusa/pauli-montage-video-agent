"""Redis-backed asynchronous job worker with explicit handler registration."""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from pathlib import Path
from redis.exceptions import RedisError
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


def health_path() -> Path:
    return Path(os.getenv("YAPPY_WORKER_HEALTH_FILE", "/tmp/montage-worker-heartbeat"))


def run(on_idle=None) -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    client = Redis.from_url(os.getenv("YAPPY_REDIS_URL") or os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
                            socket_connect_timeout=3, socket_timeout=10)
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    stopped = threading.Event()
    def maintenance():
        # Sweeping must continue while the foreground worker renders a long clip.
        while not stopped.is_set():
            try:
                client.ping()
                if on_idle is not None:
                    on_idle()
                health_path().touch()
            except Exception:
                LOG.error("worker recovery or queue health check failed")
            stopped.wait(5)
    maintenance_thread = threading.Thread(target=maintenance, daemon=True, name="worker-recovery")
    maintenance_thread.start()
    LOG.info("worker ready")
    try:
        while not _STOP:
            try:
                item = client.blpop(QUEUE, timeout=5)
            except RedisError:
                LOG.error("queue unavailable; retrying")
                stopped.wait(2)
                continue
            if item is None:
                continue
            _, raw = item
            job_id = "unknown"
            try:
                # Capture identity before execution so failures don't share an
                # 'unknown' result key. This result is only a transport cache.
                payload = json.loads(raw) if len(raw) <= MAX_PAYLOAD_BYTES else None
                if isinstance(payload, dict) and isinstance(payload.get("job_id"), str):
                    job_id = payload["job_id"]
                job_id, result = process_payload(raw)
                envelope = {"status": "succeeded", "result": result}
            except Exception:
                LOG.error("job failed; inspect its durable status")
                envelope = {"status": "failed", "error": "Job failed. Inspect its durable status."}
            try:
                client.setex(f"{RESULT_PREFIX}{job_id}", 86_400, json.dumps(envelope))
            except RedisError:
                LOG.error("result cache unavailable; durable job state is preserved")
    finally:
        stopped.set()
        maintenance_thread.join(timeout=5)
        health_path().unlink(missing_ok=True)
        client.close()
        LOG.info("worker stopped")


if __name__ == "__main__":
    run()
