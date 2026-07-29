"""Budget-aware OperationsService with reservation-to-actual reconciliation."""
from __future__ import annotations
from .operations import BudgetExceeded,OperationsService,now_iso
from uuid import uuid4

class BudgetedOperationsService(OperationsService):
 def effective_spend(self,tenant_id:str,project_id:str)->float:
  by_job={}
  for entry in self.store.list_costs(tenant_id,project_id):
   by_job.setdefault(entry["jobId"],[]).append(entry)
  total=0.0
  for entries in by_job.values():
   actual=[e for e in entries if e.get("kind")=="actual" and e.get("status")!="reversed"]
   if actual:total+=sum(float(e["amount"]) for e in actual)
   else:total+=sum(float(e["amount"]) for e in entries if e.get("kind")=="reserved" and e.get("status")=="active")
  return total
 def reserve_cost(self,*,tenant_id,project_id,job_id,amount,currency="USD",budget_limit=None):
  amount=float(amount)
  if amount<0:raise BudgetExceeded("cost reservation cannot be negative")
  if budget_limit is not None and self.effective_spend(tenant_id,project_id)+amount>float(budget_limit):raise BudgetExceeded("budget policy would be exceeded")
  entry={"id":f"cost_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"jobId":job_id,"kind":"reserved","status":"active","amount":amount,"currency":currency,"createdAt":now_iso()}
  self.store.append_cost(entry);self.event(tenant_id,project_id,"cost.reserved",entry["id"],{"jobId":job_id,"amount":amount,"currency":currency});return entry
 def reconcile_cost(self,*,tenant_id,project_id,job_id,amount,currency="USD"):
  entry={"id":f"cost_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"jobId":job_id,"kind":"actual","status":"committed","amount":float(amount),"currency":currency,"createdAt":now_iso()}
  self.store.append_cost(entry);self.event(tenant_id,project_id,"cost.committed",entry["id"],{"jobId":job_id,"amount":float(amount),"currency":currency,"replacesReservation":True});return entry
