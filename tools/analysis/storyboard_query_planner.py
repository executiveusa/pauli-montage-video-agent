"""Storyboard-style query decomposition for documentary retrieval.

Inspired by HKUDS VideoAgent's Storyboard Agent, but intentionally deterministic and
state-free. It converts broad natural-language edit/search requests into fine-grained
visual/editorial clauses that can be scored against Montage documentary manifests.
"""

from __future__ import annotations

import re
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'_-]*", re.I)
_DURATION = re.compile(r"\b(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m)\b", re.I)
_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

EDITORIAL_TERMS = {
    "establishing": "establishing",
    "establish": "establishing",
    "b-roll": "b_roll",
    "broll": "b_roll",
    "cutaway": "cutaway",
    "reaction": "reaction",
    "transition": "transition",
    "interview": "interview",
    "montage": "montage",
    "opening": "opening",
    "intro": "opening",
    "closing": "closing",
    "ending": "closing",
    "emotional": "emotional_beat",
    "emotion": "emotional_beat",
    "archive": "archival",
    "archival": "archival",
}

MOTION_TERMS = {
    "timelapse": "timelapse",
    "time-lapse": "timelapse",
    "hyperlapse": "hyperlapse",
    "slow-motion": "slow_motion",
    "slowmo": "slow_motion",
    "drone": "aerial",
    "aerial": "aerial",
    "handheld": "handheld",
    "tracking": "tracking",
    "static": "static",
    "pan": "pan",
    "tilt": "tilt",
}

ENVIRONMENT_TERMS = {
    "street", "streets", "city", "waterfront", "beach", "ocean", "sea", "harbor",
    "airport", "station", "market", "gym", "court", "home", "house", "school",
    "restaurant", "bar", "mountain", "forest", "park", "boat", "bus", "car",
}

ACTION_TERMS = {
    "walking", "running", "talking", "speaking", "laughing", "crying", "driving",
    "traveling", "travelling", "arriving", "leaving", "playing", "working", "eating",
    "cooking", "dancing", "fishing", "boarding", "entering", "exiting", "hugging",
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "build", "by", "can", "create",
    "do", "every", "find", "for", "from", "give", "i", "in", "into", "is", "it",
    "make", "me", "of", "on", "or", "our", "show", "shot", "shots", "that", "the",
    "this", "to", "video", "videos", "where", "with", "without", "you",
}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def decompose_storyboard_query(text: str) -> dict[str, Any]:
    raw = text.strip()
    lowered = raw.lower()
    tokens = [token.lower() for token in _TOKEN.findall(raw)]

    editorial = _unique([value for key, value in EDITORIAL_TERMS.items() if key in lowered])
    motion = _unique([value for key, value in MOTION_TERMS.items() if key in lowered])
    environments = _unique([token for token in tokens if token in ENVIRONMENT_TERMS])
    actions = _unique([token for token in tokens if token in ACTION_TERMS])
    years = _unique(_YEAR.findall(raw))

    exclusions: list[str] = []
    if "no dialogue" in lowered or "without dialogue" in lowered or "silent" in lowered:
        exclusions.append("dialogue_required")
    if "no people" in lowered or "without people" in lowered:
        exclusions.append("people")
    if "no music" in lowered or "without music" in lowered:
        exclusions.append("music")

    duration_seconds: float | None = None
    match = _DURATION.search(lowered)
    if match:
        value = float(match.group(1))
        unit = match.group(2).lower()
        duration_seconds = value * 60 if unit.startswith("m") else value

    concepts = _unique([
        token for token in tokens
        if token not in STOPWORDS
        and token not in ENVIRONMENT_TERMS
        and token not in ACTION_TERMS
        and not token.isdigit()
        and not re.fullmatch(r"19\d{2}|20\d{2}", token)
    ])

    subqueries: list[dict[str, Any]] = []
    if environments or actions or motion:
        subqueries.append({
            "kind": "visual",
            "terms": _unique(environments + actions + motion + concepts[:8]),
            "transcript_required": False,
        })
    if editorial:
        subqueries.append({
            "kind": "editorial",
            "terms": editorial,
            "transcript_required": False,
        })
    if years:
        subqueries.append({
            "kind": "chronology",
            "terms": years,
            "transcript_required": False,
        })
    if concepts and not subqueries:
        subqueries.append({
            "kind": "semantic",
            "terms": concepts[:12],
            "transcript_required": False,
        })

    return {
        "schema": "montage.storyboard-query.v1",
        "request": raw,
        "visual": {
            "environments": environments,
            "actions": actions,
            "motion": motion,
            "concepts": concepts[:16],
        },
        "editorial_functions": editorial,
        "chronology": {"years": years},
        "exclusions": exclusions,
        "requested_duration_seconds": duration_seconds,
        "subqueries": subqueries,
        "transcript_required": False,
    }


class StoryboardQueryPlanner(BaseTool):
    name = "storyboard_query_planner"
    version = "1.0.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "montage"
    stability = ToolStability.PRODUCTION
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    dependencies: list[str] = []
    capabilities = [
        "intent_decomposition",
        "storyboard_query_planning",
        "silent_video_search_planning",
        "editorial_query_planning",
    ]
    input_schema = {
        "type": "object",
        "required": ["request"],
        "properties": {"request": {"type": "string", "minLength": 1}},
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=0)
    idempotency_key_fields = ["request"]
    side_effects: list[str] = []
    user_visible_verification = ["Inspect generated visual/editorial subqueries before retrieval"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        request = str(inputs.get("request") or "").strip()
        if not request:
            return ToolResult(success=False, error="request is required")
        return ToolResult(success=True, data=decompose_storyboard_query(request))
