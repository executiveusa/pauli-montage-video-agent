import base64
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from tests.studio.vector_fixtures import make_svg
from yappy_clipz.actions import ActionContext
from yappy_clipz.crafts import vectorcraft, service
from yappy_clipz.crafts.remote import RemoteCraftRunner
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings
SCOPES=('project:read','project:write','render:write','asset:read','asset:write')
@unittest.skipUnless(vectorcraft.binary_available(),'set YAPPY_VECTORCRAFT_BIN')
class VectorPipelineTests(unittest.TestCase):
    remote=False
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.rt=create_runtime(settings=Settings(project_root=root/'data'))
        if self.remote:
            (root/'work').mkdir(); self.srv=service.make_server('127.0.0.1',0,root/'work')
            threading.Thread(target=self.srv.serve_forever,daemon=True).start()
            self.rt.vectorcraft.runner=RemoteCraftRunner(f'http://127.0.0.1:{self.srv.server_address[1]}')
        self.pid=self.rt.service.create_project(tenant_id='t1',slug='v',title='V',objective='x',deliverables=['master'])['project']['id']
        self.author=ActionContext(tenant_id='t1',actor_id='agent:author',scopes=SCOPES)
        self.reviewer=ActionContext(tenant_id='t1',actor_id='agent:reviewer',scopes=SCOPES)
        self.approver=ActionContext(tenant_id='t1',actor_id='user:owner',scopes=SCOPES,approved=True,idempotency_key='vf')
        self.asset=self.make_asset(make_svg())
    def tearDown(self):
        if self.remote: self.srv.shutdown(); self.srv.server_close()
        self.tmp.cleanup()
    def make_asset(self,data,mime='image/svg+xml'):
        key=f'tenants/t1/projects/{self.pid}/{hashlib.sha256(data).hexdigest()}.svg'
        info=self.rt.storage.put_bytes(key,data,content_type=mime)
        return self.rt.assets.create_derivative(tenant_id='t1',project_id=self.pid,parent_asset_ids=[],kind='image',role='source',name='art.svg',storage_key=key,mime_type=mime,bytes_count=info.bytes,checksum_sha256=info.checksum_sha256)['id']
    def a(self,action,payload,ctx=None):
        return self.rt.dispatcher.dispatch('vectorcraft.'+action,payload,context=ctx or self.author)['result']
    def spec(self,fmt='svg',steps=None):
        return {'title':'Transform','input':self.asset,'steps':steps or [{'op':'rotate','params':{'angle':20}}],'output':{'format':fmt}}
    def preview(self,spec):
        job=self.a('job.create',{'projectId':self.pid,'spec':spec})
        self.a('plan.run',{'jobId':job['id']})
        return self.a('preview.render',{'jobId':job['id']})
    def test_full_pipeline_both_exports(self):
        for fmt in ('svg','pdf'):
            job=self.preview(self.spec(fmt)); jid={'jobId':job['id']}
            self.assertEqual(job['state'],'preview_ready')
            self.assertEqual(len(job['selfcheck']['mechanical']),9)
            self.assertTrue(all(job['selfcheck']['mechanical'].values()),job['selfcheck'])
            with self.assertRaises(ActionProblem): self.a('review.submit',{**jid,'verdict':'pass'})
            with self.assertRaises(ActionProblem): self.a('final.render',jid,self.approver)
            self.a('review.submit',{**jid,'verdict':'pass'},self.reviewer)
            with self.assertRaises(ActionProblem): self.a('final.render',jid) # explicit approval
            self.approver=ActionContext(tenant_id='t1',actor_id='user:owner',scopes=SCOPES,approved=True,idempotency_key='vf-'+fmt)
            done=self.a('final.render',jid,self.approver)
            data=base64.b64decode(self.a('artifact.get',{**jid,'artifact':'final'})['base64'])
            self.assertEqual(hashlib.sha256(data).hexdigest(),done['preview']['sha256'])
            asset=self.rt.assets.get(tenant_id='t1',project_id=self.pid,asset_id=done['final']['assetId'])
            self.assertEqual(asset['mimeType'],'image/svg+xml' if fmt=='svg' else 'application/pdf')
            self.assertEqual(asset['source']['parentAssetIds'],[self.asset])
    def test_noop_fails_review(self):
        job=self.preview(self.spec(steps=[{'op':'move','params':{'dx':0,'dy':0}}]))
        self.assertFalse(job['selfcheck']['mechanical']['outputDiffersFromInput'])
        with self.assertRaises(ActionProblem): self.a('review.submit',{'jobId':job['id'],'verdict':'pass'},self.reviewer)
    def test_revise_and_tamper_gates(self):
        job=self.preview(self.spec()); jid={'jobId':job['id']}
        revised=self.a('job.revise',{**jid,'spec':self.spec('pdf')},self.reviewer)
        self.assertEqual(revised['state'],'draft'); self.assertIsNone(revised['digest'])
        with self.assertRaises(ActionProblem): self.a('preview.render',jid)
        self.a('plan.run',jid); self.a('preview.render',jid)
        with self.assertRaises(ActionProblem): self.a('review.submit',{**jid,'verdict':'pass'},self.reviewer)
        job2=self.preview(self.spec()); jid2={'jobId':job2['id']}
        self.a('review.submit',{**jid2,'verdict':'pass'},self.reviewer)
        d=self.rt.vectorcraft._dir('t1',job2['id']); (d/job2['preview']['file']).write_bytes(b'tampered')
        with self.assertRaises(ActionProblem): self.a('final.render',jid2,self.approver)
    def test_input_policy_and_changed_input(self):
        self.rt.assets.update_metadata(tenant_id='t1',project_id=self.pid,asset_id=self.asset,tags=['Client:Acme'])
        job=self.a('job.create',{'projectId':self.pid,'spec':self.spec()})
        with self.assertRaises(ActionProblem) as exc: self.a('plan.run',{'jobId':job['id']})
        self.assertEqual(exc.exception.status,403)
        self.rt.assets.update_metadata(tenant_id='t1',project_id=self.pid,asset_id=self.asset,tags=[])
        self.a('plan.run',{'jobId':job['id']})
        asset=self.rt.assets.get(tenant_id='t1',project_id=self.pid,asset_id=self.asset)
        self.rt.storage.put_bytes(asset['storage']['key'],make_svg().replace(b'#ff7040',b'#000000'),content_type='image/svg+xml')
        with self.assertRaises(ActionProblem): self.a('preview.render',{'jobId':job['id']})
        for data,mime in [(b'<svg/>','image/svg+xml'),(make_svg(),'image/png')]:
            bad=self.make_asset(data,mime); job=self.a('job.create',{'projectId':self.pid,'spec':{**self.spec(),'input':bad}})
            with self.assertRaises(ActionProblem): self.a('plan.run',{'jobId':job['id']})
    def test_cross_tenant_and_store(self):
        job=self.a('job.create',{'projectId':self.pid,'spec':self.spec()})
        with self.assertRaises(ActionProblem): self.a('job.get',{'jobId':job['id']},ActionContext(tenant_id='t2',actor_id='agent:x',scopes=SCOPES))
        with self.assertRaises(ActionProblem): self.rt.dispatcher.dispatch('photocraft.job.get',{'jobId':job['id']},context=self.author)
        self.assertEqual(self.a('job.list',{})['count'],1)
class RemoteVectorPipelineTests(VectorPipelineTests): remote=True
