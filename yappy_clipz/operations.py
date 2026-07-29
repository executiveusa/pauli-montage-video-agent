"""Durable jobs, events, approvals, costs, budgets, and leases."""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None


class OperationError(RuntimeError): pass
class OperationNotFound(OperationError): pass
class InvalidTransition(OperationError): pass
class BudgetExceeded(OperationError): pass


def now_iso() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def epoch() -> int: return int(time.time())


class OperationStore(Protocol):
    def put_job(self, job:dict[str,Any])->dict[str,Any]: ...
    def get_job(self, tenant_id:str, job_id:str)->dict[str,Any]: ...
    def list_jobs(self, tenant_id:str, project_id:str|None=None)->list[dict[str,Any]]: ...
    def claim_next(self, tenant_id:str, worker_id:str, lease_seconds:int, project_id:str|None=None)->dict[str,Any]|None: ...
    def append_event(self, event:dict[str,Any])->dict[str,Any]: ...
    def list_events(self, tenant_id:str, project_id:str|None=None, after_sequence:int=0)->list[dict[str,Any]]: ...
    def put_approval(self, approval:dict[str,Any])->dict[str,Any]: ...
    def get_approval(self, tenant_id:str, approval_id:str)->dict[str,Any]: ...
    def list_approvals(self, tenant_id:str, project_id:str|None=None)->list[dict[str,Any]]: ...
    def append_cost(self, entry:dict[str,Any])->dict[str,Any]: ...
    def list_costs(self, tenant_id:str, project_id:str|None=None)->list[dict[str,Any]]: ...
    def get_idempotency(self, tenant_id:str, key:str)->dict[str,Any]|None: ...
    def put_idempotency(self, tenant_id:str, key:str, value:dict[str,Any])->None: ...


class JsonOperationStore:
    """Atomic local operation store for owner-controlled and test modes."""
    def __init__(self, path:Path|str) -> None:
        self.path=Path(path).expanduser().resolve(); self.lock=RLock()
    def _read(self)->dict[str,Any]:
        if not self.path.is_file(): return {"jobs":{},"events":[],"approvals":{},"costs":[],"idempotency":{},"sequence":0}
        try:return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:raise OperationError("operation store is unreadable") from exc
    def _write(self,data:dict[str,Any])->None:
        self.path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=".operations.",dir=self.path.parent)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as handle:json.dump(data,handle,sort_keys=True);handle.flush();os.fsync(handle.fileno())
            os.chmod(tmp,0o600);os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    def put_job(self,job):
        with self.lock:data=self._read();data["jobs"][job["id"]]=json.loads(json.dumps(job));self._write(data);return json.loads(json.dumps(job))
    def get_job(self,tenant_id,job_id):
        with self.lock:job=self._read()["jobs"].get(job_id)
        if not job or job.get("tenantId")!=tenant_id:raise OperationNotFound("job not found")
        return job
    def list_jobs(self,tenant_id,project_id=None):
        with self.lock:rows=list(self._read()["jobs"].values())
        return sorted([r for r in rows if r.get("tenantId")==tenant_id and (project_id is None or r.get("projectId")==project_id)],key=lambda r:r["createdAt"],reverse=True)
    def claim_next(self,tenant_id,worker_id,lease_seconds,project_id=None):
        with self.lock:
            data=self._read();now=epoch();candidates=[r for r in data["jobs"].values() if r.get("tenantId")==tenant_id and (project_id is None or r.get("projectId")==project_id) and (r.get("state")=="queued" or (r.get("state")=="claimed" and int(r.get("extensions",{}).get("leaseExpires",0))<=now))]
            if not candidates:return None
            job=sorted(candidates,key=lambda r:r["createdAt"])[0];job["state"]="claimed";job["claimedBy"]=worker_id;job["updatedAt"]=now_iso();job.setdefault("extensions",{})["leaseExpires"]=now+lease_seconds;data["jobs"][job["id"]]=job;self._write(data);return json.loads(json.dumps(job))
    def append_event(self,event):
        with self.lock:data=self._read();data["sequence"]+=1;event=dict(event,sequence=data["sequence"]);data["events"].append(event);self._write(data);return event
    def list_events(self,tenant_id,project_id=None,after_sequence=0):
        with self.lock:rows=self._read()["events"]
        return [r for r in rows if r.get("tenantId")==tenant_id and int(r.get("sequence",0))>after_sequence and (project_id is None or r.get("projectId")==project_id)]
    def put_approval(self,approval):
        with self.lock:data=self._read();data["approvals"][approval["id"]]=approval;self._write(data);return json.loads(json.dumps(approval))
    def get_approval(self,tenant_id,approval_id):
        with self.lock:row=self._read()["approvals"].get(approval_id)
        if not row or row.get("tenantId")!=tenant_id:raise OperationNotFound("approval not found")
        return row
    def list_approvals(self,tenant_id,project_id=None):
        with self.lock:rows=list(self._read()["approvals"].values())
        return [r for r in rows if r.get("tenantId")==tenant_id and (project_id is None or r.get("projectId")==project_id)]
    def append_cost(self,entry):
        with self.lock:data=self._read();data["costs"].append(entry);self._write(data);return entry
    def list_costs(self,tenant_id,project_id=None):
        with self.lock:rows=self._read()["costs"]
        return [r for r in rows if r.get("tenantId")==tenant_id and (project_id is None or r.get("projectId")==project_id)]
    def get_idempotency(self,tenant_id,key):
        with self.lock:return self._read()["idempotency"].get(tenant_id+":"+key)
    def put_idempotency(self,tenant_id,key,value):
        with self.lock:data=self._read();data["idempotency"][tenant_id+":"+key]=value;self._write(data)


