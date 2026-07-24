#!/usr/bin/env python3
"""Offline JSON Schema + semantic validation for YAPPY-CLIPZ contracts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "schemas"
EXAMPLE = ROOT / "examples" / "studio-project.v1.example.json"
ROOT_SCHEMA_ID = "https://yappyverse.studio/schemas/studio-project.v1.schema.json"


class ContractValidationError(ValueError):
    """Raised when structural or semantic contract validation fails."""


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_schemas(schema_dir: Path = SCHEMA_DIR) -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    registry: Registry = Registry()

    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = _read_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ContractValidationError(f"{path.name}: schema is missing a non-empty $id")
        if schema_id in schemas:
            raise ContractValidationError(f"duplicate schema $id: {schema_id}")
        schemas[schema_id] = schema
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))

    if ROOT_SCHEMA_ID not in schemas:
        raise ContractValidationError(f"root schema not found: {ROOT_SCHEMA_ID}")
    return schemas, registry


def _duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _ids(items: Iterable[dict[str, Any]]) -> set[str]:
    return {str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")}


def _by_id(items: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item["id"]): item
        for item in items
        if isinstance(item, dict) and item.get("id")
    }


def _require_refs(errors: list[str], refs: Iterable[str], allowed: set[str], label: str) -> None:
    for ref in refs:
        if ref not in allowed:
            errors.append(f"{label} references missing id: {ref}")


def semantic_errors(project: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    root = project.get("project", {})
    tenant_id = root.get("tenantId")
    project_id = root.get("id")

    collections = {
        "assets": project.get("assets", []),
        "elements": project.get("elements", []),
        "scenes": project.get("scenes", []),
        "shots": project.get("shots", []),
        "jobs": project.get("jobs", []),
        "approvals": project.get("approvals", []),
        "decisions": project.get("decisions", []),
        "events": project.get("events", []),
        "renders": project.get("renders", []),
        "exports": project.get("exports", []),
    }

    for name, items in collections.items():
        duplicates = _duplicates(str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id"))
        for duplicate in duplicates:
            errors.append(f"{name} contains duplicate id: {duplicate}")

    assets = _ids(collections["assets"])
    elements = _ids(collections["elements"])
    scenes = _ids(collections["scenes"])
    shots = _ids(collections["shots"])
    jobs = _ids(collections["jobs"])
    approvals = _ids(collections["approvals"])
    decisions = _ids(collections["decisions"])
    events = _ids(collections["events"])
    renders = _ids(collections["renders"])

    scenes_by_id = _by_id(collections["scenes"])
    shots_by_id = _by_id(collections["shots"])
    approvals_by_id = _by_id(collections["approvals"])

    for name in ("assets", "elements", "jobs", "approvals", "decisions", "events", "renders", "exports"):
        for item in collections[name]:
            if item.get("tenantId") != tenant_id:
                errors.append(f"{name}/{item.get('id')} tenantId does not match project tenantId")
            if item.get("projectId") != project_id:
                errors.append(f"{name}/{item.get('id')} projectId does not match project id")

    brief = project.get("brief", {})
    _require_refs(errors, brief.get("referenceAssetIds", []), assets, "brief.referenceAssetIds")

    brand = project.get("brand", {})
    _require_refs(errors, brand.get("logoAssetIds", []), assets, "brand.logoAssetIds")

    research = project.get("research", {})
    _require_refs(errors, research.get("sourceAssetIds", []), assets, "research.sourceAssetIds")

    script = project.get("script", {})
    if script.get("assetId") is not None:
        _require_refs(errors, [script["assetId"]], assets, "script.assetId")
    for beat in script.get("beats", []):
        _require_refs(errors, beat.get("sceneIds", []), scenes, f"script.beat/{beat.get('id')}.sceneIds")

    for asset in collections["assets"]:
        _require_refs(
            errors,
            asset.get("source", {}).get("parentAssetIds", []),
            assets,
            f"asset/{asset.get('id')}.source.parentAssetIds",
        )
        _require_refs(
            errors,
            asset.get("rights", {}).get("releaseAssetIds", []),
            assets,
            f"asset/{asset.get('id')}.rights.releaseAssetIds",
        )

    for element in collections["elements"]:
        _require_refs(errors, element.get("referenceAssetIds", []), assets, f"element/{element.get('id')}.referenceAssetIds")

    for scene in collections["scenes"]:
        scene_id = scene.get("id")
        _require_refs(errors, scene.get("elementIds", []), elements, f"scene/{scene_id}.elementIds")
        location = scene.get("locationElementId")
        if location is not None:
            _require_refs(errors, [location], elements, f"scene/{scene_id}.locationElementId")
        scene_shot_ids = scene.get("shotIds", [])
        _require_refs(errors, scene_shot_ids, shots, f"scene/{scene_id}.shotIds")
        for shot_id in scene_shot_ids:
            linked_shot = shots_by_id.get(shot_id)
            if linked_shot and linked_shot.get("sceneId") != scene_id:
                errors.append(
                    f"scene/{scene_id}.shotIds contains {shot_id} but shot/{shot_id}.sceneId is {linked_shot.get('sceneId')}"
                )

    for shot in collections["shots"]:
        shot_id = shot.get("id")
        scene_id = shot.get("sceneId")
        _require_refs(errors, [scene_id], scenes, f"shot/{shot_id}.sceneId")
        owning_scene = scenes_by_id.get(scene_id)
        if owning_scene and shot_id not in owning_scene.get("shotIds", []):
            errors.append(
                f"shot/{shot_id}.sceneId points to {scene_id} but scene/{scene_id}.shotIds does not contain {shot_id}"
            )
        _require_refs(errors, shot.get("elementIds", []), elements, f"shot/{shot_id}.elementIds")
        _require_refs(errors, shot.get("referenceAssetIds", []), assets, f"shot/{shot_id}.referenceAssetIds")
        _require_refs(errors, shot.get("generatedAssetIds", []), assets, f"shot/{shot_id}.generatedAssetIds")
        if shot.get("providerDecisionId") is not None:
            _require_refs(errors, [shot["providerDecisionId"]], decisions, f"shot/{shot_id}.providerDecisionId")

        shot_approval_ids = shot.get("approvalIds", [])
        _require_refs(errors, shot_approval_ids, approvals, f"shot/{shot_id}.approvalIds")
        for approval_id in shot_approval_ids:
            approval = approvals_by_id.get(approval_id)
            if not approval:
                continue
            if approval.get("scopeType") != "shot" or approval.get("subjectId") != shot_id:
                errors.append(
                    f"shot/{shot_id}.approvalIds contains {approval_id} but approval scope/subject does not match the shot"
                )

    timeline = project.get("timeline", {})
    track_ids = [track.get("id") for track in timeline.get("tracks", []) if track.get("id")]
    for duplicate in _duplicates(track_ids):
        errors.append(f"timeline contains duplicate track id: {duplicate}")
    item_ids: list[str] = []
    for track in timeline.get("tracks", []):
        for item in track.get("items", []):
            if item.get("id"):
                item_ids.append(item["id"])
            if item.get("assetId") is not None:
                _require_refs(errors, [item["assetId"]], assets, f"timeline.item/{item.get('id')}.assetId")
            if item.get("shotId") is not None:
                _require_refs(errors, [item["shotId"]], shots, f"timeline.item/{item.get('id')}.shotId")
    for duplicate in _duplicates(item_ids):
        errors.append(f"timeline contains duplicate item id: {duplicate}")

    for job in collections["jobs"]:
        route = job.get("providerRouteId")
        if route is not None:
            _require_refs(errors, [route], decisions, f"job/{job.get('id')}.providerRouteId")

    for render in collections["renders"]:
        if render.get("jobId") is not None:
            _require_refs(errors, [render["jobId"]], jobs, f"render/{render.get('id')}.jobId")
        if render.get("assetId") is not None:
            _require_refs(errors, [render["assetId"]], assets, f"render/{render.get('id')}.assetId")

    for export in collections["exports"]:
        if export.get("renderId") is not None:
            _require_refs(errors, [export["renderId"]], renders, f"export/{export.get('id')}.renderId")
        if export.get("assetId") is not None:
            _require_refs(errors, [export["assetId"]], assets, f"export/{export.get('id')}.assetId")

    provenance = project.get("provenance", {})
    _require_refs(errors, provenance.get("decisionIds", []), decisions, "provenance.decisionIds")
    _require_refs(errors, provenance.get("eventIds", []), events, "provenance.eventIds")

    return errors


def validate_project(project: dict[str, Any], schema_dir: Path = SCHEMA_DIR) -> None:
    schemas, registry = load_schemas(schema_dir)
    validator = Draft202012Validator(
        schemas[ROOT_SCHEMA_ID],
        registry=registry,
        format_checker=FormatChecker(),
    )
    structural = sorted(validator.iter_errors(project), key=lambda error: list(error.absolute_path))
    if structural:
        messages = [f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in structural]
        raise ContractValidationError("schema validation failed:\n" + "\n".join(messages))

    semantic = semantic_errors(project)
    if semantic:
        raise ContractValidationError("semantic validation failed:\n" + "\n".join(semantic))

    round_trip = json.loads(json.dumps(project, sort_keys=True))
    if round_trip != project:
        raise ContractValidationError("JSON round-trip changed project semantics")


def validate_project_file(path: Path) -> dict[str, Any]:
    project = _read_json(path)
    if not isinstance(project, dict):
        raise ContractValidationError("StudioProject document must be a JSON object")
    validate_project(project)
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=EXAMPLE)
    args = parser.parse_args()
    validate_project_file(args.path)
    print(json.dumps({"valid": True, "path": str(args.path), "schemaVersion": "1.0.0"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
