"""Explainable provider/model routing and cost estimation."""
from __future__ import annotations
from typing import Any
from uuid import uuid4
from .providers import ProviderCatalog
from .operations import OperationError


class OmniRouter:
    def __init__(self,catalog:ProviderCatalog)->None:self.catalog=catalog
    @staticmethod
    def estimate_model(model:dict[str,Any],payload:dict[str,Any])->dict[str,Any]:
        pricing=model.get("pricing") or {};currency=pricing.get("currency","USD");unit=pricing.get("unit")
        if unit=="second":
            duration=payload.get("duration",payload.get("durationSeconds",8));duration=8 if duration=="auto" else float(duration);resolution=payload.get("resolution",model.get("defaults",{}).get("resolution","720p"));rate=(pricing.get("ratesPerSecondUsd") or {}).get(resolution)
            amount=duration*float(rate) if rate is not None else None
        else:amount=None
        return {"amount":round(amount,6) if amount is not None else None,"currency":currency,"unit":unit,"pricingVerifiedAt":pricing.get("verifiedAt"),"pricingSource":pricing.get("source")}
    def plan(self,*,capability:str,payload:dict[str,Any],quality_lane:str="economy",max_cost:float|None=None,preferred_provider:str|None=None,privacy_lane:str="cloud",allow_experimental:bool=True)->dict[str,Any]:
        candidates=[]
        for summary in self.catalog.list():
            provider=self.catalog.get(summary["providerId"])
            if preferred_provider and provider["providerId"]!=preferred_provider:continue
            for model in provider.get("models",[]):
                if capability not in model.get("capabilities",[]):continue
                if not allow_experimental and model.get("lifecycle")!="stable":continue
                estimate=self.estimate_model(model,payload);amount=estimate["amount"]
                reasons=[];score=100.0
                if max_cost is not None and amount is not None and amount>max_cost:reasons.append("over_cost_ceiling");score-=1000
                fast=bool(model.get("fastTier"));
                if quality_lane=="economy":score+=20 if fast else 0;reasons.append("economy_prefers_fast" if fast else "standard_quality")
                elif quality_lane=="premium":score+=20 if not fast else -5;reasons.append("premium_prefers_standard" if not fast else "fast_tradeoff")
                if amount is not None:score-=amount
                if privacy_lane in {"sovereign","owner_private"}:score-=500;reasons.append("cloud_provider_conflicts_with_privacy_lane")
                candidates.append({"routeId":f"route_{provider['providerId']}_{model['modelId'].replace('/','_')}","providerId":provider["providerId"],"modelId":model["modelId"],"capability":capability,"score":round(score,4),"estimate":estimate,"reasons":reasons,"eligible":score>-500})
        ranked=sorted(candidates,key=lambda x:(x["eligible"],x["score"]),reverse=True)
        chosen=next((c for c in ranked if c["eligible"]),None)
        return {"planId":f"rplan_{uuid4().hex[:24]}","capability":capability,"qualityLane":quality_lane,"privacyLane":privacy_lane,"maxCost":max_cost,"chosen":chosen,"candidates":ranked,"requiresApproval":bool(chosen and chosen["estimate"]["amount"] not in {None,0})}
    def explain(self,plan:dict[str,Any])->dict[str,Any]:
        chosen=plan.get("chosen")
        if not chosen:return {"summary":"No eligible route satisfies the declared capability, privacy, lifecycle, and cost policies.","plan":plan}
        return {"summary":f"Selected {chosen['providerId']} / {chosen['modelId']} with score {chosen['score']}.","estimate":chosen["estimate"],"reasons":chosen["reasons"],"alternatives":len(plan.get("candidates",[]))-1,"plan":plan}
