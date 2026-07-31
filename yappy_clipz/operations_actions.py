"""Universal action extensions for jobs, events, approvals, costs, and routing."""
from __future__ import annotations
from typing import Any
from .actions import ActionContext
from .errors import ActionProblem
from .hosted_actions import HostedActionDispatcher,HostedCapabilityRegistry,_cap
from .operations import BudgetExceeded,InvalidTransition,OperationError,OperationNotFound,OperationsService
from .router import OmniRouter

_OP_CAPS={
 "job.create":_cap("job.create","Create job","Create one durable idempotent asynchronous job.",scopes=["project:read","job:write"],risk="medium",idempotency="required",stage="06_animation"),
 "job.get":_cap("job.get","Get job","Inspect one durable job.",scopes=["job:read"]),
 "job.list":_cap("job.list","List jobs","List durable jobs by tenant and optional project.",scopes=["job:read"]),
 "job.claim":_cap("job.claim","Claim job","Lease the next queued job to a worker.",scopes=["job:write"],risk="medium",idempotency="supported"),
 "job.start":_cap("job.start","Start job","Move a claimed job to running.",scopes=["job:write"],risk="medium",idempotency="supported"),
 "job.complete":_cap("job.complete","Complete job","Commit output references and actual cost.",scopes=["job:write"],risk="medium",idempotency="supported"),
 "job.fail":_cap("job.fail","Fail job","Record structured retryable failure evidence.",scopes=["job:write"],risk="medium",idempotency="supported"),
 "job.cancel":_cap("job.cancel","Cancel job","Cancel queued, claimed, or running work.",scopes=["job:write"],risk="medium",approval="explicit",idempotency="supported"),
 "job.retry":_cap("job.retry","Retry job","Return a failed job to the queue.",scopes=["job:write"],risk="medium",approval="explicit",idempotency="supported"),
 "event.list":_cap("event.list","List events","Read ordered events after an optional cursor.",scopes=["job:read"]),
 "event.stream":_cap("event.stream","Stream events","Return an ordered cursor page for polling or remote streaming adapters.",scopes=["job:read"]),
 "approval.request":_cap("approval.request","Request approval","Create a durable human approval request.",scopes=["job:write"],risk="medium",idempotency="supported"),
 "approval.list":_cap("approval.list","List approvals","List project approval evidence.",scopes=["job:read"]),
 "approval.decide":_cap("approval.decide","Decide approval","Approve, reject, or revoke an operation.",scopes=["job:write"],risk="high",approval="explicit",idempotency="supported"),
 "cost.estimate":_cap("cost.estimate","Estimate cost","Estimate candidate provider/model cost without submission.",scopes=["provider:read"]),
 "cost.reserve":_cap("cost.reserve","Reserve cost","Reserve project budget before paid execution.",scopes=["budget:spend"],risk="high",approval="explicit",idempotency="required"),
 "cost.reconcile":_cap("cost.reconcile","Reconcile cost","Commit actual provider spend evidence.",scopes=["budget:spend"],risk="high",idempotency="required"),
 "cost.list":_cap("cost.list","List costs","Read reserved and actual cost ledger entries.",scopes=["job:read"]),
 "route.plan":_cap("route.plan","Plan route","Rank eligible provider models using cost, quality, privacy, and lifecycle policy.",scopes=["provider:read"]),
 "route.explain":_cap("route.explain","Explain route","Explain a previously computed route plan.",scopes=["provider:read"]),
}

class OperationsCapabilityRegistry:
 def __init__(self,base:HostedCapabilityRegistry)->None:self.base=base
 def list(self,*,lifecycle=None):
  rows=self.base.list(lifecycle=lifecycle);rows.extend(v for v in _OP_CAPS.values() if lifecycle is None or v["lifecycle"]==lifecycle);return sorted(rows,key=lambda x:x["actionId"])
 def describe(self,action_id):return dict(_OP_CAPS[action_id]) if action_id in _OP_CAPS else self.base.describe(action_id)
 def contains(self,action_id):return action_id in _OP_CAPS or self.base.contains(action_id)
 def action_ids(self):return tuple(sorted(set(self.base.action_ids())|set(_OP_CAPS)))

