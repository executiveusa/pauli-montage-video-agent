"""Rebuild the original-art film source and synthesized score. Python + numpy.

Run here: python author.py. Render via the pinned HyperFrames package scripts.
Logo masters and font license are committed alongside the composition.
"""
from pathlib import Path
import math
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent
A = ROOT / 'assets'
A.mkdir(exist_ok=True)
INK, PAPER, GOLD = '#0A0A0A', '#F4F1EA', '#D7A95B'


def art(n):
    n %= 6
    bg = [GOLD, INK, PAPER, INK, GOLD, INK][n]
    if n == 0:
        body = ''.join(f'<circle cx="240" cy="180" r="{r}" fill="none" stroke="{INK}" stroke-width="3"/>' for r in range(26, 219, 24))
        body += f'<circle class="pulse-disc" cx="240" cy="180" r="58" fill="{INK}"/>'
    elif n == 1:
        body = ''.join(f'<path d="M{-200+i*35} 0l360 360" stroke="{PAPER}" stroke-width="15"/>' for i in range(24))
        body += f'<rect x="145" y="85" width="190" height="190" fill="{GOLD}" transform="rotate(-18 240 180)"/>'
    elif n == 2:
        body = ''.join(f'<path d="M0 {50+i*28}Q120 {200-i*9} 240 {65+i*20}T480 {95+i*25}" fill="none" stroke="{INK}" stroke-width="5"/>' for i in range(10))
        body += f'<circle cx="332" cy="154" r="65" fill="{GOLD}"/>'
    elif n == 3:
        body = ''.join(f'<rect x="{24+i*72}" y="{65+(i%3)*32}" width="42" height="{235-(i%3)*32}" fill="{PAPER if i%2 else GOLD}"/>' for i in range(7))
    elif n == 4:
        body = ''.join(f'<path d="M{40+i*45} 40V320M20 {45+i*40}H460" stroke="{INK}" opacity=".24"/>' for i in range(10))
        body += f'<path d="M100 265L240 70L380 265Z" fill="{INK}"/><circle cx="240" cy="200" r="48" fill="{PAPER}"/>'
    else:
        body = ''.join(f'<rect x="{20+i*23}" y="{20+i*16}" width="{440-i*46}" height="{320-i*32}" fill="none" stroke="{PAPER if i%2 else GOLD}" stroke-width="9"/>' for i in range(8))
    return f'<svg data-layout-ignore="true" viewBox="0 0 480 360" xmlns="http://www.w3.org/2000/svg"><rect width="480" height="360" fill="{bg}"/>{body}</svg>'


def scene(i, start, duration, content, extra=''):
    return f'<section id="s{i}" class="clip scene {extra}" data-composition-id="s{i}" data-start="{start}" data-duration="{duration}" data-track-index="{i}" data-width="1920" data-height="1080"><div class="scene-content">{content}</div></section>'


def copy(kicker, title, support):
    return f'<div class="copy"><p class="eyebrow">{kicker}</p><h2>{title}</h2><p class="support">{support}</p></div>'


