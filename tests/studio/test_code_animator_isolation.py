"""Renderer isolation: scrubbed env, job-scoped paths, service split, no network/file reads from the page."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from yappy_clipz.code_animator import presets, remote, render_service, renderer

SPEC = {"title": "T", "durationSeconds": 3, "fps": 24, "aspect": "16:9", "style": "clean-title", "beats": []}
CODE = presets.preset("clean-title")["starter"]
needs_browser = pytest.mark.skipif(not renderer.renderer_available(), reason="no chromium/playwright")
SECRETS = {"DATABASE_URL": "postgres://u:p@h/db", "YAPPY_SIGNING_SECRET": "s3cr3t", "AWS_SECRET_ACCESS_KEY": "k",
           "REDIS_URL": "redis://x", "SUPABASE_SERVICE_ROLE_KEY": "z", "FAL_KEY": "f", "ANIMATOR_TEST_TOKEN": "t"}


def test_child_env_is_an_allowlist(monkeypatch, tmp_path):
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    env = renderer._child_env(str(tmp_path))
    assert not set(SECRETS) & set(env)
    assert set(env) <= set(renderer._ENV_ALLOW) | {"PYTHONPATH", "HOME", "TMPDIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "PYTHONDONTWRITEBYTECODE", "PYTHONUSERBASE"}
    assert env["HOME"] == str(tmp_path)


def test_real_render_child_carries_no_secrets_and_runs_in_private_scratch(monkeypatch, tmp_path):
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("YAPPY_ANIMATOR_SCRATCH", str(tmp_path / "scratch"))
    report = renderer.run_isolated({"op": "env", "spec": SPEC, "code": CODE})
    assert not set(SECRETS) & set(report["env"]), report["env"]
    assert report["cwd"].startswith(str(tmp_path / "scratch"))
    assert report["home"] == report["cwd"]
    assert not any(p.exists() for p in (tmp_path / "scratch").iterdir()), "scratch dir must be removed after the render"


@pytest.fixture()
def service(tmp_path, monkeypatch):
    for k, v in SECRETS.items():
        monkeypatch.setenv(k, v)
    srv = render_service.make_server("127.0.0.1", 0, tmp_path / "work")
    (tmp_path / "work").mkdir()
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", tmp_path / "work"
    srv.shutdown()


def _post(url, body):
    req = urllib.request.Request(url + "/v1/render", data=json.dumps(body).encode(), method="POST", headers={"content-type": "application/json"})
    try:
        return urllib.request.urlopen(req).status, None
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_service_rejects_bad_payloads_and_traversal(service):
    url, work = service
    base = {"jobId": "job12345678", "op": "video", "spec": SPEC, "code": CODE}
    assert _post(url, {**base, "jobId": "../../etc"})[0] == 400
    assert _post(url, {**base, "jobId": "a/b/c/d/e/f/g/h"})[0] == 400
    assert _post(url, {**base, "op": "shell"})[0] == 400
    assert _post(url, {**base, "spec": {**SPEC, "durationSeconds": 9999}})[0] == 400
    assert _post(url, {**base, "code": "   "})[0] == 400
    assert _post(url, {**base, "code": "x" * (render_service.MAX_BODY_BYTES + 1)})[0] == 413
    for bad in ("../../etc/passwd", "stills/../../x", "a/b/c", ".env%00"):
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{url}/v1/files/job12345678/{bad}")
        assert exc.value.code in {400, 404}
    # an arbitrary file path in the payload is ignored: output paths are chosen by the service
    code, err = _post(url, {**base, "out": "/etc/cron.d/x", "outDir": "/tmp/x"})
    assert code in {200, 422}
    assert not __import__("pathlib").Path("/etc/cron.d/x").exists()


def test_read_file_cannot_escape_job_dir(tmp_path):
    root = tmp_path / "work"
    (root / "job12345678").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("nope")
    (root / "job12345678" / "link").symlink_to(tmp_path / "secret.txt")
    with pytest.raises(render_service.ServiceError):
        render_service.read_file(root.resolve(), "job12345678", "link")
    with pytest.raises(render_service.ServiceError):
        render_service.read_file(root.resolve(), "job12345678", "../secret.txt")


@needs_browser
def test_remote_runner_matches_local_render_bit_for_bit(service, tmp_path):
    url, work = service
    runner = remote.RemoteRunner(url, timeout=120)
    assert runner.healthy()
    local = renderer.run_isolated({"op": "video", "spec": SPEC, "code": CODE, "out": str(tmp_path / "l.mp4")})
    far = runner({"op": "video", "spec": SPEC, "code": CODE, "out": str(tmp_path / "r.mp4")})
    assert far["frameHashDigest"] == local["frameHashDigest"]
    assert (tmp_path / "r.mp4").stat().st_size > 1000
    stills = runner({"op": "stills", "spec": SPEC, "code": CODE, "times": [0.5, 1.5], "outDir": str(tmp_path / "s")})
    assert len(stills["stills"]) == 2 and all(__import__("pathlib").Path(s["path"]).exists() for s in stills["stills"])
    assert not any(p for p in work.iterdir()), "remote job dirs are deleted after download"


@needs_browser
def test_page_cannot_read_local_files_or_reach_the_network():
    spec = renderer.parse_spec(SPEC)
    session = renderer._Session(spec, CODE)
    try:
        probe = """async () => {
          const out = {};
          try { const x = new XMLHttpRequest(); x.open('GET', 'file:///etc/hostname', false); x.send(); out.file = x.responseText || 'empty'; } catch (e) { out.file = 'blocked'; }
          try { const r = await fetch('http://169.254.169.254/latest/meta-data/'); out.net = 'reached ' + r.status; } catch (e) { out.net = 'blocked'; }
          try { const r = await fetch('file:///etc/passwd'); out.fetchfile = 'reached'; } catch (e) { out.fetchfile = 'blocked'; }
          return out;
        }"""
        result = session.page.evaluate(probe)
    finally:
        session.close()
    assert result == {"file": "blocked", "net": "blocked", "fetchfile": "blocked"}, result


def test_remote_runner_ignores_proxy_environment(service, monkeypatch):
    url, _ = service
    for k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY"):
        monkeypatch.setenv(k, "http://127.0.0.1:9")  # dead port: any proxied request would fail
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    assert remote.RemoteRunner(url).healthy() is True
