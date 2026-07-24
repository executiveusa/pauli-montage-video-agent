#!/usr/bin/env python3
"""Create the canonical YAPPY-CLIPZ ICM workspace without path traversal."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

STAGES = (
    "00_intake",
    "01_second_brain_ingest",
    "02_canon_bibles",
    "03_scene_blueprint",
    "04_prompt_compile",
    "05_voice_music",
    "06_animation",
    "07_render",
    "08_edit_localize",
    "09_publish_bridge",
    "10_qa_archive",
)

SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "stage"


class WorkspaceError(ValueError):
    """Raised when an ICM workspace request is unsafe or invalid."""


def validate_slug(value: str, field: str) -> str:
    if not isinstance(value, str) or not SAFE_SLUG.fullmatch(value):
        raise WorkspaceError(
            f"{field} must match {SAFE_SLUG.pattern!r}; path separators, '..', and absolute paths are forbidden"
        )
    return value


def _resolved_under(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceError(f"workspace escaped requested root: {resolved_candidate}") from exc
    return resolved_candidate


def initialize_workspace(root: Path, tenant: str, project: str) -> Path:
    tenant = validate_slug(tenant, "tenant")
    project = validate_slug(project, "project")
    root = root.expanduser().resolve()
    workspace = _resolved_under(root, root / "tenants" / tenant / project)
    workspace.mkdir(parents=True, exist_ok=True)

    context_template = TEMPLATE_DIR / "CONTEXT.md"
    checklist_template = TEMPLATE_DIR / "CHECKLIST.md"
    handoff_template = TEMPLATE_DIR / "handoff.json"
    for required in (context_template, checklist_template, handoff_template):
        if not required.is_file():
            raise WorkspaceError(f"missing ICM template: {required}")

    handoff_base = json.loads(handoff_template.read_text(encoding="utf-8"))

    for stage in STAGES:
        stage_dir = _resolved_under(root, workspace / stage)
        stage_dir.mkdir(parents=True, exist_ok=True)
        (stage_dir / "input").mkdir(exist_ok=True)
        (stage_dir / "output").mkdir(exist_ok=True)
        shutil.copyfile(context_template, stage_dir / "CONTEXT.md")
        shutil.copyfile(checklist_template, stage_dir / "CHECKLIST.md")
        handoff = dict(handoff_base)
        handoff["stage"] = stage
        (stage_dir / "handoff.json").write_text(
            json.dumps(handoff, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "schemaVersion": 1,
        "tenant": tenant,
        "project": project,
        "stages": list(STAGES),
    }
    (workspace / "workspace.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return workspace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    workspace = initialize_workspace(args.root, args.tenant, args.project)
    print(json.dumps({"workspace": str(workspace), "stages": len(STAGES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
