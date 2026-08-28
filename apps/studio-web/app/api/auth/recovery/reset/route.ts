import { NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";

const redirect=(path:string)=>new NextResponse(null,{status:303,headers:{Location:path}});
export async function POST(request:Request){const form=await request.formData();const token=String(form.get("token")||"");const base=studioApiBaseUrl();if(!base)return redirect(`/recovery/reset?token=${encodeURIComponent(token)}&error=service`);try{const response=await fetch(`${base}/api/v1/accounts/recovery/reset`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({token,password:String(form.get("password")||"")}),cache:"no-store"});return response.ok?redirect("/sign-in"):redirect(`/recovery/reset?token=${encodeURIComponent(token)}&error=token`);}catch{return redirect(`/recovery/reset?token=${encodeURIComponent(token)}&error=service`);}}
