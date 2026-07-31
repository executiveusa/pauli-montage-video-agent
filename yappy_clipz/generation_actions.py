"""Universal generation workbench actions."""
from __future__ import annotations
from typing import Any

from .actions import ActionContext
from .errors import ActionProblem
from .generation import GenerationApprovalRequired,GenerationError,GenerationExecutionUnavailable,GenerationResultInvalid,GenerationService
from .operations_actions import OperationsActionDispatcher,OperationsCapabilityRegistry
from .hosted_actions import _cap

_MEDIA_ACTIONS={
 "image.generate":"image.generate","image.edit":"image.edit","image.inpaint":"image.inpaint","image.outpaint":"image.outpaint","image.upscale":"image.upscale","image.variation":"image.variation",
 "video.text_to_video":"video.text_to_video","video.image_to_video":"video.image_to_video","video.reference_to_video":"video.reference_to_video","video.extend":"video.extend","video.regenerate":"video.regenerate",
}
_GEN_CAPS={
 "generation.plan":_cap("generation.plan","Plan generation","Validate, route, and estimate one provider-neutral generation request.",scopes=["project:read","provider:read"],stage="04_prompt_compile"),
 "generation.workflow.plan":_cap("generation.workflow.plan","Plan generation workflow","Compile Prompt Locker steps into routed, estimated generation plans.",scopes=["project:read","provider:read","prompt:compile"],stage="04_prompt_compile"),
 "generation.workflow.submit":_cap("generation.workflow.submit","Submit generation workflow","Approve and queue each routed workflow step.",scopes=["project:read","job:write","provider:execute","budget:spend"],risk="high",approval="explicit",idempotency="required",stage="06_animation"),
 "generation.sync":_cap("generation.sync","Sync provider job","Poll provider status, normalize outputs, register generated assets, and reconcile cost.",scopes=["job:write","asset:write","provider:read"],risk="medium",idempotency="supported",stage="06_animation"),
 "generation.cancel":_cap("generation.cancel","Cancel provider job","Cancel provider work, release reservation, and close the durable job.",scopes=["job:write","provider:execute","budget:spend"],risk="high",approval="explicit",idempotency="supported",stage="06_animation"),
}
for action_id in _MEDIA_ACTIONS:
 _GEN_CAPS[action_id]=_cap(action_id,action_id.replace("_"," ").replace("."," · ").title(),"Submit an approved provider-neutral media generation job.",scopes=["project:read","job:write","provider:execute","budget:spend"],risk="high",approval="explicit",idempotency="required",stage="06_animation")

class GenerationCapabilityRegistry:
 def __init__(self,base:OperationsCapabilityRegistry)->None:self.base=base
 def list(self,*,lifecycle=None):
  rows=self.base.list(lifecycle=lifecycle);rows.extend(v for v in _GEN_CAPS.values() if lifecycle is None or v["lifecycle"]==lifecycle);return sorted(rows,key=lambda x:x["actionId"])
 def describe(self,action_id):return dict(_GEN_CAPS[action_id]) if action_id in _GEN_CAPS else self.base.describe(action_id)
 def contains(self,action_id):return action_id in _GEN_CAPS or self.base.contains(action_id)
 def action_ids(self):return tuple(sorted(set(self.base.action_ids())|set(_GEN_CAPS)))

