// Private Sites adapter; all project state and permission decisions stay in Montage.
const UPSTREAM = 'https://montage-staging.2.25.241.209.sslip.io';
const schema = properties => ({type:'object',properties,additionalProperties:false});
const string = {type:'string'};
const tools = [
 {name:'montage_connection_status',description:'Check this private plugin connection and whether an owner-scoped Studio token has been configured. Does not read projects.',inputSchema:schema({}),annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}},
 {name:'montage_capabilities',description:'Discover the connected Montage actions and their actual readiness.',inputSchema:schema({}),annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}},
 {name:'montage_describe_action',description:'Read action input, scope, approval and idempotency requirements before calling it.',inputSchema:{...schema({action_id:string}),required:['action_id']},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}},
 {name:'montage_projects',description:'List projects in the workspace authorized by the configured token.',inputSchema:schema({}),annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}},
 {name:'montage_action',description:'Invoke an existing Montage action. Describe its contract first. Obtain explicit human approval before approved=true. Use stable idempotency keys for mutations/retries. May edit, render or incur provider charges under the backend approval contract.',inputSchema:{...schema({action_id:string,input:{type:'object'},approved:{type:'boolean',default:false},idempotency_key:string}),required:['action_id','input']},annotations:{readOnlyHint:false,destructiveHint:true,openWorldHint:true}}
];
const json = (value,status=200) => Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const content = (value,isError=false) => ({content:[{type:'text',text:JSON.stringify(value)}],isError});
export async function runTool(name,args,request,env,fetcher=fetch){
 const user=request.headers.get('oai-authenticated-user-id');
 if(!user) return content({error:'authentication_required',message:'Open this private plugin through your signed-in ChatGPT account.'},true);
 const token=env.MONTAGE_STUDIO_TOKEN;
 if(name==='montage_connection_status') return content({plugin:'Montage Studio Agent',workspace:'isolated staging',studioOrigin:UPSTREAM,authenticated:true,tokenConfigured:!!token,ownerBindingConfigured:!!env.MONTAGE_OWNER_EMAIL,studioConnected:null,configuration:token?'Token configured; capabilities/readiness require a live call.':'An owner-scoped Montage service token must be added to the private plugin runtime as MONTAGE_STUDIO_TOKEN. Never put it in chat.',sourcePreservation:'All edits use the existing StudioProject action API.'});
 // Bind service-token use to the verified owner identity, even if Site sharing changes later.
 if(!env.MONTAGE_OWNER_EMAIL || request.headers.get('oai-authenticated-user-email')?.toLowerCase()!==env.MONTAGE_OWNER_EMAIL.toLowerCase()) return content({error:'owner_binding_required',message:'Configure MONTAGE_OWNER_EMAIL for the private plugin owner before accessing a Studio workspace.'},true);
 if(!token || !/^[A-Za-z0-9._~-]{32,8192}$/.test(token)) return content({error:'studio_connection_required',message:'Connect the private plugin to Montage with an owner-scoped service token in hosted settings. No credentials belong in chat.'},true);
 let action,input={},approved=false,idempotency_key;
 if(name==='montage_capabilities') action='capabilities.list';
 else if(name==='montage_describe_action'){action='capabilities.describe';input={actionId:args.action_id};}
 else if(name==='montage_projects') action='project.list';
 else if(name==='montage_action'){action=args.action_id;input=args.input;approved=args.approved??false;idempotency_key=args.idempotency_key;}
 else return content({error:'unknown_tool'},true);
 if(!/^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/.test(action??'') || !input || typeof input!=='object' || Array.isArray(input) || 'tenantId' in input || 'tenant_id' in input || typeof approved!=='boolean' || (idempotency_key!==undefined && (typeof idempotency_key!=='string'||idempotency_key.length>200))) return content({error:'invalid_request'},true);
 try{
  const response=await fetcher(`${UPSTREAM}/api/studio/actions/${encodeURIComponent(action)}`,{method:'POST',headers:{'content-type':'application/json',cookie:`yappy_studio_session=${token}`},body:JSON.stringify({input,approved,...(idempotency_key?{idempotency_key}:{})}),redirect:'error',signal:AbortSignal.timeout(8000),cache:'no-store'});
  if(!response.ok) return content({error:response.status===401?'authentication_required':response.status===403?'authorization_denied':'studio_action_failed',status:response.status,message:'Inspect the action contract and current saved state before retrying. Reuse the same idempotency key after an uncertain mutation.'},true);
  return content(await response.json());
 }catch{return content({error:'studio_unavailable',message:'The existing Studio gateway did not complete the request. Inspect state before retrying; keep the same idempotency key.'},true);}
}
const page = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Montage Studio Agent</title><style>body{margin:0;background:#11110f;color:#efede4;font:18px/1.6 system-ui,sans-serif}main{max-width:720px;margin:10vh auto;padding:32px}h1{font-size:48px;line-height:1.1}a{color:#efede4}section{border-top:1px solid #555;padding-top:24px;margin-top:32px}code{font-size:14px;overflow-wrap:anywhere}</style><main><p>MONTAGE · PRIVATE AGENT CONNECTION</p><h1>Your studio, in the conversation.</h1><p>Read your projects, inspect the saved timeline, and request edits or renders through Montage’s existing actions. Originals and project history stay in your studio.</p><section><h2>Connect once</h2><p>This private beta uses your isolated staging workspace. The owner’s Montage service token and verified email must be configured in hosted settings before project access. Keep credentials out of chat.</p><p>After connection, ask: “Show my Montage projects.” Before a consequential action, the agent must describe the change and obtain your approval.</p></section><section><h2>Current boundaries</h2><p>Browser-local projects remain on that browser and are not visible to this server plugin. Hosted tools enforce the token’s workspace and scopes. Missing renderer services remain unavailable.</p><p><a href="https://montage-staging.2.25.241.209.sslip.io/sign-in" rel="noreferrer">Open the staging studio</a></p></section></main></html>`;
export default {async fetch(request,env){
 const path=new URL(request.url).pathname;
 if(path==='/mcp' && request.method==='POST'){
  if(Number(request.headers.get('content-length')||0)>1048576) return json({error:'request_too_large'},413);
  let body;try{
   const reader=request.body?.getReader();const chunks=[];let size=0;
   if(reader){while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>1048576){await reader.cancel();return json({error:'request_too_large'},413);}chunks.push(value);}}
   const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
   body=JSON.parse(new TextDecoder().decode(bytes));
  }catch{return json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Invalid JSON'}},400);} 
  const id=body?.id??null;
  if(body?.method==='notifications/initialized' && body?.jsonrpc==='2.0' && body.id===undefined)return new Response(null,{status:202});
  if(!(typeof id==='string'||(typeof id==='number'&&Number.isFinite(id))))return json({jsonrpc:'2.0',id:null,error:{code:-32600,message:'A request requires a string or finite numeric ID'}},400);
  if(body?.jsonrpc!=='2.0')return json({jsonrpc:'2.0',id,error:{code:-32600,message:'Invalid request'}},400);
  let result;
  if(body.method==='server/discover')result={supportedVersions:['2026-07-28'],capabilities:{tools:{}}};
  else if(body.method==='initialize')result={protocolVersion:'2026-07-28',capabilities:{tools:{}},serverInfo:{name:'montage-studio-agent',version:'0.1.0'}};
  else if(body.method==='notifications/initialized')return new Response(null,{status:202});
  else if(body.method==='tools/list')result={tools};
  else if(body.method==='tools/call')result=await runTool(body.params?.name,body.params?.arguments??{},request,env);
  else return json({jsonrpc:'2.0',id,error:{code:-32601,message:'Method not found'}},404);
  return json({jsonrpc:'2.0',id,result});
 }
 if(path==='/' && request.method==='GET')return new Response(page,{headers:{'content-type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self' https://chatgpt.com"}});
 return new Response('Not found',{status:404});
}};
