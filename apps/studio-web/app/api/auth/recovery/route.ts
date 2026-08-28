import { NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";

const redirect=(path:string)=>new NextResponse(null,{status:303,headers:{Location:path}});
export async function POST(request:Request){const form=await request.formData();const base=studioApiBaseUrl();if(!base)return redirect("/recovery?error=service");try{const response=await fetch(`${base}/api/v1/accounts/recovery`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({email:String(form.get("email")||"")}),cache:"no-store"});return response.ok?redirect("/recovery?sent=1"):redirect("/recovery?error=service");}catch{return redirect("/recovery?error=service");}}