holes = ''.join(f'M{x} {y}h28v28h-28Z' for x in (18, 254) for y in (18, 64, 110, 156))
mark = f'<svg class="mark" viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg"><path id="left-strip" fill-rule="evenodd" d="M0 0H64V200H0Z{holes[:holes.find("M254")]}"/><path id="right-strip" fill-rule="evenodd" d="M236 0H300V200H236Z{holes[holes.find("M254"):]}"/><path id="m-core" d="M70 0L150 64L230 0V200H150V120H70Z"/><path id="lower-left" d="M64 136H136V200H64Z"/></svg>'
scenes = [scene(1, 0, 3.5, f'<div class="identity">{mark}<img class="wordmark" src="assets/montage-wordmark-white.svg" alt="Montage"/></div>')]
positions = [(20,25,-12),(360,0,9),(670,45,16),(0,280,6),(335,230,-5),(660,310,-10),(100,520,-7),(420,510,8),(730,555,13)]
cards = ''.join(f'<div class="source-card {"selected" if i==4 else ""}" style="left:{x}px;top:{y}px;transform:rotate({r}deg)">{art(i)}<span>{i+1:02}</span></div>' for i,(x,y,r) in enumerate(positions))
scenes += [scene(2, 2.8, 5.7, copy('01 / SOURCE', 'Start with<br/>your footage.', 'An illustrated workflow.')+f'<div class="art-stage source-field" data-layout-ignore="true">{cards}<div class="selection-frame"></div></div>', 'split dark')]
clips = ''.join(f'<div class="edit-clip clip-{i}">{art(n)}<span>{label}</span>{"<i class=cutline></i>" if i==1 else ""}</div>' for i,(n,label) in enumerate([(1,'A'),(4,'B'),(2,'C')]))
editing = f'<div class="art-stage"><div class="edit-preview">{art(4)}</div><div class="edit-timeline">{clips}<i class="playhead"></i></div><p class="edit-caption">ILLUSTRATED EDIT SEQUENCE</p></div>'
scenes += [scene(3, 7.8, 5.7, copy('02 / EDIT','Cut.<br/>Undo.<br/>Try again.','Keep the original.')+editing, 'split paper')]
# Large typography is kept as SVG paths, including the outlined treatment.
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
font = instantiateVariableFont(TTFont(A/'Inter.ttf'), {'wght':900,'opsz':32})
glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
paths, advance, bounds = [], 0, []
for ch in 'TYPE.':
    name = cmap[ord(ch)]
    pen, bp = SVGPathPen(glyphs), BoundsPen(glyphs)
    glyphs[name].draw(pen); glyphs[name].draw(bp)
    paths.append(f'<path transform="translate({advance} 0)" d="{pen.getCommands()}"/>')
    if bp.bounds:
        x0,y0,x1,y1 = bp.bounds
        bounds.append((advance+x0,y0,advance+x1,y1))
    advance += glyphs[name].width-65
x0=min(b[0] for b in bounds)-30; x1=max(b[2] for b in bounds)+30
y0=min(b[1] for b in bounds)-30; y1=max(b[3] for b in bounds)+30
def type_plate(outline=False):
    paint = f'fill="none" stroke="{GOLD}" stroke-width="16"' if outline else f'fill="{PAPER}"'
    return f'<svg viewBox="{x0} {-y1} {x1-x0} {y1-y0}" xmlns="http://www.w3.org/2000/svg" aria-label="TYPE."><g transform="scale(1 -1)" {paint}>{"".join(paths)}</g></svg>'
