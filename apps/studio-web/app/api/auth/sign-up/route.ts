import { NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";
import { sessionCookieName, studioSessionConfigured } from "@/lib/studio-session";

const redirect = (path: string) => new NextResponse(null,{status:303,headers:{Location:path}});

export async function POST(request: Request) {
  if (!studioSessionConfigured()) return redirect("/sign-up?error=service");
  const form=await request.formData();const base=studioApiBaseUrl();if(!base)return redirect("/sign-up?error=service");
  try {
    const upstream=await fetch(`${base}/api/v1/accounts`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({email:String(form.get("email")||""),password:String(form.get("password")||""),display_name:String(form.get("displayName")||"")}),cache:"no-store"});
    const body=await upstream.json().catch(()=>({}));if(!upstream.ok||typeof body.accessToken!=="string")return redirect(`/sign-up?error=${upstream.status===409?"conflict":"invalid"}`);
    const response=redirect("/studio/new");response.cookies.set(sessionCookieName(),body.accessToken,{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:Math.max(60,Number(body.expiresAt)-Math.floor(Date.now()/1000))});return response;
  } catch { return redirect("/sign-up?error=service"); }
}
