from tools.analysis.storyboard_query_planner import StoryboardQueryPlanner, decompose_storyboard_query


def test_silent_timelapse_visual_query_does_not_require_transcript():
    plan = decompose_storyboard_query(
        "Find silent waterfront timelapse establishing shots from 2020, no people, about 30 seconds"
    )
    assert plan["transcript_required"] is False
    assert "waterfront" in plan["visual"]["environments"]
    assert "timelapse" in plan["visual"]["motion"]
    assert "establishing" in plan["editorial_functions"]
    assert plan["chronology"]["years"] == ["2020"]
    assert "dialogue_required" in plan["exclusions"]
    assert "people" in plan["exclusions"]
    assert plan["requested_duration_seconds"] == 30
    assert any(q["kind"] == "visual" for q in plan["subqueries"])


def test_editorial_and_action_terms_are_separated():
    plan = decompose_storyboard_query(
        "Build an emotional opening montage of people walking through city streets and arriving at the airport"
    )
    assert "opening" in plan["editorial_functions"]
    assert "montage" in plan["editorial_functions"]
    assert "emotional_beat" in plan["editorial_functions"]
    assert "walking" in plan["visual"]["actions"]
    assert "arriving" in plan["visual"]["actions"]
    assert "city" in plan["visual"]["environments"]
    assert "streets" in plan["visual"]["environments"]
    assert "airport" in plan["visual"]["environments"]


def test_minutes_are_normalized_to_seconds():
    plan = decompose_storyboard_query("Create a 2 minute closing montage")
    assert plan["requested_duration_seconds"] == 120


def test_tool_rejects_empty_request():
    result = StoryboardQueryPlanner().execute({"request": "   "})
    assert result.success is False
    assert result.error == "request is required"


def test_tool_returns_retrieval_ready_schema():
    result = StoryboardQueryPlanner().execute({"request": "Find drone shots of the harbor"})
    assert result.success is True
    assert result.data["schema"] == "montage.storyboard-query.v1"
    assert "aerial" in result.data["visual"]["motion"]
    assert "harbor" in result.data["visual"]["environments"]
