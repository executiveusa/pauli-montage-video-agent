import assert from "node:assert/strict";
import test from "node:test";
import { createMontageBridge, handleMontageMcp } from "./montage-mcp";

const tokenA = "a".repeat(48);
const tokenB = "b".repeat(48);
function request(body: unknown, token?: string, origin?: string) {
  return new Request("https://montage.example/api/mcp", {method:"POST", headers:{"content-type":"application/json",accept:"application/json, text/event-stream",...(token?{authorization:`Bearer ${token}`} : {}),...(origin?{origin}:{})},body:JSON.stringify(body)});
}
const call = (name: string, args = {}) => ({jsonrpc:"2.0",id:1,method:"tools/call",params:{name,arguments:args}});

test("real SDK transport initializes and discovers the 11 stable tools",async()=>{
  const r = await handleMontageMcp(request({jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2025-03-26",capabilities:{},clientInfo:{name:"acceptance",version:"1"}}}));
  assert.equal(r.status,200); assert.equal((await r.json()).result.serverInfo.name,"montage");
  const d = await handleMontageMcp(request({jsonrpc:"2.0",id:2,method:"tools/list"}));
  const tools = (await d.json()).result.tools;
  assert.equal(tools.length,11);
  assert.equal(tools.find((t: {name:string})=>t.name==="timeline_get").annotations.readOnlyHint,true);
  assert.equal(tools.find((t: {name:string})=>t.name==="action_run").annotations.destructiveHint,true);
});

test("missing token cannot trigger any upstream operation",async()=>{
  let calls=0;
  const r=await handleMontageMcp(request(call("project_list")),{fetcher:async()=>{calls++;throw new Error("must not fetch");}});
  const payload=await r.json(); assert.equal(payload.result.isError,true);
  assert.match(payload.result.content[0].text,/authentication_required/);assert.equal(calls,0);
});

test("direct gateway forwards only caller token and approved/idempotency intent",async()=>{
  let seen: {url:string;init:RequestInit}|undefined;
  const invoke=createMontageBridge(request({},tokenA),{apiBase:"http://studio-api:8000",fetcher:async(url,init)=>{seen={url:String(url),init:init!};return Response.json({result:{version:2}});}});
  await invoke("timeline.replace",{projectId:"p",expectedVersion:1,timeline:{}},{idempotency_key:"same-key"});
  assert.equal(seen!.url,"http://studio-api:8000/api/v1/actions/timeline.replace");
  assert.equal((seen!.init.headers as Record<string,string>).authorization,`Bearer ${tokenA}`);
  assert.equal((seen!.init.headers as Record<string,string>).cookie,undefined);
  assert.deepEqual(JSON.parse(seen!.init.body as string),{input:{projectId:"p",expectedVersion:1,timeline:{}},approved:false,idempotency_key:"same-key"});
  assert.equal(seen!.init.redirect,"error");assert.equal(seen!.init.cache,"no-store");
});

test("isolated beta fallback uses existing authenticated cookie gateway",async()=>{
  let seen:RequestInit|undefined;
  const invoke=createMontageBridge(request({},tokenA),{fetcher:async(url,init)=>{assert.equal(String(url),"https://montage-staging.2.25.241.209.sslip.io/api/studio/actions/project.list");seen=init;return Response.json({result:[]});}});
  await invoke("project.list");assert.equal((seen!.headers as Record<string,string>).cookie,`yappy_studio_session=${tokenA}`);
});

test("overlapping calls never exchange caller credentials",async()=>{
  const tokens:string[]=[];
  const fetcher:typeof fetch=async(_url,init)=>{tokens.push((init!.headers as Record<string,string>).authorization);await Promise.resolve();return Response.json({result:[]});};
  const a=createMontageBridge(request({},tokenA),{apiBase:"http://api:8000",fetcher});
  const b=createMontageBridge(request({},tokenB),{apiBase:"http://api:8000",fetcher});
  await Promise.all([a("project.list"),b("project.list")]);assert.deepEqual(tokens,[`Bearer ${tokenA}`,`Bearer ${tokenB}`]);
});

test("tenant override and path injection are rejected before dispatch",async()=>{
  let calls=0;
  const invoke=createMontageBridge(request({},tokenA),{fetcher:async()=>{calls++;return Response.json({});}});
  assert.equal(JSON.parse((await invoke("project.list",{tenantId:"victim"})).content[0].text).error,"invalid_request");
  assert.equal(JSON.parse((await invoke("../tokens")).content[0].text).error,"invalid_action");
  assert.equal(calls,0);
});

test("upstream credential/tenant errors never echo submitted values",async()=>{
  for(const status of [401,403,409,422,500]){
    const invoke=createMontageBridge(request({},tokenA),{fetcher:async()=>Response.json({detail:{password:"NEVER-ECHO",token:tokenA}},{status})});
    const response=await invoke("project.list");assert.equal(response.isError,true);const text=response.content[0].text;
    assert.doesNotMatch(text,/NEVER-ECHO/);assert.ok(!text.includes(tokenA));
  }
});

test("timeouts/network failures are sanitized and do not automatically retry",async()=>{
  let calls=0;
  const invoke=createMontageBridge(request({},tokenA),{fetcher:async()=>{calls++;throw new Error(tokenA);}});
  const response=await invoke("render.submit",{}, {idempotency_key:"durable-key"});
  assert.equal(calls,1);assert.ok(!response.content[0].text.includes(tokenA));assert.match(response.content[0].text,/same idempotency key/);
});

test("SDK tool save maps exact optimistic version; approval is explicit",async()=>{
  let sent:Record<string,unknown>|undefined;
  const r=await handleMontageMcp(request(call("timeline_replace",{project_id:"p",expected_version:7,timeline:{tracks:[]}}),tokenA),{fetcher:async(_url,init)=>{sent=JSON.parse(init!.body as string);return Response.json({result:{version:8}});}});
  assert.equal(r.status,200);assert.deepEqual(sent!.input,{projectId:"p",expectedVersion:7,timeline:{tracks:[]}});assert.equal(sent!.approved,false);
});

test("cross-origin browser calls and persistent SSE are not accepted",async()=>{
  assert.equal((await handleMontageMcp(request(call("project_list"),tokenA,"https://evil.example"))).status,403);
  assert.equal((await handleMontageMcp(new Request("https://montage.example/api/mcp"))).status,405);
});
