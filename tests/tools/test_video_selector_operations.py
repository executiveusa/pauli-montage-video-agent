"""Generic-operation routing coverage for VideoSelector (PR 56 review, P1).

The generic branch of _filter_candidates treated a missing
is_operation_available() checker as ready=True, so providers with no editing
capability (e.g. seedance_video) were admitted to video_edit routes, and
providers using the native edit_video spelling (Gemini) never matched the
selector's video_edit name. These tests pin the fixed behavior.
"""

from __future__ import annotations

from tools.video.video_selector import VideoSelector


class _Tool:
    def __init__(self, name, *, supports=None, enum_ops=None, checker=None):
        self.name = name
        self.provider = name
        self.supports = supports or {}
        self.input_schema = {"properties": {}}
        if enum_ops is not None:
            self.input_schema["properties"]["operation"] = {"enum": list(enum_ops)}
        if checker is not None:
            self.is_operation_available = checker


def _selector() -> VideoSelector:
    return VideoSelector()


def test_video_edit_excludes_provider_without_capability_evidence():
    seedance_like = _Tool("seedance_video", supports={"text_to_video": True, "image_to_video": True})
    gemini_like = _Tool("gemini_omni_video", supports={"text_to_video": True, "edit_video": True},
                        enum_ops=["text_to_video", "image_to_video", "edit_video"])
    routed = _selector()._filter_candidates({"operation": "video_edit"}, [seedance_like, gemini_like])
    assert [tool.name for tool in routed] == ["gemini_omni_video"]


def test_video_edit_alias_reaches_native_edit_video_spelling():
    gemini_like = _Tool("gemini_omni_video", enum_ops=["text_to_video", "edit_video"])
    routed = _selector()._filter_candidates({"operation": "video_edit"}, [gemini_like])
    assert [tool.name for tool in routed] == ["gemini_omni_video"]


def test_provider_checker_stays_authoritative_when_present():
    atlas_like = _Tool("atlas_video", checker=lambda op: op == "video_edit")
    refusing = _Tool("other_video", supports={"edit_video": True}, checker=lambda op: False)
    routed = _selector()._filter_candidates({"operation": "video_edit"}, [refusing, atlas_like])
    assert [tool.name for tool in routed] == ["atlas_video"]


def test_unsupported_operation_falls_back_to_all_candidates():
    seedance_like = _Tool("seedance_video", supports={"text_to_video": True})
    gemini_like = _Tool("gemini_omni_video", supports={"text_to_video": True, "edit_video": True})
    routed = _selector()._filter_candidates({"operation": "upscale_video"}, [seedance_like, gemini_like])
    assert {tool.name for tool in routed} == {"seedance_video", "gemini_omni_video"}


def test_default_text_to_video_still_admits_declaring_providers():
    seedance_like = _Tool("seedance_video", supports={"text_to_video": True})
    undeclared = _Tool("mystery_video")
    routed = _selector()._filter_candidates({"operation": "text_to_video"}, [undeclared, seedance_like])
    assert [tool.name for tool in routed] == ["seedance_video"]