class PostgresOperationStore:
    def __init__(self,database_url:str)->None:
        if not database_url or psycopg is None:raise OperationError("PostgreSQL operation store is not configured")
        self.url=database_url
    def _c(self):return psycopg.connect(self.url,row_factory=dict_row)
    def put_job(self,job):
        with self._c() as c:c.execute("INSERT INTO yappy_jobs(tenant_id,project_id,job_id,document,created_at,updated_at) VALUES(%s,%s,%s,%s::jsonb,now(),now()) ON CONFLICT(job_id) DO UPDATE SET document=EXCLUDED.document,updated_at=now()",(job["tenantId"],job["projectId"],job["id"],json.dumps(job)))
        return job
    def get_job(self,tenant_id,job_id):
        with self._c() as c:r=c.execute("SELECT document FROM yappy_jobs WHERE tenant_id=%s AND job_id=%s",(tenant_id,job_id)).fetchone()
        if not r:raise OperationNotFound("job not found")
        return r["document"]
    def list_jobs(self,tenant_id,project_id=None):
        sql="SELECT document FROM yappy_jobs WHERE tenant_id=%s";args=[tenant_id]
        if project_id is not None:sql+=" AND project_id=%s";args.append(project_id)
        sql+=" ORDER BY updated_at DESC"
        with self._c() as c:return [r["document"] for r in c.execute(sql,args).fetchall()]
    def claim_next(self,tenant_id,worker_id,lease_seconds,project_id=None):
        with self._c() as c:
            sql="SELECT job_id,document FROM yappy_jobs WHERE tenant_id=%s AND ((document->>'state')='queued' OR ((document->>'state')='claimed' AND COALESCE((document->'extensions'->>'leaseExpires')::bigint,0)<=extract(epoch from now())))";args=[tenant_id]
            if project_id is not None:sql+=" AND project_id=%s";args.append(project_id)
            sql+=" ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1";row=c.execute(sql,args).fetchone()
            if not row:return None
            job=row["document"];job["state"]="claimed";job["claimedBy"]=worker_id;job["updatedAt"]=now_iso();job.setdefault("extensions",{})["leaseExpires"]=epoch()+lease_seconds;c.execute("UPDATE yappy_jobs SET document=%s::jsonb,updated_at=now() WHERE job_id=%s",(json.dumps(job),row["job_id"]));return job
    def append_event(self,event):
        with self._c() as c:r=c.execute("INSERT INTO yappy_events(tenant_id,project_id,event_id,document,created_at) VALUES(%s,%s,%s,%s::jsonb,now()) RETURNING sequence",(event["tenantId"],event.get("projectId"),event["id"],json.dumps(event))).fetchone();event=dict(event,sequence=r["sequence"]);c.execute("UPDATE yappy_events SET document=%s::jsonb WHERE event_id=%s",(json.dumps(event),event["id"]));return event
    def list_events(self,tenant_id,project_id=None,after_sequence=0):
        sql="SELECT document FROM yappy_events WHERE tenant_id=%s AND sequence>%s";args=[tenant_id,after_sequence]
        if project_id is not None:sql+=" AND project_id=%s";args.append(project_id)
        sql+=" ORDER BY sequence"
        with self._c() as c:return [r["document"] for r in c.execute(sql,args).fetchall()]
    def put_approval(self,a):
        with self._c() as c:c.execute("INSERT INTO yappy_approvals(tenant_id,project_id,approval_id,document,created_at,updated_at) VALUES(%s,%s,%s,%s::jsonb,now(),now()) ON CONFLICT(approval_id) DO UPDATE SET document=EXCLUDED.document,updated_at=now()",(a["tenantId"],a["projectId"],a["id"],json.dumps(a)))
        return a
    def get_approval(self,tenant_id,approval_id):
        with self._c() as c:r=c.execute("SELECT document FROM yappy_approvals WHERE tenant_id=%s AND approval_id=%s",(tenant_id,approval_id)).fetchone()
        if not r:raise OperationNotFound("approval not found")
        return r["document"]
    def list_approvals(self,tenant_id,project_id=None):
        sql="SELECT document FROM yappy_approvals WHERE tenant_id=%s";args=[tenant_id]
        if project_id is not None:sql+=" AND project_id=%s";args.append(project_id)
        with self._c() as c:return [r["document"] for r in c.execute(sql,args).fetchall()]
    def append_cost(self,e):
        with self._c() as c:c.execute("INSERT INTO yappy_cost_ledger(tenant_id,project_id,entry_id,document,created_at) VALUES(%s,%s,%s,%s::jsonb,now())",(e["tenantId"],e["projectId"],e["id"],json.dumps(e)))
        return e
    def list_costs(self,tenant_id,project_id=None):
        sql="SELECT document FROM yappy_cost_ledger WHERE tenant_id=%s";args=[tenant_id]
        if project_id is not None:sql+=" AND project_id=%s";args.append(project_id)
        with self._c() as c:return [r["document"] for r in c.execute(sql,args).fetchall()]
    def get_idempotency(self,tenant_id,key):
        with self._c() as c:r=c.execute("SELECT document FROM yappy_idempotency WHERE tenant_id=%s AND idempotency_key=%s",(tenant_id,key)).fetchone();return r["document"] if r else None
    def put_idempotency(self,tenant_id,key,value):
        with self._c() as c:c.execute("INSERT INTO yappy_idempotency(tenant_id,idempotency_key,document,created_at) VALUES(%s,%s,%s::jsonb,now()) ON CONFLICT(tenant_id,idempotency_key) DO NOTHING",(tenant_id,key,json.dumps(value)))


