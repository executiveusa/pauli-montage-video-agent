"""Universal action dispatcher shared by CLI, API, MCP, and A2A callers."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib, json, threading
from typing import Any, Callable
from uuid import uuid4

from .capabilities import CapabilityRegistry, CapabilityRegistryError
from .errors import ActionProblem
from .icm_runtime import IcmNotFound, IcmRuntime, IcmRuntimeError
from .prompt_locker import PromptLocker, PromptLockerError, PromptNotFound
from .providers import (FalApprovalRequired, FalExecutionDisabled, FalProviderAdapter,
    FalProviderError, FalProviderValidationError, FalUpstreamError, ProviderCatalog, ProviderCatalogError)
from .repository import ProjectNotFound, RepositoryBusy, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict

@dataclass(frozen=True, slots=True)
class ActionContext:
    tenant_id: str | None = None
    actor_id: str | None = None
    approved: bool = False
    idempotency_key: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    request_id: str | None = None
    scopes: tuple[str, ...] | None = None

class IdempotencyStore:
    """Process-local duplicate suppression for owner/local and tests."""
    def __init__(self) -> None:
        self._lock, self._records = threading.Lock(), {}
    @staticmethod
    def digest(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    def lookup(self, tenant: str, action: str, key: str, payload: dict[str, Any]) -> Any | None:
        identity, digest = (tenant, action, key), self.digest(payload)
        with self._lock:
            record = self._records.get(identity)
            if record is None: return None
            if record[0] != digest:
                raise ActionProblem("idempotency_conflict", "idempotency key was already used with different input", 409)
            return json.loads(json.dumps(record[1]))
    def save(self, tenant: str, action: str, key: str, payload: dict[str, Any], result: Any) -> None:
        with self._lock: self._records[(tenant, action, key)] = (self.digest(payload), json.loads(json.dumps(result)))

class ActionDispatcher:
    def __init__(self, *, service: StudioService, registry: CapabilityRegistry, prompt_locker: PromptLocker,
                 provider_catalog: ProviderCatalog, fal: FalProviderAdapter, icm: IcmRuntime,
                 idempotency_store: IdempotencyStore | None = None) -> None:
        self.service, self.registry, self.prompt_locker = service, registry, prompt_locker
        self.provider_catalog, self.fal, self.icm = provider_catalog, fal, icm
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self._handlers: dict[str, Callable[[dict[str, Any], ActionContext], Any]] = {
            "capabilities.list": lambda p,c: self.registry.list(lifecycle=p.get("lifecycle")),
            "capabilities.describe": lambda p,c: self.registry.describe(self.req(p,"actionId")),
            "system.health": lambda p,c: {"ok":True,"service":"yappy-clipz","falConfigured":self.fal.configured(),"falExecutionEnabled":self.fal.settings.execution_enabled},
            "system.version": lambda p,c: {"product":"YAPPY-CLIPZ","interfaceContract":"1.0.0","studioProject":"1.0.0","promptLocker":"1.0.0","providerManifest":"1.0.0","icm":"2.0.0"},
            "project.create": self._project_create, "project.list": lambda p,c:self.service.list_projects(tenant_id=self.tenant(c)),
            "project.get": lambda p,c:self.service.get_project(tenant_id=self.tenant(c),project_id=self.req(p,"projectId")),
            "project.validate": lambda p,c:self.service.validate_project(tenant_id=self.tenant(c),project_id=self.req(p,"projectId")),
            "timeline.get": lambda p,c:self.service.get_timeline(tenant_id=self.tenant(c),project_id=self.req(p,"projectId")),
            "timeline.replace": self._timeline_replace,
            "prompt.list": lambda p,c:self.prompt_locker.list_prompts(), "prompt.get": lambda p,c:self.prompt_locker.get_prompt(self.req(p,"promptId")),
            "prompt.compile": lambda p,c:self.prompt_locker.compile_prompt(self.req(p,"promptId"),p.get("variables",{})),
            "workflow.list": lambda p,c:self.prompt_locker.list_workflows(), "workflow.get": lambda p,c:self.prompt_locker.get_workflow(self.req(p,"workflowId")),
            "workflow.compile": lambda p,c:self.prompt_locker.compile_workflow(self.req(p,"workflowId"),p.get("variables",{})),
            "provider.list": self._provider_list, "provider.get": self._provider_get, "provider.request.plan": self._provider_plan,
            "provider.request.submit": self._provider_submit, "provider.request.status": self._provider_status,
            "provider.request.result": self._provider_result, "provider.request.cancel": self._provider_cancel,
            "icm.workspace.create": self._icm_workspace, "icm.run.create": self._icm_run_create, "icm.run.get": self._icm_run_get,
            "icm.run.resume": self._icm_run_resume, "icm.stage.get": self._icm_stage_get, "icm.stage.prepare": self._icm_stage_prepare,
            "icm.stage.start": self._icm_stage_start, "icm.stage.verify": self._icm_stage_verify, "icm.stage.handoff": self._icm_stage_handoff,
            "icm.stage.mark-stale": self._icm_stage_stale, "icm.context.compile": self._icm_context,
            "icm.artifact.resolve": self._icm_artifact,
        }

    @staticmethod
    def req(payload: dict[str, Any], name: str) -> Any:
        value = payload.get(name)
        if value is None or value == "": raise ActionProblem("invalid_request", f"{name} is required", 400, details={"field":name})
        return value
    @staticmethod
    def tenant(context: ActionContext) -> str:
        if not context.tenant_id: raise ActionProblem("authentication_required", "tenant context is required", 401)
        return context.tenant_id

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        c, payload = context or ActionContext(), input_payload or {}
        request_id, correlation_id = c.request_id or f"req_{uuid4().hex}", c.correlation_id or f"corr_{uuid4().hex}"
        if not isinstance(payload, dict): raise ActionProblem("invalid_request", "input must be an object", 400)
        try:
            cap = self.registry.describe(action_id)
            required = set(cap.get("requiredScopes", []))
            if c.scopes is not None and not required.issubset(c.scopes):
                raise ActionProblem("authorization_denied", "caller lacks required scopes", 403, details={"requiredScopes":sorted(required)})
            if cap.get("approvalPolicy") == "explicit" and not c.approved:
                raise ActionProblem("approval_required", "explicit approval is required for this action", 409)
            if cap.get("idempotency") == "required" and not c.idempotency_key:
                raise ActionProblem("invalid_request", "idempotency key is required for this action", 400)
            cached = self.idempotency_store.lookup(c.tenant_id or "_system",action_id,c.idempotency_key,payload) if c.idempotency_key else None
            result = cached if cached is not None else self._handlers[action_id](payload,c)
            replay = cached is not None
            if c.idempotency_key and not replay: self.idempotency_store.save(c.tenant_id or "_system",action_id,c.idempotency_key,payload,result)
        except ActionProblem: raise
        except (KeyError, CapabilityRegistryError) as exc: raise ActionProblem("not_found", str(exc), 404) from exc
        except PromptNotFound as exc: raise ActionProblem("not_found", str(exc), 404) from exc
        except (PromptLockerError, ProviderCatalogError, FalProviderError, IcmRuntimeError, ServiceValidationError, RepositoryError, ValueError) as exc:
            raise self._problem(exc) from exc
        doc = {"contractVersion":"1.0.0","requestId":request_id,"correlationId":correlation_id,"causationId":c.causation_id,
               "actionId":action_id,"status":"accepted" if action_id=="provider.request.submit" else "succeeded","idempotentReplay":replay,
               "result":result,"evidence":{"eventIds":[],"decisionIds":[],"approvalIds":[],"artifactRefs":[],"icmHandoffRef":None}}
        if action_id == "provider.request.submit":
            doc["job"]={"id":result.get("requestId"),"providerId":result.get("providerId"),"providerRequestId":result.get("requestId"),
                        "state":result.get("state","queued"),"progress":0,"approvalRequired":False,"estimatedCost":result.get("estimatedCost")}
        return doc

    @staticmethod
    def _problem(exc: Exception) -> ActionProblem:
        if isinstance(exc,(ProjectNotFound,IcmNotFound)): return ActionProblem("not_found","project not found",404)
        if isinstance(exc,TimelineVersionConflict): return ActionProblem("version_conflict",str(exc),409,details={"resource":"timeline","expectedVersion":exc.expected_version,"currentVersion":exc.current_version})
        if isinstance(exc,RepositoryBusy): return ActionProblem("project_busy",str(exc),503,True)
        if isinstance(exc,FalApprovalRequired): return ActionProblem("approval_required",str(exc),409)
        if isinstance(exc,FalExecutionDisabled): return ActionProblem("policy_denied",str(exc),403)
        if isinstance(exc,FalProviderValidationError): return ActionProblem("invalid_request",str(exc),400)
        if isinstance(exc,FalUpstreamError): return ActionProblem("provider_unavailable",str(exc),503,True)
        if isinstance(exc,FalProviderError): return ActionProblem("provider_unavailable",str(exc),503,True)
        return ActionProblem("invalid_request",str(exc),400)

    def _project_create(self,p,c):
        return self.service.create_project(tenant_id=self.tenant(c),slug=self.req(p,"slug"),title=self.req(p,"title"),objective=self.req(p,"objective"),
            deliverables=self.req(p,"deliverables"),quality_lane=p.get("qualityLane","premium"),audience=p.get("audience",[]),constraints=p.get("constraints",[]))
    def _timeline_replace(self,p,c):
        return self.service.replace_timeline(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),expected_version=self.req(p,"expectedVersion"),timeline=self.req(p,"timeline"))
    def _provider_list(self,p,c):
        rows=self.provider_catalog.list()
        for row in rows:
            if row["providerId"]=="fal": row.update(configured=self.fal.configured(),executionEnabled=self.fal.settings.execution_enabled)
        return rows
    def _provider_get(self,p,c):
        provider=self.req(p,"providerId"); return self.fal.describe() if provider=="fal" else self.provider_catalog.get(provider)
    @staticmethod
    def _fal_only(p):
        if p.get("providerId","fal")!="fal": raise ActionProblem("invalid_request","only the fal provider is implemented in this phase",400)
    def _provider_plan(self,p,c): self._fal_only(p); return self.fal.plan(model_id=self.req(p,"modelId"),input_payload=self.req(p,"input"),webhook_url=p.get("webhookUrl"))
    def _provider_submit(self,p,c): self._fal_only(p); return self.fal.submit(model_id=self.req(p,"modelId"),input_payload=self.req(p,"input"),approved=c.approved,idempotency_key=c.idempotency_key or p.get("idempotencyKey",""),webhook_url=p.get("webhookUrl"))
    def _provider_status(self,p,c): self._fal_only(p); return self.fal.status(model_id=self.req(p,"modelId"),request_id=self.req(p,"requestId"),logs=bool(p.get("logs",True)))
    def _provider_result(self,p,c): self._fal_only(p); return self.fal.result(model_id=self.req(p,"modelId"),request_id=self.req(p,"requestId"))
    def _provider_cancel(self,p,c): self._fal_only(p); return self.fal.cancel(model_id=self.req(p,"modelId"),request_id=self.req(p,"requestId"),approved=c.approved)

    def _icm_project(self,p,c):
        tenant,project=self.tenant(c),self.req(p,"projectId"); self.service.get_project(tenant_id=tenant,project_id=project); return tenant,project
    def _icm_workspace(self,p,c): t,j=self._icm_project(p,c); return self.icm.create_workspace(tenant_id=t,project_id=j)
    def _icm_run_create(self,p,c): t,j=self._icm_project(p,c); return self.icm.create_run(tenant_id=t,project_id=j,actor_id=c.actor_id,correlation_id=c.correlation_id,parent_run_id=p.get("parentRunId"),run_id=p.get("runId"))
    def _icm_run_get(self,p,c): t,j=self._icm_project(p,c); return self.icm.get_run(tenant_id=t,project_id=j,run_id=self.req(p,"runId"))
    def _icm_run_resume(self,p,c): t,j=self._icm_project(p,c); return self.icm.resume_run(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),actor_id=c.actor_id)
    def _icm_stage_get(self,p,c): t,j=self._icm_project(p,c); return self.icm.get_stage(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"))
    def _icm_stage_prepare(self,p,c):
        t,j=self._icm_project(p,c); return self.icm.prepare_stage(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"),
            input_refs=p.get("inputRefs",[]),allowed_action_ids=self.req(p,"allowedActionIds"),required_scopes=p.get("requiredScopes",[]),risk_ceiling=p.get("riskCeiling","medium"),max_context_tokens=p.get("maxContextTokens",8000))
    def _icm_stage_start(self,p,c): t,j=self._icm_project(p,c); return self.icm.start_stage(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"))
    def _icm_stage_verify(self,p,c): t,j=self._icm_project(p,c); return self.icm.verify_stage(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"),outputs=p.get("outputs",[]),verification=self.req(p,"verification"))
    def _icm_stage_handoff(self,p,c):
        t,j=self._icm_project(p,c); return self.icm.handoff_stage(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"),
            actor=p.get("actor") or {"actorId":c.actor_id,"type":"agent","client":"action-dispatcher","model":"unknown"},action_ids=p.get("actionIds",[]),decision_ids=p.get("decisionIds",[]),approval_ids=p.get("approvalIds",[]),job_ids=p.get("jobIds",[]),event_ids=p.get("eventIds",[]),artifact_ids=p.get("artifactIds",[]),blockers=p.get("blockers",[]),warnings=p.get("warnings",[]),next_stage_id=p.get("nextStageId"))
    def _icm_stage_stale(self,p,c): t,j=self._icm_project(p,c); return self.icm.mark_stage_stale(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"),reason=self.req(p,"reason"))
    def _icm_context(self,p,c): t,j=self._icm_project(p,c); return self.icm.compile_context(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),stage_id=self.req(p,"stageId"))
    def _icm_artifact(self,p,c): t,j=self._icm_project(p,c); return self.icm.resolve_artifact(tenant_id=t,project_id=j,run_id=self.req(p,"runId"),relative_path=self.req(p,"relativePath"))
