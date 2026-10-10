"""Client for the craft render service. Uploads inputs, runs a stage, downloads the named outputs, cleans up."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from . import imagecraft
from .pdfcraft import CraftRunError

# Internal-only service: never send these requests through HTTP(S)_PROXY.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def input_names(engine: str, inputs: list[bytes]) -> list[str]:
    """Fixed server-side names: in0..inN.pdf for documents, in0.png / in0.jpg (by magic bytes) for images."""
    if engine in imagecraft.ENGINES:
        try:
            ext = imagecraft.sniff(inputs[0])[0] if len(inputs) == 1 else None
        except imagecraft.ImageSpecError as exc:
            raise CraftRunError(str(exc)) from exc
        if ext is None:
            raise CraftRunError("image engines take exactly one input")
        return [f"in0.{ext}"]
    return [f"in{i}.pdf" for i in range(len(inputs))]


class RemoteCraftRunner:
    def __init__(self, base_url: str, *, timeout: int = 200) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Any = None, *, raw_body: bytes | None = None, raw: bool = False, timeout: int | None = None) -> Any:
        data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"content-type": "application/octet-stream" if raw_body is not None else "application/json"})
        try:
            with _OPENER.open(req, timeout=timeout or self.timeout) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read().decode()).get("error", "craft service error")
            except Exception:  # noqa: BLE001
                message = "craft service error"
            raise CraftRunError(f"craft service: {message}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CraftRunError(f"craft service unreachable: {exc}") from None
        return payload if raw else json.loads(payload.decode())

    def healthy(self, engine: str = "pdfcraft") -> bool:
        try:
            doc = self._request("GET", "/healthz", timeout=3)
            return bool((doc.get("ready") or {}).get(engine, doc.get("available") if engine == "pdfcraft" else False))
        except CraftRunError:
            return False

    def __call__(self, engine: str, stage: str, *, inputs: list[bytes], spec: dict[str, Any] | None = None, out_dir: Path | None = None) -> dict[str, Any]:
        job_id = "c" + uuid.uuid4().hex
        names = input_names(engine, inputs)
        try:
            for name, data in zip(names, inputs):
                self._request("PUT", f"/v1/jobs/{job_id}/inputs/{name}", raw_body=data)
            result = self._request("POST", "/v1/run", {"jobId": job_id, "engine": engine, "stage": stage, "inputs": names, "spec": spec})
            if stage == "build" and out_dir is not None:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "previews").mkdir(exist_ok=True)
                (out_dir / result["output"]).write_bytes(self._request("GET", f"/v1/files/{job_id}/{result['output']}", raw=True))
                for p in result.get("previews", []):
                    (out_dir / p["file"]).write_bytes(self._request("GET", f"/v1/files/{job_id}/{p['file']}", raw=True))
            return result
        finally:
            try:
                self._request("DELETE", f"/v1/jobs/{job_id}", timeout=10)
            except CraftRunError:
                pass


class LocalCraftRunner:
    """Runs the engine binary directly in a scratch directory. Dev and tests only; production uses the container."""

    def __init__(self, scratch: Path) -> None:
        self.scratch = Path(scratch)

    def healthy(self, engine: str = "pdfcraft") -> bool:
        from . import pdfcraft
        return imagecraft.binary_available(engine) if engine in imagecraft.ENGINES else pdfcraft.binary_available()

    def __call__(self, engine: str, stage: str, *, inputs: list[bytes], spec: dict[str, Any] | None = None, out_dir: Path | None = None) -> dict[str, Any]:
        import shutil
        from . import pdfcraft
        job_dir = self.scratch / ("c" + uuid.uuid4().hex)
        job_dir.mkdir(parents=True)
        try:
            names = input_names(engine, inputs)
            for name, data in zip(names, inputs):
                (job_dir / name).write_bytes(data)
            if engine in imagecraft.ENGINES:
                if stage == "info":
                    return imagecraft.run_info(engine, job_dir, names)
                result = imagecraft.run_build(engine, job_dir, spec or {}, names)
            elif stage == "info":
                return pdfcraft.run_info(job_dir, names)
            else:
                result = pdfcraft.run_build(job_dir, spec or {}, names)
            if out_dir is not None:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "previews").mkdir(exist_ok=True)
                shutil.copyfile(job_dir / result["output"], out_dir / result["output"])
                for p in result.get("previews", []):
                    (out_dir / p["file"]).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(job_dir / p["file"], out_dir / p["file"])
            return result
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)