class OperationsService:
    def __init__(self,store:OperationStore)->None:self.store=store
    def event(self,tenant_id,project_id,event_type,subject_id,data=None,correlation_id=None,causation_id=None):
        return self.store.append_event({"id":f"evt_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"type":event_type,"subjectId":subject_id,"data":data or {},"correlationId":correlation_id,"causationId":causation_id,"createdAt":now_iso()})
    def create_job(self,*,tenant_id,project_id,job_type,capability,input_refs=None,provider_route_id=None,estimated_cost=None,currency="USD",idempotency_key,correlation_id=None,icm_stage=None):
        existing=self.store.get_idempotency(tenant_id,idempotency_key)
        if existing:return self.store.get_job(tenant_id,existing["jobId"])
        job={"id":f"job_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"type":job_type,"capability":capability,"state":"queued","attempt":0,"progress":0,"inputRefs":input_refs or [],"outputRefs":[],"providerRouteId":provider_route_id,"estimatedCost":estimated_cost,"actualCost":None,"currency":currency,"claimedBy":None,"error":None,"createdAt":now_iso(),"updatedAt":now_iso(),"startedAt":None,"finishedAt":None,"extensions":{"correlationId":correlation_id,"icmStage":icm_stage}}
        self.store.put_job(job);self.store.put_idempotency(tenant_id,idempotency_key,{"jobId":job["id"]});self.event(tenant_id,project_id,"job.queued",job["id"],{"capability":capability},correlation_id);return job
    def get_job(self,tenant_id,job_id):return self.store.get_job(tenant_id,job_id)
    def list_jobs(self,tenant_id,project_id=None):return self.store.list_jobs(tenant_id,project_id)
    def claim(self,tenant_id,worker_id,lease_seconds=120,project_id=None):
        job=self.store.claim_next(tenant_id,worker_id,lease_seconds,project_id)
        if job:self.event(tenant_id,job["projectId"],"job.claimed",job["id"],{"workerId":worker_id,"leaseSeconds":lease_seconds})
        return job
    def transition(self,tenant_id,job_id,state,*,progress=None,output_refs=None,error=None,actual_cost=None):
        job=self.store.get_job(tenant_id,job_id);allowed={"queued":{"cancelled","claimed"},"claimed":{"running","queued","cancelled"},"running":{"succeeded","failed","cancelled","awaiting_approval"},"awaiting_approval":{"queued","cancelled"},"failed":{"queued"},"succeeded":set(),"cancelled":set()}
        if state not in allowed.get(job["state"],set()):raise InvalidTransition(f"cannot transition {job['state']} to {state}")
        job["state"]=state;job["updatedAt"]=now_iso()
        if state=="running" and not job.get("startedAt"):job["startedAt"]=now_iso();job["attempt"]+=1
        if state in {"succeeded","failed","cancelled"}:job["finishedAt"]=now_iso()
        if progress is not None:job["progress"]=max(0,min(float(progress),1))
        if output_refs is not None:job["outputRefs"]=output_refs
        if error is not None:job["error"]=error
        if actual_cost is not None:job["actualCost"]=actual_cost
        self.store.put_job(job);self.event(tenant_id,job["projectId"],f"job.{state}",job_id,{"progress":job.get("progress"),"error":error});return job
    def cancel(self,tenant_id,job_id):return self.transition(tenant_id,job_id,"cancelled")
    def retry(self,tenant_id,job_id):return self.transition(tenant_id,job_id,"queued")
    def request_approval(self,*,tenant_id,project_id,scope_type,subject_id,requested_by,note=None,evidence=None,expires_at=None):
        a={"id":f"apr_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"scopeType":scope_type,"subjectId":subject_id,"status":"pending","requestedAt":now_iso(),"requestedBy":requested_by,"resolvedAt":None,"resolvedBy":None,"note":note,"evidence":evidence or [],"expiresAt":expires_at,"extensions":{}}
        self.store.put_approval(a);self.event(tenant_id,project_id,"approval.requested",a["id"],{"scopeType":scope_type,"subjectId":subject_id});return a
    def decide_approval(self,tenant_id,approval_id,status,resolved_by,note=None):
        if status not in {"approved","rejected","revoked"}:raise OperationError("invalid approval decision")
        a=self.store.get_approval(tenant_id,approval_id)
        if a["status"]!="pending" and status!="revoked":raise InvalidTransition("approval is not pending")
        a["status"]=status;a["resolvedAt"]=now_iso();a["resolvedBy"]=resolved_by
        if note is not None:a["note"]=note
        self.store.put_approval(a);self.event(tenant_id,a["projectId"],f"approval.{status}",approval_id,{"subjectId":a["subjectId"]});return a
    def reserve_cost(self,*,tenant_id,project_id,job_id,amount,currency="USD",budget_limit=None):
        spent=sum(float(e["amount"]) for e in self.store.list_costs(tenant_id,project_id) if e["kind"] in {"reserved","actual"} and e.get("status")!="released")
        if budget_limit is not None and spent+amount>budget_limit:raise BudgetExceeded("budget policy would be exceeded")
        e={"id":f"cost_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"jobId":job_id,"kind":"reserved","status":"active","amount":float(amount),"currency":currency,"createdAt":now_iso()};self.store.append_cost(e);self.event(tenant_id,project_id,"cost.reserved",e["id"],{"jobId":job_id,"amount":amount,"currency":currency});return e
    def reconcile_cost(self,*,tenant_id,project_id,job_id,amount,currency="USD"):
        e={"id":f"cost_{uuid4().hex[:24]}","tenantId":tenant_id,"projectId":project_id,"jobId":job_id,"kind":"actual","status":"committed","amount":float(amount),"currency":currency,"createdAt":now_iso()};self.store.append_cost(e);self.event(tenant_id,project_id,"cost.committed",e["id"],{"jobId":job_id,"amount":amount,"currency":currency});return e
