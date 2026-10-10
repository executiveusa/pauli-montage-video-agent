"""Client for the isolated render service. Same call shape as renderer.run_isolated."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from .renderer import AnimatorRenderError


class RemoteRunner:
    def __init__(self, base_url: str, *, timeout: int = 700) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None, *, raw: bool = False, timeout: int | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read().decode()).get("error", "render service error")
            except Exception:  # noqa: BLE001
                message = "render service error"
            raise AnimatorRenderError(f"render service: {message}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AnimatorRenderError(f"render service unreachable: {exc}") from None
        return payload if raw else json.loads(payload.decode())

    def healthy(self) -> bool:
        try:
            return bool(self._request("GET", "/healthz", timeout=3).get("available"))
        except AnimatorRenderError:
            return False

    def __call__(self, job: dict[str, Any]) -> dict[str, Any]:
        job_id = "r" + uuid.uuid4().hex
        payload = {"jobId": job_id, "op": job["op"], "spec": job["spec"], "code": job["code"]}
        if job["op"] == "stills":
            payload["times"] = job["times"]
        try:
            result = self._request("POST", "/v1/render", payload)
            if job["op"] == "stills":
                out_dir = Path(job["outDir"])
                out_dir.mkdir(parents=True, exist_ok=True)
                for still in result["stills"]:
                    name = Path(still["path"]).name
                    (out_dir / name).write_bytes(self._request("GET", f"/v1/files/{job_id}/stills/{name}", raw=True))
                    still["path"] = str(out_dir / name)
            else:
                out = Path(job["out"])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(self._request("GET", f"/v1/files/{job_id}/out.mp4", raw=True))
                result["output"] = str(out)
            return result
        finally:
            try:
                self._request("DELETE", f"/v1/jobs/{job_id}", timeout=10)
            except AnimatorRenderError:
                pass