class OperationsActionDispatcher(HostedActionDispatcher):
 def __init__(self,*,operations:OperationsService,router:OmniRouter,**kwargs):
  self.operations=operations;self.router=router;super().__init__(**kwargs);self._handlers.update({
   "job.create":self._job_create,"job.get":self._job_get,"job.list":self._job_list,"job.claim":self._job_claim,"job.start":self._job_start,"job.complete":self._job_complete,"job.fail":self._job_fail,"job.cancel":self._job_cancel,"job.retry":self._job_retry,
   "event.list":self._events,"event.stream":self._events,"approval.request":self._approval_request,"approval.list":self._approval_list,"approval.decide":self._approval_decide,
   "cost.estimate":self._cost_estimate,"cost.reserve":self._cost_reserve,"cost.reconcile":self._cost_reconcile,"cost.list":self._cost_list,"route.plan":self._route_plan,"route.explain":self._route_explain})
 def dispatch(self,*args,**kwargs):
  try:return super().dispatch(*args,**kwargs)
  except ActionProblem:raise
  except OperationNotFound as exc:raise ActionProblem("not_found",str(exc),404) from exc
  except InvalidTransition as exc:raise ActionProblem("invalid_transition",str(exc),409) from exc
  except BudgetExceeded as exc:raise ActionProblem("budget_exceeded",str(exc),409) from exc
  except OperationError as exc:raise ActionProblem("invalid_request",str(exc),400) from exc
 def _job_create(self,p,c):return self.operations.create_job(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),job_type=self.req(p,"type"),capability=self.req(p,"capability"),input_refs=p.get("inputRefs",[]),provider_route_id=p.get("providerRouteId"),estimated_cost=p.get("estimatedCost"),currency=p.get("currency","USD"),idempotency_key=c.idempotency_key or self.req(p,"idempotencyKey"),correlation_id=c.correlation_id,icm_stage=p.get("icmStage"))
 def _job_get(self,p,c):return self.operations.get_job(self.tenant(c),self.req(p,"jobId"))
 def _job_list(self,p,c):return self.operations.list_jobs(self.tenant(c),p.get("projectId"))
 def _job_claim(self,p,c):return self.operations.claim(self.tenant(c),self.req(p,"workerId"),int(p.get("leaseSeconds",120)),p.get("projectId"))
 def _job_start(self,p,c):return self.operations.transition(self.tenant(c),self.req(p,"jobId"),"running")
 def _job_complete(self,p,c):return self.operations.transition(self.tenant(c),self.req(p,"jobId"),"succeeded",progress=1,output_refs=p.get("outputRefs",[]),actual_cost=p.get("actualCost"))
 def _job_fail(self,p,c):return self.operations.transition(self.tenant(c),self.req(p,"jobId"),"failed",error=self.req(p,"error"))
 def _job_cancel(self,p,c):return self.operations.cancel(self.tenant(c),self.req(p,"jobId"))
 def _job_retry(self,p,c):return self.operations.retry(self.tenant(c),self.req(p,"jobId"))
 def _events(self,p,c):return self.operations.store.list_events(self.tenant(c),p.get("projectId"),int(p.get("afterSequence",0)))
 def _approval_request(self,p,c):return self.operations.request_approval(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),scope_type=self.req(p,"scopeType"),subject_id=self.req(p,"subjectId"),requested_by=c.actor_id,note=p.get("note"),evidence=p.get("evidence"),expires_at=p.get("expiresAt"))
 def _approval_list(self,p,c):return self.operations.store.list_approvals(self.tenant(c),p.get("projectId"))
 def _approval_decide(self,p,c):return self.operations.decide_approval(self.tenant(c),self.req(p,"approvalId"),self.req(p,"status"),c.actor_id or "unknown",p.get("note"))
 def _route_plan(self,p,c):return self.router.plan(capability=self.req(p,"capability"),payload=p.get("input",{}),quality_lane=p.get("qualityLane","economy"),max_cost=p.get("maxCost"),preferred_provider=p.get("preferredProvider"),privacy_lane=p.get("privacyLane","cloud"),allow_experimental=bool(p.get("allowExperimental",True)))
 def _route_explain(self,p,c):return self.router.explain(self.req(p,"plan"))
 def _cost_estimate(self,p,c):return self._route_plan(p,c)
 def _cost_reserve(self,p,c):return self.operations.reserve_cost(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),job_id=self.req(p,"jobId"),amount=float(self.req(p,"amount")),currency=p.get("currency","USD"),budget_limit=p.get("budgetLimit"))
 def _cost_reconcile(self,p,c):return self.operations.reconcile_cost(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),job_id=self.req(p,"jobId"),amount=float(self.req(p,"amount")),currency=p.get("currency","USD"))
 def _cost_list(self,p,c):return self.operations.store.list_costs(self.tenant(c),p.get("projectId"))
