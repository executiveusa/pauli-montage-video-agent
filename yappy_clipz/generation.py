"""Provider-neutral generation planning, submission, reconciliation, and provenance."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from .costing import BudgetedOperationsService
from .prompt_locker import PromptLocker
from .providers import ProviderCatalog
from .providers.fal_extended import ExtendedFalProviderAdapter
from .repository import ProjectRepository
from .router import OmniRouter


class GenerationError(RuntimeError):
    pass


class GenerationApprovalRequired(GenerationError):
    pass


class GenerationExecutionUnavailable(GenerationError):
    pass


class GenerationResultInvalid(GenerationError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


class GenerationService:
    def __init__(
        self,
        *,
        repository: ProjectRepository,
        catalog: ProviderCatalog,
        router: OmniRouter,
        operations: BudgetedOperationsService,
        prompts: PromptLocker,
        fal: ExtendedFalProviderAdapter,
    ) -> None:
        self.repository = repository
        self.catalog = catalog
        self.router = router
        self.operations = operations
        self.prompts = prompts
        self.fal = fal

    @staticmethod
    def _route_capability(capability: str) -> str:
        return {"image.variation": "image.edit", "video.regenerate": "video.edit"}.get(capability, capability)

    def prepare(
        self,
        *,
        tenant_id: str,
        project_id: str,
        capability: str,
        provider_input: dict[str, Any],
        model_id: str | None = None,
        quality_lane: str = "economy",
        privacy_lane: str = "cloud",
        max_cost: float | None = None,
        preferred_provider: str | None = "fal",
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        self.repository.get(tenant_id, project_id)
        if not isinstance(provider_input, dict):
            raise GenerationError("providerInput must be an object")
        routing_capability = self._route_capability(capability)
        if model_id:
            model = self.catalog.get_model(preferred_provider or "fal", model_id)
            if routing_capability not in model.get("capabilities", []):
                raise GenerationError("selected model does not support requested capability")
            preliminary = self.router.estimate_model(model, provider_input)
            eligible = privacy_lane not in {"sovereign", "owner_private"}
            if max_cost is not None and preliminary.get("amount") is not None:
                eligible = eligible and float(preliminary["amount"]) <= float(max_cost)
            chosen = {
                "routeId": f"route_{preferred_provider or 'fal'}_{model_id.replace('/', '_')}",
                "providerId": preferred_provider or "fal",
                "modelId": model_id,
                "capability": routing_capability,
                "score": 100.0,
                "estimate": preliminary,
                "reasons": ["explicit_model"],
                "eligible": eligible,
            }
            route = {
                "planId": f"rplan_{uuid4().hex[:24]}",
                "capability": routing_capability,
                "qualityLane": quality_lane,
                "privacyLane": privacy_lane,
                "maxCost": max_cost,
                "chosen": chosen if eligible else None,
                "candidates": [chosen],
                "requiresApproval": True,
            }
        else:
            route = self.router.plan(
                capability=routing_capability,
                payload=provider_input,
                quality_lane=quality_lane,
                max_cost=max_cost,
                preferred_provider=preferred_provider,
                privacy_lane=privacy_lane,
            )
        chosen = route.get("chosen")
        if not chosen:
            raise GenerationExecutionUnavailable("no eligible provider route")
        if chosen["providerId"] != "fal":
            raise GenerationExecutionUnavailable("selected provider adapter is not installed")
        provider_plan = self.fal.plan(
            model_id=chosen["modelId"], input_payload=provider_input, webhook_url=webhook_url
        )
        estimate = chosen.get("estimate") or provider_plan.get("estimatedCost")
        if estimate and estimate.get("amount") is None:
            estimate = provider_plan.get("estimatedCost") or estimate
        amount = (estimate or {}).get("amount")
        if max_cost is not None:
            if amount is None:
                raise GenerationExecutionUnavailable("hard cost ceiling requires a known final provider estimate")
            if float(amount) > float(max_cost):
                raise GenerationExecutionUnavailable("final provider estimate exceeds cost ceiling")
        chosen["estimate"] = estimate
        return {
            "generationPlanId": f"gplan_{uuid4().hex[:24]}",
            "tenantId": tenant_id,
            "projectId": project_id,
            "capability": capability,
            "routingCapability": routing_capability,
            "route": route,
            "providerPlan": provider_plan,
            "estimatedCost": estimate,
            "qualityLane": quality_lane,
            "privacyLane": privacy_lane,
            "maxCost": max_cost,
            "approvalRequired": True,
            "preparedAt": _now(),
        }

    def plan_workflow(
        self,
        *,
        tenant_id: str,
        project_id: str,
        workflow_id: str,
        variables: dict[str, Any],
        max_cost: float | None = None,
        quality_lane: str = "economy",
        privacy_lane: str = "cloud",
    ) -> dict[str, Any]:
        compiled = self.prompts.compile_workflow(workflow_id, variables)
        steps: list[dict[str, Any]] = []
        total = 0.0
        unknown = False
        for step in compiled["steps"]:
            model = self.catalog.get_model(step.get("providerId") or "fal", step["modelId"])
            media_capability = next(
                (
                    item
                    for item in model.get("capabilities", [])
                    if item.startswith("video.") or item.startswith("image.")
                ),
                None,
            )
            if not media_capability:
                raise GenerationError("workflow step has no executable media capability")
            plan = self.prepare(
                tenant_id=tenant_id,
                project_id=project_id,
                capability=media_capability,
                provider_input=step["providerInput"],
                model_id=step["modelId"],
                quality_lane=quality_lane,
                privacy_lane=privacy_lane,
                max_cost=max_cost,
                preferred_provider=step.get("providerId") or "fal",
            )
            amount = (plan.get("estimatedCost") or {}).get("amount")
            if amount is None:
                unknown = True
            else:
                total += float(amount)
            steps.append({"stepId": step["stepId"], "title": step["title"], "plan": plan})
        if max_cost is not None and (unknown or total > float(max_cost)):
            raise GenerationExecutionUnavailable("compiled workflow exceeds or cannot prove the cost ceiling")
        return {
            "workflowId": compiled["workflowId"],
            "workflowVersion": compiled["workflowVersion"],
            "title": compiled["title"],
            "steps": steps,
            "estimatedCost": {"amount": None if unknown else round(total, 6), "currency": "USD"},
            "executionPolicy": compiled["executionPolicy"],
            "approvalRequired": True,
        }

    def submit(
        self,
        *,
        tenant_id: str,
        project_id: str,
        capability: str,
        provider_input: dict[str, Any],
        actor_id: str,
        approved: bool,
        idempotency_key: str,
        model_id: str | None = None,
        quality_lane: str = "economy",
        privacy_lane: str = "cloud",
        max_cost: float | None = None,
        budget_limit: float | None = None,
        input_refs: list[str] | None = None,
        correlation_id: str | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        if not approved:
            raise GenerationApprovalRequired("explicit human approval is required")
        if not self.fal.configured() or not self.fal.settings.execution_enabled:
            raise GenerationExecutionUnavailable(
                "provider execution is not configured and enabled server-side"
            )
        plan = self.prepare(
            tenant_id=tenant_id,
            project_id=project_id,
            capability=capability,
            provider_input=provider_input,
            model_id=model_id,
            quality_lane=quality_lane,
            privacy_lane=privacy_lane,
            max_cost=max_cost,
            webhook_url=webhook_url,
        )
        amount = (plan.get("estimatedCost") or {}).get("amount")
        if amount is None:
            raise GenerationExecutionUnavailable("paid execution requires a known cost estimate")
        chosen = plan["route"]["chosen"]
        job = self.operations.create_job(
            tenant_id=tenant_id,
            project_id=project_id,
            job_type="generation",
            capability=capability,
            input_refs=input_refs or [],
            provider_route_id=chosen["routeId"],
            estimated_cost=float(amount),
            currency=(plan.get("estimatedCost") or {}).get("currency", "USD"),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            icm_stage="06_animation",
        )
        existing_request = (job.get("extensions") or {}).get("providerRequestId")
        if existing_request:
            return {"job": job, "approval": None, "plan": plan, "duplicate": True}
        approval = self.operations.request_approval(
            tenant_id=tenant_id,
            project_id=project_id,
            scope_type="generation",
            subject_id=plan["generationPlanId"],
            requested_by=actor_id,
            note="Explicit generation submission approval",
            evidence=[{"kind": "generation_plan", "id": plan["generationPlanId"]}],
        )
        approval = self.operations.decide_approval(
            tenant_id, approval["id"], "approved", actor_id
        )
        reservation = self.operations.reserve_cost(
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job["id"],
            amount=float(amount),
            currency=(plan.get("estimatedCost") or {}).get("currency", "USD"),
            budget_limit=budget_limit,
        )
        try:
            submitted = self.fal.submit(
                model_id=chosen["modelId"],
                input_payload=provider_input,
                approved=True,
                idempotency_key=idempotency_key,
                webhook_url=webhook_url,
            )
        except Exception as exc:
            self.operations.release_cost(
                tenant_id=tenant_id,
                project_id=project_id,
                job_id=job["id"],
                reason="provider_submission_failed",
            )
            job["state"] = "failed"
            job["error"] = {
                "code": "provider_submission_failed",
                "message": str(exc),
                "retryable": True,
                "details": {},
            }
            job["updatedAt"] = _now()
            job["finishedAt"] = _now()
            self.operations.store.put_job(job)
            self.operations.event(
                tenant_id, project_id, "job.failed", job["id"], job["error"], correlation_id
            )
            raise
        job["state"] = "running"
        job["attempt"] = 1
        job["progress"] = 0
        job["claimedBy"] = "provider:fal"
        job["startedAt"] = _now()
        job["updatedAt"] = _now()
        job.setdefault("extensions", {}).update(
            {
                "providerId": "fal",
                "providerModelId": chosen["modelId"],
                "providerRequestId": submitted["requestId"],
                "generationPlan": plan,
                "approvalId": approval["id"],
                "reservationId": reservation["id"],
                "providerSubmission": submitted,
            }
        )
        self.operations.store.put_job(job)
        self.operations.event(
            tenant_id,
            project_id,
            "provider.submitted",
            job["id"],
            {
                "providerId": "fal",
                "requestId": submitted["requestId"],
                "modelId": chosen["modelId"],
            },
            correlation_id,
        )
        return {
            "job": job,
            "approval": approval,
            "reservation": reservation,
            "plan": plan,
            "provider": submitted,
            "duplicate": False,
        }

    @staticmethod
    def _media_nodes(value: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                url = node.get("url")
                if isinstance(url, str) and url.startswith("https://"):
                    found.append(node)
                for child in node.values():
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(value)
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in found:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        return unique

    def _register_results(
        self,
        *,
        tenant_id: str,
        project_id: str,
        job: dict[str, Any],
        result: dict[str, Any],
        actor_id: str,
    ) -> list[dict[str, Any]]:
        nodes = self._media_nodes(result)
        assets: list[dict[str, Any]] = []
        parents = [
            ref for ref in job.get("inputRefs", []) if isinstance(ref, str) and ref.startswith("ast_")
        ]
        for index, node in enumerate(nodes, 1):
            url = node["url"]
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                continue
            mime = node.get("content_type") or node.get("contentType")
            kind = (
                "video"
                if (mime or "").startswith("video/")
                or parsed.path.lower().endswith((".mp4", ".webm", ".mov"))
                else "audio"
                if (mime or "").startswith("audio/")
                else "image"
            )
            asset = {
                "id": f"ast_{uuid4().hex[:24]}",
                "tenantId": tenant_id,
                "projectId": project_id,
                "kind": kind,
                "role": "generated",
                "name": node.get("file_name") or f"{job['capability']}-{index}",
                "mimeType": mime,
                "bytes": node.get("file_size"),
                "checksum": None,
                "storage": {
                    "type": "provider",
                    "key": f"fal:{job['extensions']['providerRequestId']}:{index}",
                    "bucket": None,
                    "url": url,
                },
                "source": {
                    "type": "generated",
                    "provider": "fal",
                    "externalId": job["extensions"]["providerRequestId"],
                    "parentAssetIds": parents,
                    "license": None,
                    "attribution": None,
                    "sourceUrl": url,
                },
                "media": {
                    "width": node.get("width"),
                    "height": node.get("height"),
                    "durationSeconds": node.get("duration") or node.get("duration_seconds"),
                    "fps": node.get("fps"),
                    "channels": None,
                    "sampleRate": None,
                },
                "rights": {
                    "commercialUse": None,
                    "consentRecordIds": [],
                    "releaseAssetIds": [],
                    "expiresAt": None,
                },
                "tags": ["generated", "fal", job["capability"]],
                "createdAt": _now(),
                "createdBy": actor_id,
                "extensions": {"jobId": job["id"], "providerResult": _copy(node)},
            }
            asset["media"] = {
                key: value for key, value in asset["media"].items() if value is not None
            }
            assets.append(asset)

        def mutate(project: dict[str, Any]) -> dict[str, Any]:
            existing = {
                item.get("storage", {}).get("url") for item in project.get("assets", [])
            }
            project.setdefault("assets", []).extend(
                item for item in assets if item["storage"]["url"] not in existing
            )
            project["project"]["updatedAt"] = _now()
            return project

        if assets:
            self.repository.mutate(tenant_id, project_id, mutate)
        return assets

    def sync(self, *, tenant_id: str, job_id: str, actor_id: str) -> dict[str, Any]:
        job = self.operations.get_job(tenant_id, job_id)
        extensions = job.get("extensions") or {}
        model_id = extensions.get("providerModelId")
        request_id = extensions.get("providerRequestId")
        if not model_id or not request_id:
            raise GenerationError("job has no provider request")
        status = self.fal.status(model_id=model_id, request_id=request_id)
        state = str(status.get("status") or status.get("state") or "").upper()
        self.operations.event(
            tenant_id,
            job["projectId"],
            "provider.status",
            job_id,
            {"providerStatus": state, "requestId": request_id},
        )
        if state in {"COMPLETED", "SUCCEEDED", "SUCCESS"}:
            raw = self.fal.result(model_id=model_id, request_id=request_id)
            assets = self._register_results(
                tenant_id=tenant_id,
                project_id=job["projectId"],
                job=job,
                result=raw,
                actor_id=actor_id,
            )
            output_refs = [item["id"] for item in assets]
            actual = float(job.get("estimatedCost") or 0)
            updated = self.operations.transition(
                tenant_id,
                job_id,
                "succeeded",
                progress=1,
                output_refs=output_refs,
                actual_cost=actual,
            )
            self.operations.reconcile_cost(
                tenant_id=tenant_id,
                project_id=job["projectId"],
                job_id=job_id,
                amount=actual,
                currency=job.get("currency", "USD"),
            )
            return {"job": updated, "assets": assets, "providerResult": raw}
        if state in {"FAILED", "ERROR", "CANCELLED"}:
            error = {
                "code": "provider_failed",
                "message": str(status.get("error") or status.get("detail") or state),
                "retryable": state != "CANCELLED",
                "details": status,
            }
            updated = self.operations.transition(tenant_id, job_id, "failed", error=error)
            self.operations.release_cost(
                tenant_id=tenant_id,
                project_id=job["projectId"],
                job_id=job_id,
                reason="provider_failed",
            )
            return {"job": updated, "assets": [], "providerStatus": status}
        job["progress"] = float(status.get("progress", job.get("progress", 0)) or 0)
        job["updatedAt"] = _now()
        self.operations.store.put_job(job)
        return {"job": job, "assets": [], "providerStatus": status}

    def cancel(self, *, tenant_id: str, job_id: str, approved: bool) -> dict[str, Any]:
        if not approved:
            raise GenerationApprovalRequired("explicit approval is required before cancellation")
        job = self.operations.get_job(tenant_id, job_id)
        extensions = job.get("extensions") or {}
        response = self.fal.cancel(
            model_id=extensions["providerModelId"],
            request_id=extensions["providerRequestId"],
            approved=True,
        )
        updated = self.operations.cancel(tenant_id, job_id)
        self.operations.release_cost(
            tenant_id=tenant_id,
            project_id=job["projectId"],
            job_id=job_id,
            reason="cancelled",
        )
        return {"job": updated, "provider": response}
