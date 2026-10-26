import assert from "node:assert/strict";
import test from "node:test";
import type { Timeline } from "./timeline";
import { planBrowserReview } from "./browser-review-plan";
import { matchChatTime, parseChatSeconds } from "./chat-timing";
const base=():Timeline=>({version:3,canvas:{width:1080,height:1920,fps:30,durationSeconds:4,background:"#000000"},tracks:[{id:"video",type:"video",order:0,items:[{id:"a",kind:"asset",assetId:"source",startSeconds:0,durationSeconds:2,sourceStartSeconds:1,sourceEndSeconds:3},{id:"b",kind:"asset",assetId:"source",startSeconds:2,durationSeconds:2,sourceStartSeconds:6,sourceEndSeconds:8}]}]});
test("browser plan preserves contiguous order, source windows, text timing and immutable input",()=>{
 const timeline=base();timeline.tracks.push({id:"title",type:"text",order:1,items:[{id:"t",kind:"text",startSeconds:2,durationSeconds:1,text:"Saved title",extensions:{role:"title"}}]});
 const before=structuredClone(timeline),plan=planBrowserReview(timeline,"source",10);
 assert.deepEqual(plan.segments,[{start:1,end:3,outputStart:0},{start:6,end:8,outputStart:2}]);
 assert.deepEqual(plan.overlays,[{text:"Saved title",start:2,end:3,role:"title"}]);assert.equal(plan.durationSeconds,4);assert.deepEqual(timeline,before);
});
test("browser review rejects gaps, overlaps and saved duration caps rather than flattening",()=>{
 for(const start of [1.5,2.5]){const timeline=base();timeline.tracks[0].items[1].startSeconds=start;assert.throws(()=>planBrowserReview(timeline,"source",10),/Gaps and overlapping/);}
 for(const cap of [3,5,NaN]){const timeline=base();timeline.canvas.durationSeconds=cap;assert.throws(()=>planBrowserReview(timeline,"source",10),/canvas duration/);}
});
test("browser review refuses additional media, retiming, transforms, audio and muted tracks",()=>{
 const bad:Timeline[]=[];
 let timeline=base();timeline.tracks[0].items[1].assetId="second-source";bad.push(timeline);
 timeline=base();timeline.tracks[0].items[1].sourceEndSeconds=9;bad.push(timeline);
 timeline=base();timeline.tracks[0].items[0].transform={rotationDegrees:20};bad.push(timeline);
 timeline=base();timeline.tracks[0].items[0].effects=[{type:"fade"}];bad.push(timeline);
 timeline=base();timeline.tracks[0].muted=true;bad.push(timeline);
 timeline=base();timeline.tracks.push({id:"audio",type:"audio",order:1,items:[{id:"sound",kind:"asset",assetId:"music",startSeconds:0,durationSeconds:4}]});bad.push(timeline);
 timeline=base();timeline.tracks.push({...timeline.tracks[0],id:"second-track"});bad.push(timeline);
 timeline=base();timeline.canvas.width=1920;timeline.canvas.height=1080;bad.push(timeline);
 for(const value of bad)assert.throws(()=>planBrowserReview(value,"source",10),/FFmpeg/);
 assert.throws(()=>planBrowserReview(base(),"source",7),/out-of-bounds/);
});
test("browser review does not silently truncate unsupported text",()=>{
 const timeline=base();timeline.tracks.push({id:"text",type:"text",order:1,items:[{id:"t",kind:"text",text:"x".repeat(81),startSeconds:0,durationSeconds:1}]});
 assert.throws(()=>planBrowserReview(timeline,"source",10),/Text is too long/);
 timeline.tracks[1].items[0].text="Title";timeline.tracks[1].items[0].durationSeconds=5;
 assert.throws(()=>planBrowserReview(timeline,"source",10),/Text extends/);
});
test("chat timestamps are parsed as whole timestamps, not their numeric prefix",()=>{
 assert.equal(matchChatTime("Trim to 1:30","trim")?.seconds,90);
 assert.equal(matchChatTime("Split at 0:05","split")?.seconds,5);
 assert.equal(matchChatTime("Trim to 5.5 seconds","trim")?.seconds,5.5);
 assert.equal(parseChatSeconds("1:99"),null);assert.equal(parseChatSeconds("1:30:99"),null);
 assert.equal(matchChatTime("trim to 1:30:99","trim")?.seconds,null);
 assert.equal(matchChatTime("trim to 3.14.6","trim"),null);
});
