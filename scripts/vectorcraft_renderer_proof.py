"""Proof against the isolated craft service. Every comparison affects the verdict. PDF byte identity is info only."""
import argparse
import hashlib
import io
import json
import time
import uuid
from pathlib import Path
from PIL import Image
from yappy_clipz.crafts.remote import RemoteCraftRunner
from yappy_clipz.crafts.vectorpipeline import check_build, contact_sheet
from yappy_clipz.crafts import vectorcraft
from yappy_clipz.crafts.pdfcraft import CraftRunError

INPUT = b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240"><rect x="20" y="30" width="180" height="100" fill="#ff7040"/><circle cx="240" cy="160" r="35" fill="#3080ff"/></svg>'

def pixels(data):
    with Image.open(io.BytesIO(data)) as im:
        return hashlib.sha256(im.convert('RGBA').tobytes()).hexdigest()
def passed(verdict):
    return bool(verdict) and all(bool(v) for v in verdict.values())
def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--force-fail',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);r=RemoteCraftRunner(a.url);cases={};verdict={}
    sha=hashlib.sha256(INPUT).hexdigest()
    verdict['ready']=r.healthy('vectorcraft')
    for fmt in ('svg','pdf'):
        for name, steps in [('rotate',[{'op':'rotate','params':{'angle':20}}]),('moveScale',[{'op':'move','params':{'dx':15,'dy':10}},{'op':'scale','params':{'sx':75,'sy':90}}]),('reflect',[{'op':'reflectHorizontal'}])]:
            key=fmt+'-'+name; spec=vectorcraft.parse_spec({'title':'Proof','input':'ast_proof','steps':steps,'output':{'format':fmt}})
            outputs=[]; facts=[]
            for i in range(2):
                out=a.out/key/str(i); f=r('vectorcraft','build',inputs=[INPUT],spec=spec,out_dir=out);facts.append(f)
                outputs.append({'data':(out/f['output']).read_bytes(),'before':(out/'previews/before.png').read_bytes(),'after':(out/'previews/after.png').read_bytes()})
                if i==0: time.sleep(1.05) # ModDate can differ; never gate on PDF byte identity
            checks=[check_build(spec,f,input_sha256=sha,output_bytes=o['data'],before=o['before'],after=o['after']) for f,o in zip(facts,outputs)]
            gate={f'run{i}.{k}':v for i,c in enumerate(checks) for k,v in c['mechanical'].items()}
            gate.update(pinnedVersion=all(f['version']==vectorcraft.PINNED_VERSION for f in facts),
                        mechanicalCount=all(len(c['mechanical'])==9 for c in checks),
                        reportedShaMatchesDisk=all(hashlib.sha256(o['data']).hexdigest()==f['sha256'] for f,o in zip(facts,outputs)),
                        reportedBytesMatchesDisk=all(len(o['data'])==f['bytes'] for f,o in zip(facts,outputs)),
                        samePagePixelsTwice=pixels(outputs[0]['after'])==pixels(outputs[1]['after']))
            if a.force_fail: gate['samePagePixelsTwice']=False
            cases[key]={'gate':gate,'infoOnly':{'sameBytesTwice':outputs[0]['data']==outputs[1]['data']},'facts':facts}
            verdict[key]=passed(gate)
            (a.out/(key+'.png')).write_bytes(contact_sheet(outputs[0]['before'],outputs[0]['after']))
    for name,data in [('script',INPUT.replace(b'<rect',b'<script')),('link',INPUT.replace(b'<rect',b'<image href="file:///etc/passwd"')),('entity',b'<!DOCTYPE svg>'+INPUT),('oversize',INPUT.replace(b'width="320"',b'width="9999"'))]:
        jid = 'v' + uuid.uuid4().hex
        try:
            r._request('PUT', f'/v1/jobs/{jid}/inputs/in0.svg', raw_body=data)
            verdict['refuse-'+name]=False
            r._request('DELETE', f'/v1/jobs/{jid}')
        except CraftRunError as exc:
            verdict['refuse-'+name]='craft service:' in str(exc) # unreachable is not a refusal pass
    doc={'cases':cases,'verdict':verdict,'pass':passed(verdict)}
    (a.out/'receipts.json').write_text(json.dumps(doc,indent=2))
    for key,case in cases.items():
        print(key, 'PASS' if verdict[key] else 'FAIL', [k for k,v in case['gate'].items() if not v])
    print('ALL PASS' if doc['pass'] else 'FAIL',verdict)
    return 0 if doc['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