scenes += [scene(4,12.8,3.7,'<p class="eyebrow">03 / MOTION STUDIES</p><div class="type-stage"><div class="type-solid">'+type_plate()+'</div><div class="type-outline">'+type_plate(True)+'</div></div><p class="support">Original lettering in motion.</p>','dark')]
planeholes=''.join(f'M{x} {y}h24v32h-24Z' for x in (17,459) for y in (28,96,164,232,300,368,436))
planes=''.join(f'<div class="plane" style="transform:translateZ({-i*78}px)"><svg viewBox="0 0 500 500"><path fill="{INK}" fill-rule="evenodd" d="M0 0H500V500H0ZM58 18H442V482H58Z{planeholes}"/></svg></div>' for i in range(8))
scenes += [scene(5,15.8,3.7,copy('04 / DEPTH','Shape.','Built from the frame.')+f'<div class="art-stage depth" data-layout-ignore="true"><div class="sculpture">{planes}</div></div>','split gold')]
tiles=''.join(f'<div class="tile tile-{i}">{art(i)}</div>' for i in range(9))
scenes += [scene(6,18.8,4.7,f'<div class="rhythm-head"><p class="eyebrow">05 / PACE</p><h2>Rhythm.</h2></div><div class="tile-grid">{tiles}</div>','dark')]
formats=''.join(f'<div class="format {cls}">{art(4)}<span>{label}</span></div>' for cls,label in [('wide','16:9'),('square','1:1'),('tall','9:16')])
scenes += [scene(7,22.8,4.7,copy('06 / OUTPUT','Render.<br/>Review.<br/>Export.','Illustrated output formats.')+f'<div class="art-stage">{formats}</div>','split paper')]
scenes += [scene(8,26.8,3.2,'<div class="closing"><img src="assets/montage-horizontal-white.svg" alt="Montage"/><p class="beta">PRIVATE BETA</p><p class="cta">Request beta access <span>→</span></p></div>','dark')]
css = '''
@font-face{font-family:Inter;src:url(assets/Inter.ttf);font-weight:100 900;font-style:normal}*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0A0A0A;font-family:Inter,Arial,sans-serif}main{position:relative;width:1920px;height:1080px;color:#F4F1EA;overflow:hidden}.scene{position:absolute;inset:0;background:#0A0A0A;overflow:hidden}.scene-content{width:100%;height:100%;padding:100px 140px;display:flex;flex-direction:column;justify-content:center;gap:28px}.split .scene-content{display:grid;grid-template-columns:610px 1fr;gap:66px;align-items:center}.paper{background:#F4F1EA;color:#0A0A0A}.gold{background:#D7A95B;color:#0A0A0A}p,h2{margin:0}.copy{display:flex;flex-direction:column;gap:36px;min-width:0}.eyebrow{font-size:24px;font-weight:550;letter-spacing:.12em}h2{font-size:126px;font-weight:850;letter-spacing:-.065em;line-height:.99}.support{font-size:27px;color:#BCB8B0}.paper .support,.gold .support{color:#393730}.art-stage{height:790px;position:relative;min-width:0}.identity{width:990px;align-self:center;display:flex;flex-direction:column;align-items:center;gap:-6px}.mark{width:450px;height:300px;fill:#FFFFFF}.wordmark{width:900px;height:auto;margin-top:-6px}.source-card{position:absolute;width:260px;height:207px;border:4px solid #F4F1EA;background:#0A0A0A}.source-card svg{width:100%;height:100%;object-fit:cover}.source-card span,.edit-clip span,.format span{position:absolute;left:12px;bottom:12px;background:#0A0A0A;color:#F4F1EA;font-size:24px;padding:6px 10px}.source-card.selected{border-color:#D7A95B;z-index:4}.selection-frame{position:absolute;left:311px;top:211px;width:294px;height:242px;border:3px solid #D7A95B;z-index:6}.edit-preview{position:absolute;left:50px;top:34px;width:780px;height:485px;overflow:hidden}.edit-preview svg{width:100%;height:100%}.edit-timeline{position:absolute;left:50px;top:570px;width:780px;height:112px;display:flex;gap:12px}.edit-clip{position:relative;width:252px;height:112px;flex-shrink:0;overflow:hidden;transform-origin:left center}.edit-clip svg{width:100%;height:100%;object-fit:cover}.edit-clip span{font-size:20px;left:8px;bottom:8px;padding:2px 7px}.cutline{position:absolute;left:126px;top:0;width:4px;height:112px;background:#F4F1EA}.playhead{position:absolute;top:-16px;width:3px;height:144px;background:#0A0A0A}.edit-caption{position:absolute;left:50px;top:728px;font-size:20px;letter-spacing:.08em}.type-stage{display:flex;flex-direction:column;justify-content:center;width:100%;gap:0}.type-stage>div{height:340px;width:100%}.type-stage svg{width:100%;height:100%}.depth{perspective:1150px;display:grid;place-items:center}.sculpture{width:540px;height:540px;transform-style:preserve-3d;transform:rotateY(-28deg) rotateX(16deg) rotateZ(8deg)}.plane{position:absolute;inset:0;transform-style:preserve-3d}.plane svg{width:100%;height:100%}#s5 h2{font-size:162px}.rhythm-head{display:flex;justify-content:space-between;align-items:center}.rhythm-head h2{font-size:116px}.tile-grid{width:1640px;height:700px;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);gap:14px}.tile{overflow:hidden}.tile svg{width:100%;height:100%;object-fit:cover}.format{position:absolute;border:8px solid #0A0A0A;background:#0A0A0A;overflow:hidden}.format svg{width:100%;height:100%}.wide{left:0;top:70px;width:580px;height:326px;transform:rotate(-7deg)}.square{left:80px;top:425px;width:300px;height:300px;transform:rotate(5deg)}.tall{left:562px;top:150px;width:278px;height:494px;transform:rotate(8deg)}.closing{display:flex;flex-direction:column;align-items:center;gap:42px}.closing img{width:1260px;height:auto}.beta{font-size:26px;letter-spacing:.19em;color:#BCB8B0}.cta{font-size:40px}.cta span{color:#D7A95B;margin-left:24px}
'''
js = '''
window.__timelines={};window.__timelines.main=gsap.timeline({paused:true});
function timeline(id,mask){const t=gsap.timeline({paused:true});window.__timelines[id]=t;if(mask)t.fromTo('#'+id,{clipPath:mask},{clipPath:mask.startsWith('circle')?'circle(150% at 72% 50%)':'inset(0% 0% 0% 0%)',duration:.58,ease:'expo.inOut'},0);return t;}
function copyIn(t,id){t.from('#'+id+' .eyebrow',{y:24,opacity:0,duration:.55,ease:'power2.out'},.3).from('#'+id+' h2',{x:-65,opacity:0,duration:.85,ease:'expo.out'},.4).from('#'+id+' .support',{y:28,opacity:0,duration:.65,ease:'power3.out'},.65);}
let t=timeline('s1');t.from('.identity',{scale:1.08,duration:2.3,ease:'power2.out'},.18).from('#left-strip',{x:-920,rotation:-6,opacity:0,svgOrigin:'32 100',duration:1.05,ease:'expo.out'},.2).from('#right-strip',{x:920,rotation:6,opacity:0,svgOrigin:'268 100',duration:1.05,ease:'expo.out'},.38).from('#m-core',{y:190,rotation:-9,opacity:0,svgOrigin:'150 100',duration:.95,ease:'power4.out'},.52).from('#lower-left',{x:-130,y:110,opacity:0,duration:.8,ease:'back.out(1.15)'},.76).from('.wordmark',{y:100,opacity:0,duration:.9,ease:'power3.out'},1.35);
t=timeline('s2','inset(0% 0% 100% 0%)');copyIn(t,'s2');t.from('.source-card',{y:360,scale:.8,rotation:22,opacity:0,stagger:.065,duration:1.15,ease:'power4.out'},.3).from('.selection-frame',{scale:1.3,opacity:0,duration:.5,ease:'power2.out'},2.1).to('.selected',{scale:1.15,rotation:0,duration:.9,ease:'expo.inOut'},2.3);
t=timeline('s3','inset(0% 100% 0% 0%)');copyIn(t,'s3');t.from('.edit-preview',{scale:.78,rotation:8,opacity:0,duration:.95,ease:'power4.out'},.35).from('.edit-clip',{y:110,opacity:0,stagger:.09,duration:.75,ease:'power3.out'},.6).from('.edit-caption',{y:20,opacity:0,duration:.6,ease:'power2.out'},.9).from('.playhead',{opacity:0,duration:.3,ease:'sine.out'},.8).to('.playhead',{x:770,duration:3.65,ease:'none'},1).to('.clip-1',{scaleX:.58,duration:.42,ease:'power2.inOut'},1.65).to('.clip-1',{scaleX:1,duration:.42,ease:'power2.inOut'},2.45).to('.clip-1',{x:264,duration:.65,ease:'expo.inOut'},3.35).to('.clip-2',{x:-264,duration:.65,ease:'expo.inOut'},3.35).to('.edit-preview svg',{rotation:180,duration:1,ease:'power3.inOut'},3.35);
t=timeline('s4','circle(0% at 72% 50%)');t.from('#s4 .eyebrow',{y:25,opacity:0,duration:.6,ease:'power2.out'},.2).from('.type-solid',{x:-1250,opacity:0,duration:1,ease:'expo.out'},.3).from('.type-outline',{x:1250,opacity:0,duration:1,ease:'power4.out'},.44).from('#s4 .support',{y:22,opacity:0,duration:.65,ease:'power3.out'},.8).to('.type-solid',{x:70,duration:1.6,ease:'sine.inOut'},1.35).to('.type-outline',{x:-70,duration:1.6,ease:'sine.inOut'},1.35);
t=timeline('s5','inset(0% 50% 0% 50%)');copyIn(t,'s5');t.from('.plane',{scale:.2,rotationZ:-35,opacity:0,duration:1.15,stagger:.055,ease:'power4.out'},.3).to('.sculpture',{rotationY:30,rotationX:-12,rotationZ:-7,duration:2.5,ease:'sine.inOut'},.6);
t=timeline('s6','inset(50% 0% 50% 0%)');t.from('#s6 .eyebrow',{x:-50,opacity:0,duration:.6,ease:'power2.out'},.2).from('#s6 h2',{y:60,opacity:0,duration:.8,ease:'expo.out'},.3).from('.tile',{scale:.25,rotation:-18,opacity:0,duration:.8,stagger:.055,ease:'power4.out'},.25).to('#s6 .pulse-disc',{scale:1.28,svgOrigin:'240 180',duration:.25,repeat:9,yoyo:true,ease:'sine.inOut'},1.2).to('.tile-1 svg,.tile-5 svg',{rotation:180,duration:2.6,ease:'power2.inOut'},1.15);
t=timeline('s7','inset(0% 0% 0% 100%)');copyIn(t,'s7');t.from('.wide',{x:-180,rotation:-24,opacity:0,duration:1,ease:'expo.out'},.35).from('.square',{y:160,scale:.7,opacity:0,duration:.9,ease:'power3.out'},.6).from('.tall',{x:170,rotation:26,opacity:0,duration:1,ease:'power4.out'},.8).to('.wide',{rotation:-3,duration:1.3,ease:'sine.inOut'},2).to('.tall',{rotation:3,duration:1.3,ease:'sine.inOut'},2);
t=timeline('s8','inset(50% 0% 50% 0%)');t.from('.closing img',{y:65,opacity:0,duration:.9,ease:'expo.out'},.28).from('.beta',{y:30,opacity:0,duration:.65,ease:'power2.out'},.5).from('.cta',{y:35,opacity:0,duration:.7,ease:'power3.out'},.65).to('.closing',{opacity:0,duration:.28,ease:'power2.inOut'},2.9);
'''
html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Montage / brand film</title><script src="assets/gsap-3.14.2.min.js"></script><style>{css}</style></head><body><main id="main" data-composition-id="main" data-start="0" data-duration="30" data-width="1920" data-height="1080">{"".join(scenes)}<audio id="score" src="assets/hero-score.wav" data-start="0" data-duration="30" data-track-index="9" data-volume="1"></audio></main><script>{js}</script></body></html>'
(ROOT/'index.html').write_text(html)

