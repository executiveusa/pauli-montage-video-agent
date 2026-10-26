/** Approximate device-local review copy, never an ffprobe-verified delivery master. */
import type { Timeline } from "@/lib/timeline";
import { getBrowserSource } from "@/lib/browser-source-media";
import { getLocalSourceAsset } from "@/lib/local-studio-store";
import { planBrowserReview } from "./browser-review-plan";

export type BrowserReviewExport = { blob:Blob; filename:string; durationSeconds:number; mimeType:string; withAudio:null };
const WIDTH=540, HEIGHT=960;
const aborted = () => new DOMException("Browser review canceled.", "AbortError");
function check(signal:AbortSignal) { if(signal.aborted) throw aborted(); }
function bounded<T>(promise:Promise<T>, ms:number, signal:AbortSignal, message:string):Promise<T> {
  return new Promise((resolve,reject) => {
    let settled=false;
    const finish=(error?:unknown,value?:T) => {
      if(settled)return;settled=true;clearTimeout(timer);signal.removeEventListener("abort",cancel);
      error ? reject(error) : resolve(value as T);
    };
    const cancel=()=>finish(aborted());
    const timer=setTimeout(()=>finish(new Error(message)),ms);
    signal.addEventListener("abort",cancel,{once:true});
    if(signal.aborted)cancel();
    promise.then(value=>finish(undefined,value),error=>finish(error));
  });
}
function mediaReady(video:HTMLVideoElement, event:string, ready:()=>boolean, signal:AbortSignal):Promise<void> {
  check(signal);
  if(ready())return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const finish=(error?:Error)=>{clearTimeout(timer);video.removeEventListener(event,done);video.removeEventListener("error",fail);signal.removeEventListener("abort",cancel);error?reject(error):resolve();};
    const done=()=>{if(ready())finish();};
    const fail=()=>finish(new Error("Source video could not be decoded."));
    const cancel=()=>finish(aborted());
    const timer=setTimeout(()=>finish(new Error("Video decode or seek timed out.")),15000);
    video.addEventListener(event,done);video.addEventListener("error",fail,{once:true});signal.addEventListener("abort",cancel,{once:true});
    if(signal.aborted)cancel();else done();
  });
}
async function seek(video:HTMLVideoElement, seconds:number, signal:AbortSignal) {
  check(signal);video.pause();
  if(Math.abs(video.currentTime-seconds)>.00001){
    await new Promise<void>((resolve,reject)=>{
      const finish=(error?:Error)=>{clearTimeout(timer);video.removeEventListener("seeked",done);video.removeEventListener("error",fail);signal.removeEventListener("abort",cancel);error?reject(error):resolve();};
      const done=()=>finish();const fail=()=>finish(new Error("Source seek failed."));const cancel=()=>finish(aborted());
      const timer=setTimeout(()=>finish(new Error("Source seek timed out.")),15000);
      video.addEventListener("seeked",done,{once:true});video.addEventListener("error",fail,{once:true});signal.addEventListener("abort",cancel,{once:true});
      try{check(signal);video.currentTime=seconds;}catch(error){finish(error instanceof Error?error:new Error("Source seek failed."));}
    });
  }
  await mediaReady(video,"loadeddata",()=>video.readyState>=2,signal);
}
function recorderTransition(recorder:MediaRecorder, command:"pause"|"resume", signal:AbortSignal) {
  return new Promise<void>((resolve,reject)=>{
    const finish=(error?:Error)=>{clearTimeout(timer);recorder.removeEventListener(command,done);signal.removeEventListener("abort",cancel);error?reject(error):resolve();};
    const done=()=>finish();const cancel=()=>finish(aborted());
    const timer=setTimeout(()=>finish(new Error("Browser recorder transition timed out.")),5000);
    recorder.addEventListener(command,done,{once:true});signal.addEventListener("abort",cancel,{once:true});
    try{check(signal);recorder[command]();}catch(error){finish(error instanceof Error?error:new Error("Recorder failed."));}
  });
}

