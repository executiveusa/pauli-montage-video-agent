"use client";

import { FormEvent, useMemo, useState } from "react";

type Plan = { generationPlanId:string; capability:string; estimatedCost?:{amount:number|null;currency:string;unit?:string}; route:{chosen?:{providerId:string;modelId:string;reasons:string[]}}; providerPlan:{input:Record<string,unknown>;configured:boolean;executionEnabled:boolean} };
type ActionDocument<T> = { status:string; result:T; job?:unknown };

const choices = [
  ["video.text_to_video","Text to video"],
  ["video.image_to_video","Image to video"],
  ["video.reference_to_video","Reference to video"],
  ["image.generate","Generate image"],
  ["image.edit","Edit image"],
  ["image.inpaint","Inpaint image"],
  ["image.upscale","Upscale image"],
] as const;

export function GenerationWorkbench({ projectId }: { projectId:string }) {
  const [capability,setCapability]=useState("video.text_to_video");
  const [prompt,setPrompt]=useState("");
  const [imageUrl,setImageUrl]=useState("");
  const [duration,setDuration]=useState("8");
  const [resolution,setResolution]=useState("720p");
  const [aspect,setAspect]=useState("16:9");
  const [maxCost,setMaxCost]=useState("3.00");
  const [plan,setPlan]=useState<Plan|null>(null);
  const [result,setResult]=useState<Record<string,unknown>|null>(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [approved,setApproved]=useState(false);

  const providerInput=useMemo(() => {
    const input:Record<string,unknown>={};
    if(prompt.trim()) input.prompt=prompt.trim();
    if(capability.startsWith("video.")){input.duration=duration;input.resolution=resolution;input.aspect_ratio=aspect;input.generate_audio=true;}
    if(imageUrl.trim()){
      if(capability==="video.reference_to_video") input.image_urls=[imageUrl.trim()];
      else input.image_url=imageUrl.trim();
    }
    return input;
  },[aspect,capability,duration,imageUrl,prompt,resolution]);

  async function call<T>(actionId:string, input:Record<string,unknown>, options?:{approved?:boolean;idempotency?:string}):Promise<T>{
    const response=await fetch(`/api/studio/actions/${actionId}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({input,approved:Boolean(options?.approved),idempotency_key:options?.idempotency})});
    const payload=await response.json();
    if(!response.ok || payload.status==="failed") throw new Error(payload.message||payload.detail||payload.error||"Studio action failed");
    return (payload as ActionDocument<T>).result;
  }

  async function preview(event:FormEvent){event.preventDefault();setBusy(true);setError("");setResult(null);setApproved(false);
    try{const next=await call<Plan>("generation.plan",{projectId,capability,providerInput,qualityLane:"economy",privacyLane:"cloud",maxCost:Number(maxCost)});setPlan(next);}catch(reason){setPlan(null);setError(reason instanceof Error?reason.message:"Planning failed");}finally{setBusy(false);}}
  async function submit(){if(!plan||!approved)return;setBusy(true);setError("");
    try{const idempotency=crypto.randomUUID();const submitted=await call<Record<string,unknown>>(capability,{projectId,providerInput,qualityLane:"economy",privacyLane:"cloud",maxCost:Number(maxCost),budgetLimit:Number(maxCost)}, {approved:true,idempotency});setResult(submitted);}catch(reason){setError(reason instanceof Error?reason.message:"Submission failed");}finally{setBusy(false);}}

  return <div className="generation-shell">
    <header className="generation-header"><div><span className="generation-kicker">Create workbench</span><h1>Plan first. Spend second.</h1><p>One neutral request is routed to a replaceable model, costed, approved, queued, and traced back to this project.</p></div><span className="generation-project">{projectId}</span></header>
    <div className="generation-grid">
      <form className="generation-panel generation-form" onSubmit={preview}>
        <label>Capability<select value={capability} onChange={event=>{setCapability(event.target.value);setPlan(null);}}>{choices.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        <label>Prompt<textarea required={!capability.includes("upscale")} rows={7} value={prompt} onChange={event=>setPrompt(event.target.value)} placeholder="Describe the shot, edit, or visual outcome." /></label>
        <label>Public reference URL<input type="url" value={imageUrl} onChange={event=>setImageUrl(event.target.value)} placeholder="https://…" /></label>
        <div className="generation-fields"><label>Duration<select value={duration} onChange={event=>setDuration(event.target.value)}><option>4</option><option>8</option><option>12</option><option>15</option></select></label><label>Resolution<select value={resolution} onChange={event=>setResolution(event.target.value)}><option>480p</option><option>720p</option></select></label><label>Aspect<select value={aspect} onChange={event=>setAspect(event.target.value)}><option>16:9</option><option>9:16</option><option>1:1</option></select></label></div>
        <label>Hard cost ceiling (USD)<input type="number" min="0" step="0.01" value={maxCost} onChange={event=>setMaxCost(event.target.value)} /></label>
        <button className="generation-primary" disabled={busy}>{busy?"Checking…":"Preview route and cost"}</button>
      </form>
      <section className="generation-panel generation-review" aria-live="polite">
        <div className="generation-section-title"><span>Execution review</span><span>{plan?"Ready to review":"Not planned"}</span></div>
        {!plan?<div className="generation-empty">No provider request exists yet. Planning never spends credits.</div>:<>
          <dl><div><dt>Provider</dt><dd>{plan.route.chosen?.providerId||"None"}</dd></div><div><dt>Model</dt><dd>{plan.route.chosen?.modelId||"Unavailable"}</dd></div><div><dt>Estimate</dt><dd>{plan.estimatedCost?.amount==null?"Unknown":`${plan.estimatedCost.currency} $${plan.estimatedCost.amount.toFixed(4)}`}</dd></div><div><dt>Server gate</dt><dd>{plan.providerPlan.configured&&plan.providerPlan.executionEnabled?"Enabled":"Locked"}</dd></div></dl>
          <details><summary>Exact provider payload</summary><pre>{JSON.stringify(plan.providerPlan.input,null,2)}</pre></details>
          <label className="generation-approval"><input type="checkbox" checked={approved} onChange={event=>setApproved(event.target.checked)} />I reviewed the route, payload, and maximum cost and approve this paid request.</label>
          <button type="button" className="generation-primary" disabled={busy||!approved||plan.estimatedCost?.amount==null} onClick={submit}>Approve and queue</button>
        </>}
        {error&&<div className="generation-error">{error}</div>}
        {result&&<details open><summary>Job receipt</summary><pre>{JSON.stringify(result,null,2)}</pre></details>}
      </section>
    </div>
  </div>;
}
