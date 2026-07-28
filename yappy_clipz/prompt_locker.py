"""Versioned, filesystem-backed prompt and workflow registry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z][a-zA-Z0-9_.-]*)\s*}}")


class PromptLockerError(ValueError):
    """Raised when prompt data is unsafe, missing, or invalid."""


class PromptNotFound(PromptLockerError):
    """Raised when a prompt or workflow ID is not registered."""


def _safe_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _scalar_text(value: Any, name: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)) and not isinstance(value, complex):
        return str(value)
    raise PromptLockerError(f"template variable {name!r} must be a string, number, or boolean")


class PromptLocker:
    """Loads checked-in JSON prompt/workflow definitions by stable ID."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.prompt_dir = (self.root / "prompts").resolve()
        self.workflow_dir = (self.root / "workflows").resolve()
        for child in (self.prompt_dir, self.workflow_dir):
            try:
                child.relative_to(self.root)
            except ValueError as exc:
                raise PromptLockerError("prompt locker path escaped configured root") from exc

    @staticmethod
    def _validate_id(value: str, field: str = "id") -> str:
        if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
            raise PromptLockerError(f"{field} must match {ID_PATTERN.pattern!r}")
        return value

    @staticmethod
    def _load_file(path: Path, *, expected_kind: str) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PromptLockerError(f"unreadable prompt locker file: {path.name}") from exc
        if not isinstance(data, dict) or data.get("kind") != expected_kind:
            raise PromptLockerError(f"invalid {expected_kind} definition: {path.name}")
        if data.get("schemaVersion") != "1.0.0":
            raise PromptLockerError(f"unsupported {expected_kind} schema version: {path.name}")
        PromptLocker._validate_id(data.get("id"), f"{expected_kind}.id")
        if not isinstance(data.get("version"), str) or not data["version"]:
            raise PromptLockerError(f"{expected_kind}.version is required")
        return data

    def _index(self, directory: Path, kind: str) -> dict[str, dict[str, Any]]:
        if not directory.is_dir():
            return {}
        indexed: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.rglob("*.json")):
            resolved = path.resolve()
            try:
                resolved.relative_to(directory)
            except ValueError as exc:
                raise PromptLockerError("prompt locker file escaped configured directory") from exc
            definition = self._load_file(resolved, expected_kind=kind)
            item_id = definition["id"]
            if item_id in indexed:
                raise PromptLockerError(f"duplicate {kind} id: {item_id}")
            definition["_path"] = str(resolved.relative_to(self.root))
            indexed[item_id] = definition
        return indexed

    @staticmethod
    def _summary(definition: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": definition["id"],
            "version": definition["version"],
            "title": definition.get("title", definition["id"]),
            "description": definition.get("description", ""),
            "tags": list(definition.get("tags", [])),
            "source": definition.get("source", {}),
        }

    def list_prompts(self) -> list[dict[str, Any]]:
        return [self._summary(item) for item in self._index(self.prompt_dir, "prompt").values()]

    def list_workflows(self) -> list[dict[str, Any]]:
        return [self._summary(item) for item in self._index(self.workflow_dir, "workflow").values()]

    def get_prompt(self, prompt_id: str) -> dict[str, Any]:
        prompt_id = self._validate_id(prompt_id, "prompt_id")
        try:
            result = self._index(self.prompt_dir, "prompt")[prompt_id]
        except KeyError as exc:
            raise PromptNotFound(f"prompt not found: {prompt_id}") from exc
        result.pop("_path", None)
        return _safe_copy(result)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        workflow_id = self._validate_id(workflow_id, "workflow_id")
        try:
            result = self._index(self.workflow_dir, "workflow")[workflow_id]
        except KeyError as exc:
            raise PromptNotFound(f"workflow not found: {workflow_id}") from exc
        result.pop("_path", None)
        return _safe_copy(result)

    @staticmethod
    def _derived_variables(values: dict[str, Any]) -> dict[str, Any]:
        derived = dict(values)
        duration = derived.get("duration")
        try:
            numeric_duration = int(duration)
        except (TypeError, ValueError):
            return derived
        if 4 <= numeric_duration <= 15:
            derived.setdefault("speech_start", "00:01")
            derived.setdefault("speech_end", f"00:{numeric_duration - 2:02d}")
            derived.setdefault("closing_start", f"00:{numeric_duration - 2:02d}")
            derived.setdefault("duration_timestamp", f"00:{numeric_duration:02d}")
            derived.setdefault("max_dialogue_words", max(1, round((numeric_duration - 3) * 2.5)))
        return derived

    @staticmethod
    def _render(template: str, values: dict[str, Any]) -> str:
        if not isinstance(template, str):
            raise PromptLockerError("prompt template must be a string")

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in values:
                raise PromptLockerError(f"missing template variable: {name}")
            return _scalar_text(values[name], name)

        rendered = PLACEHOLDER_PATTERN.sub(replace, template)
        unresolved = PLACEHOLDER_PATTERN.findall(rendered)
        if unresolved:
            raise PromptLockerError(f"unresolved template variables: {sorted(set(unresolved))}")
        return rendered.strip()

    def compile_prompt(self, prompt_id: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        definition = self.get_prompt(prompt_id)
        supplied = variables or {}
        if not isinstance(supplied, dict):
            raise PromptLockerError("variables must be an object")
        values = dict(definition.get("defaults", {}))
        values.update(_safe_copy(supplied))
        values = self._derived_variables(values)
        required = definition.get("requiredVariables", [])
        missing = [name for name in required if name not in values or values[name] in (None, "")]
        if missing:
            raise PromptLockerError(f"missing required variables: {', '.join(missing)}")
        return {
            "promptId": definition["id"],
            "promptVersion": definition["version"],
            "text": self._render(definition["template"], values),
            "variables": values,
            "providerHints": _safe_copy(definition.get("providerHints", {})),
            "safety": _safe_copy(definition.get("safety", {})),
            "source": _safe_copy(definition.get("source", {})),
        }

    def compile_workflow(self, workflow_id: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        workflow = self.get_workflow(workflow_id)
        supplied = variables or {}
        if not isinstance(supplied, dict):
            raise PromptLockerError("variables must be an object")
        common = dict(workflow.get("defaults", {}))
        common.update(_safe_copy(supplied))
        required = workflow.get("requiredVariables", [])
        missing = [name for name in required if name not in common or common[name] in (None, "")]
        if missing:
            raise PromptLockerError(f"missing required workflow variables: {', '.join(missing)}")
        compiled_steps: list[dict[str, Any]] = []
        for position, step in enumerate(workflow.get("steps", []), start=1):
            if not isinstance(step, dict) or not step.get("promptId"):
                raise PromptLockerError(f"workflow step {position} is invalid")
            step_variables = dict(common)
            step_variables.update(_safe_copy(step.get("variables", {})))
            compiled = self.compile_prompt(step["promptId"], step_variables)
            provider_input = dict(step.get("providerInput", {}))
            provider_input["prompt"] = compiled["text"]
            for key, value in list(provider_input.items()):
                if not isinstance(value, str) or not PLACEHOLDER_PATTERN.search(value):
                    continue
                exact = PLACEHOLDER_PATTERN.fullmatch(value.strip())
                derived = self._derived_variables(step_variables)
                if exact:
                    variable_name = exact.group(1)
                    if variable_name not in derived:
                        raise PromptLockerError(f"missing template variable: {variable_name}")
                    provider_input[key] = _safe_copy(derived[variable_name])
                else:
                    provider_input[key] = self._render(value, derived)
            compiled_steps.append(
                {
                    "stepId": step.get("id", f"step-{position}"),
                    "title": step.get("title", compiled["promptId"]),
                    "prompt": compiled,
                    "providerId": step.get("providerId", workflow.get("providerId")),
                    "modelId": step.get("modelId", workflow.get("modelId")),
                    "providerInput": provider_input,
                    "requiresApproval": bool(step.get("requiresApproval", True)),
                }
            )
        return {
            "workflowId": workflow["id"],
            "workflowVersion": workflow["version"],
            "title": workflow.get("title", workflow["id"]),
            "steps": compiled_steps,
            "variables": self._derived_variables(common),
            "executionPolicy": _safe_copy(workflow.get("executionPolicy", {})),
            "source": _safe_copy(workflow.get("source", {})),
        }
