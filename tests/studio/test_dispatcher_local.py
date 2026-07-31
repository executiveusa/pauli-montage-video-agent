import tempfile
import unittest
from pathlib import Path

from yappy_clipz.actions import ActionContext, ActionDispatcher
from yappy_clipz.capabilities import default_registry
from yappy_clipz.errors import ActionProblem
from yappy_clipz.icm_runtime import IcmRuntime
from yappy_clipz.prompt_locker import PromptLocker
from yappy_clipz.providers import FalProviderAdapter, FalSettings, ProviderCatalog

ROOT=Path(__file__).resolve().parents[2]

class FakeService:
    def __init__(self): self.calls=0
    def create_project(self,**kwargs): self.calls+=1; return {'project':{'id':'prj_x','tenantId':kwargs['tenant_id']}}
    def list_projects(self,**kwargs): return []
    def get_project(self,**kwargs): return {'project':{'id':kwargs['project_id'],'tenantId':kwargs['tenant_id']}}
    def validate_project(self,**kwargs): return {'valid':True}
    def get_timeline(self,**kwargs): return {'version':1}
    def replace_timeline(self,**kwargs): self.calls+=1; return {'timeline':{'version':2}}

class DispatcherTests(unittest.TestCase):
    def make(self,tmp):
        service=FakeService(); catalog=ProviderCatalog(ROOT/'providers')
        return service,ActionDispatcher(service=service,registry=default_registry(),prompt_locker=PromptLocker(ROOT/'prompt_locker'),provider_catalog=catalog,fal=FalProviderAdapter(catalog,FalSettings()),icm=IcmRuntime(tmp))

    def test_idempotency_replays_same_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc,d=self.make(tmp); ctx=ActionContext(tenant_id='tenant',idempotency_key='same')
            one=d.dispatch('project.create',{'slug':'a','title':'A','objective':'O','deliverables':['x']},context=ctx)
            two=d.dispatch('project.create',{'slug':'a','title':'A','objective':'O','deliverables':['x']},context=ctx)
            self.assertEqual(svc.calls,1); self.assertFalse(one['idempotentReplay']); self.assertTrue(two['idempotentReplay'])

    def test_idempotency_conflict_and_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,d=self.make(tmp); ctx=ActionContext(tenant_id='tenant',idempotency_key='same')
            d.dispatch('project.create',{'slug':'a','title':'A','objective':'O','deliverables':['x']},context=ctx)
            with self.assertRaises(ActionProblem) as cm: d.dispatch('project.create',{'slug':'b','title':'B','objective':'O','deliverables':['x']},context=ctx)
            self.assertEqual(cm.exception.code,'idempotency_conflict')
            with self.assertRaises(ActionProblem) as cm: d.dispatch('project.list',{},context=ActionContext(tenant_id='tenant',scopes=()))
            self.assertEqual(cm.exception.code,'authorization_denied')

    def test_provider_submit_stops_at_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,d=self.make(tmp)
            with self.assertRaises(ActionProblem) as cm: d.dispatch('provider.request.submit',{'modelId':'bytedance/seedance-2.0/fast/text-to-video','input':{'prompt':'x'}},context=ActionContext(tenant_id='tenant',idempotency_key='i'))
            self.assertEqual(cm.exception.code,'approval_required')

if __name__=='__main__': unittest.main()
