import pytest
from yappy_clipz.code_animator import presets, renderer, safety, spec as spec_mod

SPEC = {"title": "T", "durationSeconds": 3, "fps": 24, "aspect": "16:9",
        "style": "particles-reveal", "beats": []}
needs_browser = pytest.mark.skipif(not renderer.renderer_available(), reason="no chromium/playwright")


def test_presets_listed():
    assert len(presets.style_ids()) >= 3
    for sid in presets.style_ids():
        assert "draw" in presets.preset(sid)["starter"]


def test_lint_rejects_network_and_requires_draw():
    bad = safety.lint_code("function draw(){fetch('http://x')}")
    assert not bad.ok and any("fetch" in p for p in bad.problems)
    nodraw = safety.lint_code("var a=1;")
    assert not nodraw.ok and not nodraw.has_draw
    assert safety.lint_code(presets.preset("clean-title")["starter"]).ok


@needs_browser
def test_render_is_deterministic_across_processes(tmp_path):
    code = presets.preset("particles-reveal")["starter"]
    a = renderer.run_isolated({"op": "video", "spec": SPEC, "code": code, "out": str(tmp_path / "a.mp4")})
    b = renderer.run_isolated({"op": "video", "spec": SPEC, "code": code, "out": str(tmp_path / "b.mp4")})
    assert a["frames"] == 72 and a["frameHashDigest"] == b["frameHashDigest"]


@needs_browser
def test_timeout_kills_runaway(tmp_path):
    with pytest.raises(renderer.AnimatorRenderError):
        renderer.run_isolated({"op": "stills", "spec": SPEC, "code": "function draw(){while(true){}}",
                               "times": [0.5], "outDir": str(tmp_path)}, timeout=6)
