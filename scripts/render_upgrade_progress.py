#!/usr/bin/env python3
"""Render the upgrade progress page from immutable roadmap and evidence files."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ops/upgrade/roadmap.json"
EVIDENCE_DIR = ROOT / "ops/upgrade/evidence"
OUTPUT = ROOT / "docs/YAPPY-UPGRADE-PROGRESS.md"
SHA = re.compile(r"^[0-9a-f]{40}$")
ROADMAP_SHA256 = "ba75fca6928bdee8221d6bd9278801aebf5cbf17c2d4f02e83fd937bc27a49f1"
EVIDENCE_SCHEMA = ROOT / "ops/upgrade/schemas/slice-evidence.schema.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_roadmap(roadmap: dict) -> None:
    baseline = subprocess.run(
        ["git", "show", "refs/remotes/origin/main:ops/upgrade/roadmap.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    current = ROADMAP.read_bytes()
    if baseline.returncode == 0:
        if baseline.stdout != current:
            raise ValueError("roadmap differs from the canonical origin/main contract")
    elif baseline.returncode == 128:
        if hashlib.sha256(current).hexdigest() != ROADMAP_SHA256:
            raise ValueError("roadmap differs from the accepted immutable bootstrap contract")
    else:
        raise ValueError("canonical roadmap baseline is unavailable")
    if roadmap.get("schemaVersion") != 1:
        raise ValueError("roadmap schemaVersion must be 1")
    tasks = roadmap.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 15:
        raise ValueError("roadmap must contain exactly 15 tasks")
    orders = [task.get("order") for task in tasks]
    ids = [task.get("id") for task in tasks]
    titles = [task.get("title") for task in tasks]
    if orders != list(range(15)):
        raise ValueError("roadmap task order must be exactly 0 through 14")
    if len(set(ids)) != 15 or len(set(titles)) != 15:
        raise ValueError("roadmap task IDs and titles must be unique")
    for order, task in enumerate(tasks):
        if not re.fullmatch(rf"upgrade-{order:02d}-[a-z0-9-]+", task.get("id", "")):
            raise ValueError(f"task {order} has an invalid immutable ID")
        if not task.get("acceptance", "").strip():
            raise ValueError(f"task {order} has no acceptance contract")


def validate_evidence(evidence: dict, task_ids: set[str]) -> None:
    required = {"schemaVersion", "initiativeId", "sliceId", "identity", "status", "pullRequest", "judgment", "merge", "postMerge", "rollback"}
    if set(evidence) != required:
        raise ValueError(f"evidence fields differ from schema: {evidence.get('sliceId')}")
    if evidence["schemaVersion"] != 1 or evidence["initiativeId"] != "yappy-upgrade":
        raise ValueError("evidence identity is invalid")
    if evidence["sliceId"] not in task_ids or evidence["status"] != "completed":
        raise ValueError("evidence references an unknown or incomplete slice")
    if evidence["identity"] != {"repository": "executiveusa/pauli-montage-video-agent", "initiativeId": evidence["initiativeId"], "openspecId": evidence["sliceId"]}:
        raise ValueError("evidence immutable work identity is invalid")
    pr = evidence["pullRequest"]
    if set(pr) != {"number", "url", "headSha"} or not isinstance(pr.get("number"), int) or not re.fullmatch(rf"https://github\.com/executiveusa/pauli-montage-video-agent/pull/{pr.get('number')}", pr.get("url", "")) or not SHA.fullmatch(pr.get("headSha", "")):
        raise ValueError("pull request evidence is invalid")
    if evidence["judgment"] != {"verdict": "OURS WINS", "unresolvedReviewThreads": 0}:
        raise ValueError("independent judgment evidence is incomplete")
    if set(evidence["merge"]) != {"sha", "treeSha"} or not all(SHA.fullmatch(evidence["merge"].get(key, "")) for key in ("sha", "treeSha")):
        raise ValueError("merge evidence is invalid")
    post_merge = evidence["postMerge"]
    if set(post_merge) != {"passed", "mainSha", "treeChecks"} or post_merge.get("passed") is not True or not SHA.fullmatch(post_merge.get("mainSha", "")) or post_merge["mainSha"] != evidence["merge"]["sha"]:
        raise ValueError("post-merge evidence is invalid")
    expected_commands = {
        "cumulative-tests": "npm test --prefix ops/grinions",
        "structure": "npm run verify --prefix ops/grinions",
        "openspec": f"openspec validate {evidence['sliceId']} --strict --no-interactive",
    }
    checks = post_merge.get("treeChecks")
    if not isinstance(checks, list) or len(checks) != 3 or {check.get("name") for check in checks if isinstance(check, dict)} != set(expected_commands):
        raise ValueError("post-merge checks are incomplete")
    for check in checks:
        if set(check) != {"name", "command", "status", "subjectSha", "evidenceUrl"} or check["command"] != expected_commands[check["name"]] or check["status"] != "passed" or check["subjectSha"] != evidence["pullRequest"]["headSha"] or not re.fullmatch(r"https://github\.com/executiveusa/pauli-montage-video-agent/actions/runs/[0-9]+", check["evidenceUrl"]):
            raise ValueError("post-merge check binding is invalid")
    if set(evidence["rollback"]) != {"baselineSha", "strategy"} or not SHA.fullmatch(evidence["rollback"].get("baselineSha", "")) or not evidence["rollback"].get("strategy", "").strip():
        raise ValueError("rollback evidence is invalid")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"git evidence check failed: {' '.join(args)}")
    return result.stdout.strip()


def validate_git_evidence(evidence: dict) -> None:
    merge_sha = evidence["merge"]["sha"]
    baseline_sha = evidence["rollback"]["baselineSha"]
    if git("rev-parse", "--verify", f"{merge_sha}^{{commit}}") != merge_sha:
        raise ValueError("merge commit cannot be resolved exactly")
    if git("rev-parse", f"{merge_sha}^{{tree}}") != evidence["merge"]["treeSha"]:
        raise ValueError("recorded merge tree does not match Git")
    if git("rev-parse", f"{merge_sha}^") != baseline_sha:
        raise ValueError("rollback baseline is not the merge parent")
    subject = git("show", "-s", "--format=%s", merge_sha)
    slice_token = evidence["sliceId"].split("-", 2)[:2]
    if f"({'-'.join(slice_token)})" not in subject or not subject.endswith(f"(#{evidence['pullRequest']['number']})"):
        raise ValueError("merge subject does not bind the Slice and pull request")
    origin_main = git("rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
    remote = git(
        "ls-remote",
        "origin",
        "refs/heads/main",
        f"refs/pull/{evidence['pullRequest']['number']}/head",
    )
    remote_refs = {ref: sha for sha, ref in (line.split("\t", 1) for line in remote.splitlines())}
    if remote_refs.get("refs/heads/main") != origin_main:
        raise ValueError("origin/main is not fresh against the canonical remote")
    if remote_refs.get(f"refs/pull/{evidence['pullRequest']['number']}/head") != evidence["pullRequest"]["headSha"]:
        raise ValueError("canonical pull-request head does not match evidence")
    git("fetch", "--no-tags", "origin", evidence["pullRequest"]["headSha"])
    if git("rev-parse", f"{evidence['pullRequest']['headSha']}^{{tree}}") != evidence["merge"]["treeSha"]:
        raise ValueError("verified pull-request head tree differs from merged tree")
    git("merge-base", "--is-ancestor", merge_sha, origin_main)
    spec_path = f"openspec/changes/{evidence['sliceId']}/proposal.md"
    git("cat-file", "-e", f"{merge_sha}:{spec_path}")
    baseline_probe = subprocess.run(
        ["git", "cat-file", "-e", f"{baseline_sha}:{spec_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if baseline_probe.returncode == 0:
        raise ValueError("slice OpenSpec already existed at the rollback baseline")
    if baseline_probe.returncode != 128:
        raise ValueError("slice OpenSpec baseline binding is unavailable")


@lru_cache(maxsize=128)
def github_json(url: str) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "yappy-upgrade-evidence/1"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception as error:
        raise ValueError(f"canonical GitHub evidence unavailable: {url}") from error


def validate_github_evidence(evidence: dict) -> None:
    number = evidence["pullRequest"]["number"]
    pull = github_json(f"https://api.github.com/repos/executiveusa/pauli-montage-video-agent/pulls/{number}")
    identity_marker = f"<!-- grinions-work-identity: {json.dumps(evidence['identity'], separators=(',', ':'))} -->"
    if pull.get("state") != "closed" or not pull.get("merged_at") or pull.get("base", {}).get("ref") != "main":
        raise ValueError("canonical GitHub pull request is not merged to main")
    if pull.get("head", {}).get("sha") != evidence["pullRequest"]["headSha"] or pull.get("merge_commit_sha") != evidence["merge"]["sha"]:
        raise ValueError("canonical GitHub pull-request identity does not match evidence")
    if identity_marker not in (pull.get("body") or ""):
        raise ValueError("canonical GitHub pull request lacks the immutable identity marker")

    run_urls = {check["evidenceUrl"] for check in evidence["postMerge"]["treeChecks"]}
    for run_url in run_urls:
        run_id = run_url.rsplit("/", 1)[-1]
        run = github_json(f"https://api.github.com/repos/executiveusa/pauli-montage-video-agent/actions/runs/{run_id}")
        if run.get("name") != "GRINIONS phase gates" or run.get("event") != "pull_request" or run.get("head_sha") != evidence["pullRequest"]["headSha"] or run.get("run_attempt", 0) < 2 or run.get("run_started_at", "") <= pull.get("merged_at", "") or run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError("canonical GitHub post-merge check evidence is invalid")


def validate_unique_evidence(records: list[dict]) -> None:
    for field_path in (("pullRequest", "number"), ("pullRequest", "headSha"), ("merge", "sha")):
        values = [record[field_path[0]][field_path[1]] for record in records]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate completion binding: {'.'.join(field_path)}")


def render(*, verify_remote: bool = True) -> str:
    roadmap = load_json(ROADMAP)
    validate_roadmap(roadmap)
    task_ids = {task["id"] for task in roadmap["tasks"]}
    evidence_by_id: dict[str, dict] = {}
    for path in sorted(EVIDENCE_DIR.glob("*.json")):
        evidence = load_json(path)
        try:
            from jsonschema import Draft202012Validator
        except ModuleNotFoundError as error:
            raise RuntimeError("jsonschema from requirements-studio.txt is required to render canonical progress") from error
        schema = load_json(EVIDENCE_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(evidence)
        validate_evidence(evidence, task_ids)
        if verify_remote:
            validate_git_evidence(evidence)
            validate_github_evidence(evidence)
        slice_id = evidence["sliceId"]
        if slice_id in evidence_by_id:
            raise ValueError(f"duplicate evidence for {slice_id}")
        evidence_by_id[slice_id] = evidence
    validate_unique_evidence(list(evidence_by_id.values()))

    completed = len(evidence_by_id)
    lines = [
        "# YAPPY PopeBot + Composio upgrade progress",
        "",
        "> Generated by `scripts/render_upgrade_progress.py` from `ops/upgrade/roadmap.json` and canonical evidence. Do not edit by hand.",
        "",
        f"Completed: **{completed}/15**",
        "",
        "| Slice | Immutable OpenSpec ID | Outcome | Status | Canonical evidence |",
        "|---:|---|---|---|---|",
    ]
    for task in roadmap["tasks"]:
        evidence = evidence_by_id.get(task["id"])
        if evidence:
            status = "completed"
            proof = f"[PR #{evidence['pullRequest']['number']}]({evidence['pullRequest']['url']}) · merge `{evidence['merge']['sha'][:12]}`"
        else:
            status = "pending"
            proof = "—"
        lines.append(f"| {task['order']} | `{task['id']}` | {task['title']} | {status} | {proof} |")
    lines.extend(["", "Completion is claimed only by a schema-valid evidence record backed by canonical GitHub merge and post-merge verification.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the generated page is stale")
    args = parser.parse_args()
    rendered = render(verify_remote=True)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"stale generated progress: {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