class GenerationActionDispatcher(OperationsActionDispatcher):
 def __init__(self,*,generation:GenerationService,**kwargs):
  self.generation=generation;super().__init__(**kwargs);self._handlers.update({"generation.plan":self._plan,"generation.workflow.plan":self._workflow_plan,"generation.workflow.submit":self._workflow_submit,"generation.sync":self._sync,"generation.cancel":self._cancel})
  for action_id in _MEDIA_ACTIONS:self._handlers[action_id]=self._submit_media
 def dispatch(self,*args,**kwargs):
  try:return super().dispatch(*args,**kwargs)
  except ActionProblem:raise
  except GenerationApprovalRequired as exc:raise ActionProblem("approval_required",str(exc),409) from exc
  except GenerationExecutionUnavailable as exc:raise ActionProblem("policy_denied",str(exc),403) from exc
  except GenerationResultInvalid as exc:raise ActionProblem("provider_result_invalid",str(exc),502,True) from exc
  except GenerationError as exc:raise ActionProblem("invalid_request",str(exc),400) from exc
 def _plan(self,p,c):return self.generation.prepare(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),capability=self.req(p,"capability"),provider_input=self.req(p,"providerInput"),model_id=p.get("modelId"),quality_lane=p.get("qualityLane","economy"),privacy_lane=p.get("privacyLane","cloud"),max_cost=p.get("maxCost"),preferred_provider=p.get("preferredProvider","fal"),webhook_url=p.get("webhookUrl"))
 def _workflow_plan(self,p,c):return self.generation.plan_workflow(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),workflow_id=self.req(p,"workflowId"),variables=p.get("variables",{}),max_cost=p.get("maxCost"),quality_lane=p.get("qualityLane","economy"),privacy_lane=p.get("privacyLane","cloud"))
 def _submit_media(self,p,c):
  return self.generation.submit(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),capability=self.registry.describe(c.request_id or "").get("actionId") if False else self.req(p,"capability") if p.get("capability") else p.get("_actionId",""),provider_input=self.req(p,"providerInput"),actor_id=c.actor_id or "unknown",approved=c.approved,idempotency_key=c.idempotency_key or self.req(p,"idempotencyKey"),model_id=p.get("modelId"),quality_lane=p.get("qualityLane","economy"),privacy_lane=p.get("privacyLane","cloud"),max_cost=p.get("maxCost"),budget_limit=p.get("budgetLimit"),input_refs=p.get("inputRefs",[]),correlation_id=c.correlation_id,webhook_url=p.get("webhookUrl"))
 def dispatch(self,action_id,*args,**kwargs):
  input_payload=args[0] if args else kwargs.get("input_payload")
  if action_id in _MEDIA_ACTIONS:
   payload=dict(input_payload or {});payload["_actionId"]=_MEDIA_ACTIONS[action_id]
   if args:args=(payload,)+args[1:]
   else:kwargs["input_payload"]=payload
  try:return super().dispatch(action_id,*args,**kwargs)
  except ActionProblem:raise
  except GenerationApprovalRequired as exc:raise ActionProblem("approval_required",str(exc),409) from exc
  except GenerationExecutionUnavailable as exc:raise ActionProblem("policy_denied",str(exc),403) from exc
  except GenerationResultInvalid as exc:raise ActionProblem("provider_result_invalid",str(exc),502,True) from exc
  except GenerationError as exc:raise ActionProblem("invalid_request",str(exc),400) from exc
 def _workflow_submit(self,p,c):
  planned=self._workflow_plan(p,c);jobs=[]
  for index,step in enumerate(planned["steps"],1):
   plan=step["plan"];jobs.append(self.generation.submit(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),capability=plan["capability"],provider_input=plan["providerPlan"]["input"],actor_id=c.actor_id or "unknown",approved=c.approved,idempotency_key=f"{c.idempotency_key}:{index}",model_id=plan["route"]["chosen"]["modelId"],quality_lane=p.get("qualityLane","economy"),privacy_lane=p.get("privacyLane","cloud"),max_cost=p.get("maxCost"),budget_limit=p.get("budgetLimit"),input_refs=p.get("inputRefs",[]),correlation_id=c.correlation_id))
  return {"workflow":planned,"submissions":jobs}
 def _sync(self,p,c):return self.generation.sync(tenant_id=self.tenant(c),job_id=self.req(p,"jobId"),actor_id=c.actor_id or "unknown")
 def _cancel(self,p,c):return self.generation.cancel(tenant_id=self.tenant(c),job_id=self.req(p,"jobId"),approved=c.approved)
