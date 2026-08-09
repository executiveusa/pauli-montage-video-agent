"""Contract tests for the PopeBot + Composio upgrade authority chain."""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/render_upgrade_progress.py"
SPEC = importlib.util.spec_from_file_location("render_upgrade_progress", SCRIPT)
progress = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(progress)
ACTIVE_SCRIPT = ROOT / "scripts/validate_active_openspecs.py"
ACTIVE_SPEC = importlib.util.spec_from_file_location("validate_active_openspecs", ACTIVE_SCRIPT)
active_specs = importlib.util.module_from_spec(ACTIVE_SPEC)
assert ACTIVE_SPEC.loader
ACTIVE_SPEC.loader.exec_module(active_specs)


class UpgradeGovernanceTests(unittest.TestCase):
    def test_roadmap_has_exact_unique_immutable_slices(self):
        roadmap = progress.load_json(ROOT / "ops/upgrade/roadmap.json")
        progress.validate_roadmap(roadmap)
        self.assertEqual([task["order"] for task in roadmap["tasks"]], list(range(15)))
        self.assertEqual(roadmap["authority"]["taskSource"], "ops/upgrade/roadmap.json")

    def test_roadmap_redefinition_is_rejected(self):
        original = progress.ROADMAP
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                changed = Path(directory) / "roadmap.json"
                changed.write_text(original.read_text(encoding="utf-8").replace("Architecture and delivery contract", "Renamed authority"), encoding="utf-8")
                progress.ROADMAP = changed
                with self.assertRaisesRegex(ValueError, "canonical|bootstrap"):
                    progress.validate_roadmap(progress.load_json(changed))
        finally:
            progress.ROADMAP = original

    def test_all_completion_evidence_is_strict_and_canonical(self):
        roadmap = progress.load_json(ROOT / "ops/upgrade/roadmap.json")
        task_ids = {task["id"] for task in roadmap["tasks"]}
        evidence_files = sorted((ROOT / "ops/upgrade/evidence").glob("*.json"))
        self.assertTrue(evidence_files)
        for path in evidence_files:
            evidence = progress.load_json(path)
            progress.validate_evidence(evidence, task_ids)

    def test_declared_json_schema_accepts_all_evidence(self):
        try:
            from jsonschema import Draft202012Validator
        except ModuleNotFoundError:
            self.skipTest("jsonschema is installed by requirements-studio.txt")
        schema = progress.load_json(ROOT / "ops/upgrade/schemas/slice-evidence.schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for path in sorted((ROOT / "ops/upgrade/evidence").glob("*.json")):
            validator.validate(progress.load_json(path))

    def test_false_completion_claim_is_rejected(self):
        roadmap = progress.load_json(ROOT / "ops/upgrade/roadmap.json")
        task_ids = {task["id"] for task in roadmap["tasks"]}
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["postMerge"]["passed"] = False
        with self.assertRaisesRegex(ValueError, "post-merge evidence"):
            progress.validate_evidence(evidence, task_ids)

    def test_fabricated_git_evidence_is_rejected(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["merge"]["treeSha"] = "0" * 40
        with mock.patch.object(progress, "git", side_effect=["", evidence["merge"]["sha"], "f" * 40]):
            with self.assertRaisesRegex(ValueError, "merge tree"):
                progress.validate_git_evidence(evidence)

    def test_pull_request_number_is_bound_to_merge_subject(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["pullRequest"]["number"] = 999
        with mock.patch.object(
            progress,
            "git",
            side_effect=[
                "",
                evidence["merge"]["sha"],
                evidence["merge"]["treeSha"],
                evidence["rollback"]["baselineSha"],
                "phase(upgrade-00): prevent completed GRINIONS replay (#35)",
            ],
        ):
            with self.assertRaisesRegex(ValueError, "merge subject"):
                progress.validate_git_evidence(evidence)

    @unittest.skipUnless(os.environ.get("YAPPY_VERIFY_CANONICAL_REMOTE") == "1", "live canonical remote verification runs in the GRINIONS gate")
    def test_pull_request_head_is_bound_to_canonical_remote(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["pullRequest"]["headSha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "pull-request head"):
            progress.validate_git_evidence(evidence)

    def test_github_api_binds_merge_identity_and_required_check(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        pull = {
            "state": "closed",
            "merged_at": "2026-08-09T22:25:00Z",
            "base": {"ref": "main"},
            "head": {"sha": evidence["pullRequest"]["headSha"]},
            "merge_commit_sha": evidence["merge"]["sha"],
            "body": f"<!-- grinions-work-identity: {json.dumps(evidence['identity'], separators=(',', ':'))} -->",
        }
        run = {
            "name": "GRINIONS phase gates",
            "event": "pull_request",
            "head_sha": evidence["pullRequest"]["headSha"],
            "run_attempt": 2,
            "run_started_at": "2026-08-09T23:20:00Z",
            "status": "completed",
            "conclusion": "success",
        }
        with mock.patch.object(progress, "github_json", side_effect=[pull, run]):
            progress.validate_github_evidence(evidence)
        bad_run = {**run, "conclusion": "failure"}
        with mock.patch.object(progress, "github_json", side_effect=[pull, bad_run]):
            with self.assertRaisesRegex(ValueError, "post-merge check"):
                progress.validate_github_evidence(evidence)

        premerge_run = {**run, "run_attempt": 1, "run_started_at": "2026-08-09T22:20:00Z"}
        with mock.patch.object(progress, "github_json", side_effect=[pull, premerge_run]):
            with self.assertRaisesRegex(ValueError, "post-merge check"):
                progress.validate_github_evidence(evidence)

    def test_postmerge_command_labels_cannot_claim_success(self):
        roadmap = progress.load_json(ROOT / "ops/upgrade/roadmap.json")
        task_ids = {task["id"] for task in roadmap["tasks"]}
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["postMerge"]["treeChecks"][0]["command"] = "echo fabricated success"
        with self.assertRaisesRegex(ValueError, "check binding"):
            progress.validate_evidence(evidence, task_ids)

    def test_coordinated_roadmap_hash_tamper_is_rejected_against_origin_main(self):
        original_path, original_hash = progress.ROADMAP, progress.ROADMAP_SHA256
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                changed = Path(directory) / "roadmap.json"
                changed.write_text(original_path.read_text(encoding="utf-8").replace("Architecture and delivery contract", "Coordinated tamper"), encoding="utf-8")
                progress.ROADMAP = changed
                progress.ROADMAP_SHA256 = __import__("hashlib").sha256(changed.read_bytes()).hexdigest()
                baseline_result = progress.subprocess.CompletedProcess([], 0, stdout=original_path.read_bytes(), stderr=b"")
                with mock.patch.object(progress.subprocess, "run", return_value=baseline_result):
                    with self.assertRaisesRegex(ValueError, "canonical"):
                        progress.validate_roadmap(progress.load_json(changed))
        finally:
            progress.ROADMAP, progress.ROADMAP_SHA256 = original_path, original_hash

    def test_evidence_cannot_be_relabelled_to_another_slice(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        evidence["sliceId"] = "upgrade-14-production-pilot"
        with self.assertRaisesRegex(ValueError, "merge subject|git evidence check"):
            progress.validate_git_evidence(evidence)

    def test_completion_bindings_are_globally_unique(self):
        evidence = progress.load_json(ROOT / "ops/upgrade/evidence/upgrade-00-grinions-replay-guard.json")
        duplicate = json.loads(json.dumps(evidence))
        duplicate["sliceId"] = "upgrade-01-architecture-contract"
        with self.assertRaisesRegex(ValueError, "duplicate completion binding"):
            progress.validate_unique_evidence([evidence, duplicate])

    def test_generated_progress_is_current(self):
        expected = progress.render(verify_remote=False)
        self.assertEqual((ROOT / "docs/YAPPY-UPGRADE-PROGRESS.md").read_text(encoding="utf-8"), expected)
        self.assertIn("Completed: **1/15**", expected)

    def test_unlicensed_sources_are_excluded_from_copying(self):
        register = (ROOT / "docs/SOURCE-LICENSE-REGISTER.md").read_text(encoding="utf-8")
        for source in ("Bomx/super-video-maker-skill", "ytx-readings/design-ui-ux"):
            row = next(line for line in register.splitlines() if source in line)
            self.assertIn("REJECT COPY", row)

    def test_execution_toolchain_is_pinned(self):
        toolchain = progress.load_json(ROOT / "ops/upgrade/toolchain.json")
        tools = {item["name"]: item for item in toolchain["tools"]}
        self.assertEqual(tools["Ralphy"]["version"], "4.7.2")
        self.assertIn("506eea0e7d72c8eeb96dd2f697363bef396add34", tools["Ralphy"]["source"])
        self.assertEqual(tools["OpenSpec"]["version"], "1.3.1")

    def test_active_openspec_names_reject_options(self):
        original = active_specs.CHANGES
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                changes = Path(directory)
                (changes / "--help").mkdir()
                active_specs.CHANGES = changes
                with self.assertRaisesRegex(ValueError, "option-like"):
                    active_specs.active_changes()
        finally:
            active_specs.CHANGES = original

    def test_active_openspec_uses_exact_pinned_executable(self):
        original = active_specs.CHANGES
        try:
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                changes = Path(directory)
                (changes / "upgrade-test").mkdir()
                active_specs.CHANGES = changes
                responses = [
                    subprocess.CompletedProcess([], 0, stdout="1.3.1\n", stderr=""),
                    subprocess.CompletedProcess([], 0, stdout="", stderr=""),
                ]
                with mock.patch.object(active_specs.shutil, "which", return_value="/trusted/bin/openspec"), mock.patch.object(active_specs.subprocess, "run", side_effect=responses) as invoked:
                    self.assertEqual(active_specs.main(), 0)
                self.assertEqual(invoked.call_args_list[0].args[0], ["/trusted/bin/openspec", "--version"])
                self.assertEqual(invoked.call_args_list[1].args[0][:3], ["/trusted/bin/openspec", "validate", "upgrade-test"])
        finally:
            active_specs.CHANGES = original

    def test_global_ralphy_commands_are_slice_neutral(self):
        config = (ROOT / ".ralphy/config.yaml").read_text(encoding="utf-8")
        for unsupported in ("base_branch:", "execution:", "capabilities:"):
            self.assertNotIn(unsupported, config)
        self.assertIn("validate_active_openspecs.py", config)
        self.assertNotIn("upgrade-01-architecture-contract --strict", config)

    def test_context_documents_disclaim_upgrade_authority(self):
        for relative in (
            "docs/ARCHITECTURE.md",
            "docs/CURRENT-STATE.md",
            "docs/YAPPY-CLIPZ-MASTER-PLAN.md",
            "docs/YAPPY-CLIPZ-VOICE-CLOUD-STUDIO-PRD.md",
        ):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertRegex(content, r"(?i)not (?:a |execution or )?(?:live )?(?:completion|execution).*authority|not execution or completion authority|inventory only")


if __name__ == "__main__":
    unittest.main()
