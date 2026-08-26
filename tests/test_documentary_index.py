from datetime import datetime, timezone

from tools.analysis.documentary_index import resolve_capture_date, temporal_sample_budget


def test_embedded_creation_time_beats_backup_modified_time():
    result = resolve_capture_date(
        "GH020173.MP4",
        "2021-04-13T05:49:46Z",
        datetime(2025, 5, 26, tzinfo=timezone.utc).timestamp(),
    )
    assert result["captured_at"].startswith("2021-04-13T05:49:46")
    assert result["source"] == "embedded_creation_time"
    assert result["confidence"] == "high"


def test_filename_date_beats_filesystem_backup_timestamp():
    result = resolve_capture_date(
        "20200924_090156.mp4",
        None,
        datetime(2025, 5, 26, tzinfo=timezone.utc).timestamp(),
    )
    assert result["captured_at"].startswith("2020-09-24T09:01:56")
    assert result["source"] == "filename"
    assert result["confidence"] == "high"


def test_unknown_filename_falls_back_without_pretending_high_confidence():
    result = resolve_capture_date(
        "storm-with-fats-final-copy.mov",
        None,
        datetime(2020, 10, 17, tzinfo=timezone.utc).timestamp(),
    )
    assert result["captured_at"].startswith("2020-10-17")
    assert result["source"] == "filesystem_modified_time"
    assert result["confidence"] == "low"


def test_temporal_budget_scales_but_stays_bounded():
    assert temporal_sample_budget(15) == 12
    assert temporal_sample_budget(120) == 20
    assert temporal_sample_budget(500) == 32
    assert temporal_sample_budget(1200) == 48
    assert temporal_sample_budget(7200) == 64
