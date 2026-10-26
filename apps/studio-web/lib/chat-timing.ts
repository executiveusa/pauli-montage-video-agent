/** Exact bounded commands, not general-purpose language understanding. */
export function parseChatSeconds(raw:string):number|null {
  if(/^\d{1,2}:\d{2}(?::\d{2})?$/.test(raw)){
    const parts=raw.split(":").map(Number);
    if(parts.slice(1).some(n=>n>=60))return null;
    return parts.reduce((total,n)=>total*60+n,0);
  }
  if(!/^\d+(?:\.\d+)?$/.test(raw))return null;
  const n=Number(raw);return Number.isFinite(n)?n:null;
}
export function matchChatTime(prompt:string,kind:"trim"|"split"):{seconds:number|null}|null {
  const prefix=kind==="trim"?"(?:trim|shorten|make|cut)\\s+(?:the\\s+video\\s+)?(?:to|down to|at)":"split\\s+(?:the\\s+video\\s+)?(?:at|after)";
  const match=prompt.match(new RegExp(`\\b${prefix}\\s+(\\d{1,2}:\\d{2}(?::\\d{2})?|\\d+(?:\\.\\d+)?)(?![\\d:.])`,"i"));
  return match?{seconds:parseChatSeconds(match[1])}:null;
}