# Original deterministic sound bed; no samples or external music rights.
rate, seconds = 48000, 30
rng = np.random.default_rng(20261020)
mix = np.zeros((rate*seconds,2))
def add(at,duration,freq,gain,pan=0,kind='pluck'):
    t=np.arange(int(duration*rate))/rate
    if kind=='kick': signal=np.sin(2*np.pi*(43*t+(120-43)*.032*(1-np.exp(-t/.032))))*np.exp(-t*18)
    elif kind=='hat': signal=np.diff(rng.normal(size=len(t)+1))*np.exp(-t*75)*.28
    elif kind=='clap': signal=rng.normal(size=len(t))*np.exp(-t*32)*.22
    elif kind=='rise': signal=np.sin(2*np.pi*(freq*t+220*t*t))*np.sin(np.pi*t/duration)**2*.35
    else: signal=(np.sin(2*np.pi*freq*t)+.22*np.sin(4*np.pi*freq*t)+.08*np.sin(6*np.pi*freq*t))*(1-np.exp(-t*100))*np.exp(-t*(7 if kind=='pluck' else 3)/duration)
    start=int(at*rate); length=min(len(signal),len(mix)-start)
    if length>0: mix[start:start+length]+=signal[:length,None]*gain*np.array([math.sqrt((1-pan)/2),math.sqrt((1+pan)/2)])
