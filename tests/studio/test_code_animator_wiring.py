"""API-side wiring for the isolated renderer (needs the full API dependency set)."""
from __future__ import annotations

import pytest

from yappy_clipz.code_animator import renderer
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings


def test_production_refuses_local_rendering_without_the_service(monkeypatch, tmp_path):
    from yappy_clipz.factory import create_runtime
    from yappy_clipz.settings import Settings
    monkeypatch.setenv("YAPPY_ANIMATOR_REQUIRE_REMOTE", "1")
    monkeypatch.delenv("YAPPY_ANIMATOR_RENDERER_URL", raising=False)
    rt = create_runtime(settings=Settings(project_root=tmp_path / "data"))
    assert rt.animator.engine_descriptor()["available"] is False
    with pytest.raises(renderer.AnimatorRenderError):
        rt.animator.runner({"op": "video"})


def test_animator_root_follows_env(monkeypatch, tmp_path):
    from yappy_clipz.factory import create_runtime
    from yappy_clipz.settings import Settings
    monkeypatch.setenv("YAPPY_ANIMATOR_ROOT", str(tmp_path / "vol"))
    rt = create_runtime(settings=Settings(project_root=tmp_path / "data"))
    assert str(rt.animator.root) == str(tmp_path / "vol")