export async function renderBrowserReview(projectId:string,timeline:Timeline,options:{signal?:AbortSignal}={}):Promise<BrowserReviewExport> {
  if(typeof MediaRecorder==="undefined")throw new Error("Browser recording is unavailable. Use the FFmpeg renderer.");
  const controller=new AbortController();
  const relay=()=>controller.abort();options.signal?.addEventListener("abort",relay,{once:true});
  if(options.signal?.aborted)controller.abort();
  const signal=controller.signal;
  const asset=getLocalSourceAsset(projectId);
  if(!asset){options.signal?.removeEventListener("abort",relay);throw new Error("Import source footage first.");}
  let objectUrl:string|null=null, video:HTMLVideoElement|null=null, stream:MediaStream|null=null, recorder:MediaRecorder|null=null, audio:AudioContext|null=null;
  let playbackFrame=0, recorderFailure:Error|null=null;
  try{
    check(signal);
    const source=await bounded(getBrowserSource(projectId,asset.id),10000,signal,"Browser source storage timed out.");
    if(!source)throw new Error("Source bytes are missing from this browser. Reimport the original footage.");
    objectUrl=URL.createObjectURL(source);video=document.createElement("video");
    video.playsInline=true;video.preload="auto";video.muted=false;video.src=objectUrl;
    await mediaReady(video,"loadedmetadata",()=>video!.readyState>=1,signal);
    const plan=planBrowserReview(timeline,asset.id,video.duration);
    const mimeType=["video/webm;codecs=vp9,opus","video/webm;codecs=vp8,opus","video/webm","video/mp4"].find(type=>MediaRecorder.isTypeSupported(type));
    if(!mimeType)throw new Error("This browser has no supported recording format.");
    const canvas=document.createElement("canvas");canvas.width=WIDTH;canvas.height=HEIGHT;
    const context=canvas.getContext("2d",{alpha:false});
    if(!context||typeof canvas.captureStream!=="function")throw new Error("Canvas video capture is unavailable.");
    const paint=(elapsed:number)=>{
      context.fillStyle="#000";context.fillRect(0,0,WIDTH,HEIGHT);
      if(video!.readyState>=2 && video!.videoWidth && video!.videoHeight){
        const scale=Math.max(WIDTH/video!.videoWidth,HEIGHT/video!.videoHeight),w=video!.videoWidth*scale,h=video!.videoHeight*scale;
        context.drawImage(video!,(WIDTH-w)/2,(HEIGHT-h)/2,w,h);
      }
      for(const overlay of plan.overlays){
        if(elapsed<overlay.start||elapsed>=overlay.end)continue;
        context.textAlign=overlay.role==="lower_third"?"left":"center";context.textBaseline="middle";
        context.font="bold 34px sans-serif";context.lineWidth=6;context.strokeStyle="rgba(0,0,0,.85)";context.fillStyle="white";
        const lines=overlay.text.split("\n"),yBase=HEIGHT*(overlay.role==="caption"?.9:overlay.role==="lower_third"?.78:overlay.role==="episode_marker"?.15:.28),x=overlay.role==="lower_third"?32:WIDTH/2;
        lines.forEach((line,index)=>{const y=yBase+(index-(lines.length-1)/2)*45;context.strokeText(line,x,y,WIDTH-64);context.fillText(line,x,y,WIDTH-64);});
      }
    };
    await seek(video,plan.segments[0].start,signal);
    paint(0); // Decode and paint the first actual source frame before capture begins.
    stream=canvas.captureStream(24);
    if(typeof AudioContext!=="undefined"){
      try{
        audio=new AudioContext();const input=audio.createMediaElementSource(video),destination=audio.createMediaStreamDestination();input.connect(destination);
        for(const track of destination.stream.getAudioTracks())stream.addTrack(track);
        await bounded(audio.resume(),5000,signal,"Audio activation timed out.");
      }catch(error){
        if(signal.aborted)throw error;
        if(audio)void audio.close().catch(()=>undefined);audio=null;
      }
    }
    recorder=new MediaRecorder(stream,{mimeType,videoBitsPerSecond:3_000_000});
    const chunks:Blob[]=[];
    // This promise resolves outcomes instead of rejecting before the caller awaits it.
    const completed=new Promise<{blob?:Blob;error?:Error}>(resolve=>{
      recorder!.addEventListener("dataavailable",(event:BlobEvent)=>{if(event.data.size)chunks.push(event.data);});
      recorder!.addEventListener("error",()=>{recorderFailure=new Error("The browser recorder failed.");resolve({error:recorderFailure});controller.abort();},{once:true});
      recorder!.addEventListener("stop",()=>{const blob=new Blob(chunks,{type:mimeType});resolve(blob.size?{blob}:{error:new Error("The browser produced an empty recording.")});},{once:true});
    });
    recorder.start(500);
    for(let index=0;index<plan.segments.length;index++){
      const segment=plan.segments[index];
      if(index){
        await recorderTransition(recorder,"pause",signal);
        await seek(video,segment.start,signal);paint(segment.outputStart);
        await recorderTransition(recorder,"resume",signal);
      }
      await bounded(video.play(),5000,signal,"Source playback could not start.");
      await new Promise<void>((resolve,reject)=>{
        const finish=(error?:Error)=>{clearTimeout(timer);cancelAnimationFrame(playbackFrame);playbackFrame=0;video!.pause();signal.removeEventListener("abort",cancel);error?reject(error):resolve();};
        const cancel=()=>finish(aborted());
        const timer=setTimeout(()=>finish(new Error("Browser review stalled. Keep the page visible or use FFmpeg.")),Math.ceil((segment.end-segment.start)*2500+10000));
        signal.addEventListener("abort",cancel,{once:true});
        const step=()=>{
          if(signal.aborted){finish(aborted());return;}
          if(video!.ended||video!.currentTime>=segment.end){finish();return;}
          if(video!.currentTime>=segment.start)paint(segment.outputStart+video!.currentTime-segment.start);
          playbackFrame=requestAnimationFrame(step);
        };step();
      });
    }
    check(signal);video.pause();recorder.stop();
    const outcome=await bounded(completed,5000,signal,"The browser recorder did not finish.");
    if(outcome.error||!outcome.blob)throw outcome.error||new Error("No recording was produced.");
    return {blob:outcome.blob,mimeType,durationSeconds:plan.durationSeconds,withAudio:null,filename:`montage-${projectId}-timeline-v${timeline.version}.${mimeType.includes("mp4")?"mp4":"webm"}`};
  }catch(error){throw recorderFailure||error;}
  finally{
    options.signal?.removeEventListener("abort",relay);controller.abort();cancelAnimationFrame(playbackFrame);
    video?.pause();if(video){video.removeAttribute("src");video.load();}
    try{if(recorder&&recorder.state!=="inactive")recorder.stop();}catch{/* recorder failure already reported */}
    stream?.getTracks().forEach(track=>track.stop());
    if(audio)void audio.close().catch(()=>undefined);
    if(objectUrl)URL.revokeObjectURL(objectUrl);
  }
}