notes=[110,110,130.8128,146.8324,110,164.8138,146.8324,130.8128]
for beat in range(60):
    at=beat*.5
    if 6<=beat<55:
        add(at,.28,0,.31,kind='kick')
        if beat%2: add(at,.17,0,.22,kind='clap')
        add(at+.25,.09,0,.12,(-1 if beat%2 else 1)*.35,kind='hat')
        add(at+.03,.38,notes[beat%8]/2,.15,kind='bass')
        if not beat%2: add(at+.25,.46,notes[beat%8]*2,.07,(-1 if beat%4 else 1)*.45)
for at in [.18,.34,.7,1.05]:add(at,.18,150+at*180,.16)
for at in [2.6,7.6,12.6,15.6,18.6,22.6,26.6]:add(at,.46,110,.075,kind='rise')
for i,freq in enumerate([220,261.6256,329.6276]):add(27.15+i*.055,2.1,freq,.1,(i-1)*.35,kind='bass')
mix[:int(rate*.08)]*=np.linspace(0,1,int(rate*.08))[:,None]
mix[-int(rate*.55):]*=np.linspace(1,0,int(rate*.55))[:,None]
mix*=.76/np.max(np.abs(mix))
with wave.open(str(A/'hero-score-raw.wav'),'wb') as out:
    out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);out.writeframes((mix*32767).astype('<i2').tobytes())
print('Composition and deterministic score rebuilt.')
