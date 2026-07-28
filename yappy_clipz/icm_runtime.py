"""ICM Runtime v2: tenant-scoped context materialization and resumable handoffs."""
from __future__ import annotations
import hashlib, json, os, re, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

STAGES=("00_intake","01_second_brain_ingest","02_canon_bibles","03_scene_blueprint","04_prompt_compile","05_voice_music","06_animation","07_render","08_edit_localize","09_publish_bridge","10_qa_archive")
SAFE_ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")

def _now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def _copy(v): return json.loads(json.dumps(v))
def _digest(v): return "sha256:"+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _key(v): return hashlib.sha256(v.encode()).hexdigest()

class IcmRuntimeError(ValueError): pass
class IcmNotFound(IcmRuntimeError): pass

class IcmRuntime:
    def __init__(self,root:Path|str)->None:
        self.root=Path(root).expanduser().resolve()
    def _under(self,path:Path)->Path:
        resolved=path.resolve()
        try: resolved.relative_to(self.root)
        except ValueError as exc: raise IcmRuntimeError("ICM path escaped configured root") from exc
        return resolved
    @staticmethod
    def _id(v:str,name:str)->str:
        if not isinstance(v,str) or not SAFE_ID.fullmatch(v): raise IcmRuntimeError(f"invalid {name}")
        return v
    def _project_root(self,t,p):
        self._id(t,"tenant_id"); self._id(p,"project_id")
        return self._under(self.root/"tenants"/_key(t)/"projects"/_key(p))
    def _run_root(self,t,p,r): return self._under(self._project_root(t,p)/"runs"/self._id(r,"run_id"))
    def _stage_root(self,t,p,r,s):
        if s not in STAGES: raise IcmRuntimeError("invalid stage_id")
        return self._under(self._run_root(t,p,r)/s)
    @staticmethod
    def _write(path:Path,payload:dict):
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=".icm.",suffix=".tmp",dir=path.parent)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h: json.dump(payload,h,indent=2,sort_keys=True); h.write("\n"); h.flush(); os.fsync(h.fileno())
            os.chmod(tmp,0o600); os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    @staticmethod
    def _read(path:Path):
        if not path.is_file(): raise IcmNotFound("ICM record not found")
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise IcmRuntimeError("ICM record is unreadable") from exc
        if not isinstance(data,dict): raise IcmRuntimeError("ICM record must be an object")
        return data

    def create_workspace(self,*,tenant_id:str,project_id:str)->dict[str,Any]:
        root=self._project_root(tenant_id,project_id); root.mkdir(parents=True,exist_ok=True)
        path=root/"workspace.json"
        payload={"schemaVersion":"2.0.0","tenantId":tenant_id,"projectId":project_id,"storageKey":root.name,"factoryId":"yappy-clipz-studio","factoryVersion":"2.0.0","createdAt":_now()}
        if path.exists():
            current=self._read(path)
            if current.get("tenantId")!=tenant_id or current.get("projectId")!=project_id: raise IcmRuntimeError("workspace identity mismatch")
            return current
        self._write(path,payload); return payload

    def create_run(self,*,tenant_id:str,project_id:str,actor_id:str|None=None,correlation_id:str|None=None,parent_run_id:str|None=None,run_id:str|None=None)->dict[str,Any]:
        self.create_workspace(tenant_id=tenant_id,project_id=project_id)
        rid=self._id(run_id or f"run_{uuid4().hex}","run_id"); root=self._run_root(tenant_id,project_id,rid)
        if root.exists(): return self.get_run(tenant_id=tenant_id,project_id=project_id,run_id=rid)
        now=_now(); root.mkdir(parents=True)
        run={"schemaVersion":"2.0.0","runId":rid,"tenantId":tenant_id,"projectId":project_id,"projectSchemaVersion":"1.0.0","factoryId":"yappy-clipz-studio","factoryVersion":"2.0.0","status":"active","currentStage":"00_intake","createdAt":now,"updatedAt":now,"createdBy":{"actorId":actor_id,"type":"human_or_agent"},"correlationId":correlation_id or f"corr_{uuid4().hex}","parentRunId":parent_run_id,"resumeFromRunId":None}
        self._write(root/"run.json",run)
        for name,default in (("artifacts.json",{"artifacts":[]}), ("approvals.json",{"approvals":[]}), ("costs.json",{"currency":"USD","entries":[]}), ("blockers.json",{"blockers":[]})): self._write(root/name,{"schemaVersion":"2.0.0",**default})
        (root/"evidence").mkdir(); (root/"logs").mkdir(); (root/"events.ndjson").touch(mode=0o600)
        for stage in STAGES:
            sr=root/stage
            for d in (sr/"input"/"refs",sr/"output"/"summaries",sr/"evidence",sr/"logs"): d.mkdir(parents=True)
            (sr/"CONTEXT.md").write_text("# Stage context\n\nObjective, constraints, canonical refs, approvals, blockers, and expected outputs.\n",encoding="utf-8")
            (sr/"CHECKLIST.md").write_text("# Stage checklist\n\n- [ ] Inputs bound by stable refs and digests\n- [ ] Constraints preserved\n- [ ] Verification evidence recorded\n- [ ] Handoff written after verification\n",encoding="utf-8")
            self._write(sr/"state.json",{"schemaVersion":"2.0.0","stageId":stage,"status":"pending","attempt":0,"updatedAt":now})
        return run

    def get_run(self,*,tenant_id:str,project_id:str,run_id:str):
        run=self._read(self._run_root(tenant_id,project_id,run_id)/"run.json")
        if run.get("tenantId")!=tenant_id or run.get("projectId")!=project_id: raise IcmNotFound("ICM run not found")
        return run
    def get_stage(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id)
        result={"state":self._read(root/"state.json")}
        for name,key in (("CONTRACT.json","contract"),("input/manifest.json","inputManifest"),("output/manifest.json","outputManifest"),("handoff.json","handoff")):
            if (root/name).is_file(): result[key]=self._read(root/name)
        return result

    def _set_stage(self,t,p,r,s):
        path=self._run_root(t,p,r)/"run.json"; run=self._read(path); run.update(currentStage=s,updatedAt=_now()); self._write(path,run)
    def prepare_stage(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str,input_refs:list[dict[str,Any]],allowed_action_ids:list[str],required_scopes:list[str]|None=None,risk_ceiling:str="medium",max_context_tokens:int=8000):
        self.get_run(tenant_id=tenant_id,project_id=project_id,run_id=run_id); root=self._stage_root(tenant_id,project_id,run_id,stage_id); now=_now()
        if not isinstance(input_refs,list) or not all(isinstance(x,dict) for x in input_refs): raise IcmRuntimeError("input_refs must be a list of objects")
        if not isinstance(allowed_action_ids,list) or not allowed_action_ids: raise IcmRuntimeError("allowed_action_ids are required")
        manifest={"schemaVersion":"2.0.0","stageId":stage_id,"preparedAt":now,"refs":_copy(input_refs),"digest":_digest(input_refs)}
        contract={"schemaVersion":"2.0.0","stageId":stage_id,"stageVersion":"1.0.0","allowedActionIds":sorted(set(allowed_action_ids)),"requiredScopes":sorted(set(required_scopes or [])),"requiredInputKinds":sorted({str(x.get('kind')) for x in input_refs if x.get('kind')}),"requiredOutputKinds":[],"humanApproval":"by_action_policy","maxContextTokens":int(max_context_tokens),"riskCeiling":risk_ceiling,"verify":["input_digests_match","declared_checks_pass"]}
        self._write(root/"input"/"manifest.json",manifest); self._write(root/"CONTRACT.json",contract)
        state=self._read(root/"state.json"); state.update(status="ready",attempt=int(state.get("attempt",0))+1,updatedAt=now,inputDigest=manifest["digest"]); self._write(root/"state.json",state); self._set_stage(tenant_id,project_id,run_id,stage_id)
        return {"contract":contract,"inputManifest":manifest,"state":state}
    def start_stage(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id); state=self._read(root/"state.json")
        if state.get("status") not in {"ready","blocked","failed","stale"}: raise IcmRuntimeError("stage is not ready to start")
        state.update(status="running",startedAt=_now(),updatedAt=_now()); self._write(root/"state.json",state); return state
    def verify_stage(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str,outputs:list[dict[str,Any]],verification:list[dict[str,Any]]):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id); inputs=self._read(root/"input"/"manifest.json")
        if inputs.get("digest")!=_digest(inputs.get("refs",[])): raise IcmRuntimeError("stage input digest is stale or corrupted")
        if not isinstance(outputs,list) or not all(isinstance(x,dict) for x in outputs): raise IcmRuntimeError("outputs must be a list of objects")
        if not isinstance(verification,list) or not verification or any(not isinstance(x,dict) or x.get("status")!="passed" for x in verification): raise IcmRuntimeError("all declared verification checks must pass")
        now=_now(); out={"schemaVersion":"2.0.0","stageId":stage_id,"producedAt":now,"outputs":_copy(outputs),"digest":_digest(outputs)}
        self._write(root/"output"/"manifest.json",out); self._write(root/"evidence"/"verification.json",{"schemaVersion":"2.0.0","checks":_copy(verification),"verifiedAt":now})
        state=self._read(root/"state.json"); state.update(status="verified",verifiedAt=now,updatedAt=now,outputDigest=out["digest"]); self._write(root/"state.json",state)
        return {"state":state,"outputManifest":out,"verification":verification}
    def handoff_stage(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str,actor:dict[str,Any]|None=None,action_ids:list[str]|None=None,decision_ids:list[str]|None=None,approval_ids:list[str]|None=None,job_ids:list[str]|None=None,event_ids:list[str]|None=None,artifact_ids:list[str]|None=None,blockers:list[dict[str,Any]]|None=None,warnings:list[str]|None=None,next_stage_id:str|None=None):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id); state=self._read(root/"state.json")
        if state.get("status")!="verified": raise IcmRuntimeError("stage must be verified before handoff")
        if next_stage_id is not None and next_stage_id not in STAGES: raise IcmRuntimeError("invalid next_stage_id")
        inputs,out=self._read(root/"input"/"manifest.json"),self._read(root/"output"/"manifest.json"); now=_now()
        handoff={"schemaVersion":"2.0.0","handoffId":f"handoff_{uuid4().hex}","runId":run_id,"tenantId":tenant_id,"projectId":project_id,"stageId":stage_id,"stageVersion":"1.0.0","status":"verified","attempt":state.get("attempt",1),"startedAt":state.get("startedAt"),"completedAt":now,"actor":_copy(actor or {"actorId":None,"type":"unknown","client":"unknown","model":"unknown"}),"actionIds":sorted(set(action_ids or [])),"inputRefs":inputs.get("refs",[]),"inputDigest":inputs.get("digest"),"outputRefs":out.get("outputs",[]),"outputDigest":out.get("digest"),"decisionIds":decision_ids or [],"approvalIds":approval_ids or [],"jobIds":job_ids or [],"eventIds":event_ids or [],"artifactIds":artifact_ids or [],"cost":{"estimated":None,"actual":None,"currency":"USD"},"verification":self._read(root/"evidence"/"verification.json").get("checks",[]),"blockers":blockers or [],"warnings":warnings or [],"next":{"recommendedStageId":next_stage_id,"contextRefs":out.get("outputs",[]),"requiredApprovalIds":[]},"resume":{"safe":not bool(blockers),"staleIfRefsChange":inputs.get("refs",[])}}
        self._write(root/"handoff.json",handoff); state.update(status="handed_off",handedOffAt=now,updatedAt=now,handoffId=handoff["handoffId"]); self._write(root/"state.json",state); return handoff
    def mark_stage_stale(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str,reason:str):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id); state=self._read(root/"state.json"); state.update(status="stale",staleReason=str(reason),updatedAt=_now()); self._write(root/"state.json",state); return state
    def resume_run(self,*,tenant_id:str,project_id:str,run_id:str,actor_id:str|None=None):
        path=self._run_root(tenant_id,project_id,run_id)/"run.json"; run=self.get_run(tenant_id=tenant_id,project_id=project_id,run_id=run_id)
        if run.get("status") in {"archived","cancelled","superseded"}: raise IcmRuntimeError("run is not resumable")
        stage=self.get_stage(tenant_id=tenant_id,project_id=project_id,run_id=run_id,stage_id=run["currentStage"]); run.update(status="active",resumeFromRunId=run_id,resumedBy=actor_id,updatedAt=_now()); self._write(path,run); return {"run":run,"currentStage":stage}
    def compile_context(self,*,tenant_id:str,project_id:str,run_id:str,stage_id:str):
        root=self._stage_root(tenant_id,project_id,run_id,stage_id); contract=self._read(root/"CONTRACT.json"); inputs=self._read(root/"input"/"manifest.json"); files=["CONTEXT.md","CONTRACT.json","input/manifest.json"]
        if (root/"handoff.json").is_file(): files.append("handoff.json")
        package={"contextPackageId":f"ctx_{uuid4().hex}","stageId":stage_id,"maxContextTokens":contract.get("maxContextTokens"),"files":files,"capabilityIds":contract.get("allowedActionIds",[]),"inputDigest":inputs.get("digest")}; package["digest"]=_digest(package); return package
    def resolve_artifact(self,*,tenant_id:str,project_id:str,run_id:str,relative_path:str):
        if not isinstance(relative_path,str) or not relative_path or relative_path.startswith(("/","~")): raise IcmRuntimeError("relative_path is invalid")
        run=self._run_root(tenant_id,project_id,run_id); target=self._under(run/relative_path)
        try: target.relative_to(run)
        except ValueError as exc: raise IcmRuntimeError("artifact path escaped run root") from exc
        if target.is_symlink() or not target.is_file(): raise IcmNotFound("artifact not found")
        data=target.read_bytes(); return {"runId":run_id,"relativePath":str(target.relative_to(run)),"size":len(data),"digest":"sha256:"+hashlib.sha256(data).hexdigest()}
