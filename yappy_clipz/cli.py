"""Agent-friendly YAPPY-CLIPZ command-line adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .actions import ActionContext
from .errors import ActionProblem
from .factory import ApplicationRuntime, create_runtime
from .repository import ProjectNotFound, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict


def _json_file(value: Path) -> dict:
    try: payload = json.loads(value.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise ServiceValidationError(f"JSON file is unreadable: {exc}") from exc
    if not isinstance(payload, dict): raise ServiceValidationError("JSON file must contain an object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yappy-clipz")
    root = parser.add_subparsers(dest="resource", required=True)

    capabilities = root.add_parser("capabilities", help="Discover stable application actions")
    capability_actions = capabilities.add_subparsers(dest="action", required=True)
    capability_list = capability_actions.add_parser("list"); capability_list.add_argument("--lifecycle")
    capability_describe = capability_actions.add_parser("describe"); capability_describe.add_argument("action_id")

    action = root.add_parser("action", help="Invoke any registered action with a JSON input document")
    action_commands = action.add_subparsers(dest="action", required=True)
    action_run = action_commands.add_parser("run")
    action_run.add_argument("action_id"); action_run.add_argument("--input", type=Path, required=True); action_run.add_argument("--tenant")
    action_run.add_argument("--approved", action="store_true"); action_run.add_argument("--idempotency-key"); action_run.add_argument("--correlation-id")
    action_run.add_argument("--causation-id"); action_run.add_argument("--request-id")

    project = root.add_parser("project", help="Manage StudioProject records")
    project_actions = project.add_subparsers(dest="action", required=True)
    create = project_actions.add_parser("create")
    create.add_argument("--tenant", required=True); create.add_argument("--slug", required=True); create.add_argument("--title", required=True)
    create.add_argument("--objective", required=True); create.add_argument("--deliverable", action="append", required=True)
    create.add_argument("--audience", action="append", default=[]); create.add_argument("--constraint", action="append", default=[])
    create.add_argument("--quality-lane",default="premium",choices=("economy", "premium", "sovereign", "owner_private"))
    listing = project_actions.add_parser("list"); listing.add_argument("--tenant", required=True)
    get = project_actions.add_parser("get"); get.add_argument("--tenant", required=True); get.add_argument("project_id")
    validate = project_actions.add_parser("validate"); validate.add_argument("--tenant", required=True); validate.add_argument("project_id")

    timeline = root.add_parser("timeline", help="Read and replace canonical Timeline v1 state")
    timeline_actions = timeline.add_subparsers(dest="action", required=True)
    timeline_get = timeline_actions.add_parser("get"); timeline_get.add_argument("--tenant", required=True); timeline_get.add_argument("project_id")
    timeline_replace = timeline_actions.add_parser("replace"); timeline_replace.add_argument("--tenant", required=True)
    timeline_replace.add_argument("--expected-version", required=True, type=int); timeline_replace.add_argument("--file", required=True, type=Path); timeline_replace.add_argument("project_id")
    return parser


def execute(args: argparse.Namespace, service: StudioService, runtime: ApplicationRuntime | None = None) -> object:
    """Translate parsed CLI input into shared service/dispatcher calls."""
    if args.resource == "capabilities":
        runtime = runtime or create_runtime(service=service)
        return runtime.capabilities.list(lifecycle=args.lifecycle) if args.action == "list" else runtime.capabilities.describe(args.action_id)
    if args.resource == "action" and args.action == "run":
        runtime = runtime or create_runtime(service=service)
        return runtime.dispatcher.dispatch(args.action_id,_json_file(args.input),context=ActionContext(
            tenant_id=args.tenant,approved=args.approved,idempotency_key=args.idempotency_key,correlation_id=args.correlation_id,
            causation_id=args.causation_id,request_id=args.request_id,actor_id="cli"))
    if args.resource == "project":
        if args.action == "create": return service.create_project(tenant_id=args.tenant,slug=args.slug,title=args.title,objective=args.objective,deliverables=args.deliverable,audience=args.audience,constraints=args.constraint,quality_lane=args.quality_lane)
        if args.action == "list": return service.list_projects(tenant_id=args.tenant)
        if args.action == "get": return service.get_project(tenant_id=args.tenant, project_id=args.project_id)
        if args.action == "validate": return service.validate_project(tenant_id=args.tenant, project_id=args.project_id)
    if args.resource == "timeline":
        if args.action == "get": return service.get_timeline(tenant_id=args.tenant, project_id=args.project_id)
        if args.action == "replace": return service.replace_timeline(tenant_id=args.tenant,project_id=args.project_id,expected_version=args.expected_version,timeline=_json_file(args.file))
    raise ServiceValidationError("unsupported command")


def main(argv: Sequence[str] | None = None, service: StudioService | None = None, runtime: ApplicationRuntime | None = None) -> int:
    """Run the CLI and emit one machine-readable JSON document."""
    parser = build_parser(); args = parser.parse_args(list(argv) if argv is not None else None)
    active_runtime = runtime or create_runtime(service=service); active_service = service or active_runtime.service
    try: result = execute(args, active_service, active_runtime)
    except ActionProblem as exc:
        print(json.dumps(exc.document(request_id=getattr(args,"request_id",None) or "req_cli_error",correlation_id=getattr(args,"correlation_id",None) or "corr_cli_error")), file=sys.stderr)
        return 5 if exc.code == "version_conflict" else 2
    except ProjectNotFound as exc:
        print(json.dumps({"error": "not_found", "message": str(exc)}), file=sys.stderr); return 4
    except TimelineVersionConflict as exc:
        print(json.dumps({"error":"version_conflict","message":str(exc),"resource":"timeline","expectedVersion":exc.expected_version,"currentVersion":exc.current_version}),file=sys.stderr); return 5
    except (ServiceValidationError, RepositoryError, ValueError) as exc:
        print(json.dumps({"error": "invalid_request", "message": str(exc)}), file=sys.stderr); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0
