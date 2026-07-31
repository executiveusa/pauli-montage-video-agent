"""Phase 10 provider-neutral generation and workbench tests."""
from __future__ import annotations
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator

from yappy_clipz.costing import BudgetedOperationsService
from yappy_clipz.generation import GenerationExecutionUnavailable,GenerationService
from yappy_clipz.operations import JsonOperationStore
from yappy_clipz.prompt_locker import PromptLocker
from yappy_clipz.providers import FalSettings,ProviderCatalog
from yappy_clipz.providers.fal_extended import ExtendedFalProviderAdapter
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.router import OmniRouter
from yappy_clipz.service import StudioService

ROOT=Path(__file__).resolve().parents[2]
class FakeResponse:
 def __init__(self,status_code,body):self.status_code=status_code;self._body=body
 def json(self):return self._body
class FakeHttp:
 def __init__(self):self.calls=[]
 def request(self,method,url,**kwargs):
  self.calls.append((method,url,kwargs))
  if method=="POST":return FakeResponse(200,{"request_id":"req-phase10","queue_position":1})
  if url.endswith("/status?logs=1"):return FakeResponse(200,{"status":"COMPLETED","progress":1})
  if method=="PUT":return FakeResponse(200,{"status":"CANCELLATION_REQUESTED"})
  return FakeResponse(200,{"images":[{"url":"https://cdn.example/generated.png","content_type":"image/png","width":1024,"height":1024,"file_size":1234}],"seed":42})

class GenerationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name);self.repo=FileProjectRepository(root/"projects");self.studio=StudioService(self.repo);self.project=self.studio.create_project(tenant_id="tenant_gen",slug="generation",title="Generation",objective="Prove controlled generation",deliverables=["master"]);self.ops=BudgetedOperationsService(JsonOperationStore(root/"operations.json"));self.catalog=ProviderCatalog(ROOT/"providers");self.http=FakeHttp();self.fal=ExtendedFalProviderAdapter(self.catalog,FalSettings(execution_enabled=True),self.http);self.generation=GenerationService(repository=self.repo,catalog=self.catalog,router=OmniRouter(self.catalog),operations=self.ops,prompts=PromptLocker(ROOT/"prompt_locker"),fal=self.fal)
 def tearDown(self):self.temp.cleanup()
 def test_generation_contracts_and_image_plan(self):
  for path in (ROOT/"packages/contracts/generation").glob("*.schema.json"):Draft202012Validator.check_schema(json.loads(path.read_text()))
  plan=self.generation.prepare(tenant_id="tenant_gen",project_id=self.project["project"]["id"],capability="image.generate",provider_input={"prompt":"documentary portrait","num_images":1},model_id="fal-ai/flux-pro/kontext/text-to-image",max_cost=.05)
  self.assertEqual(plan["estimatedCost"]["amount"],.04);self.assertTrue(plan["approvalRequired"])
  with self.assertRaises(GenerationExecutionUnavailable):
   self.generation.prepare(tenant_id="tenant_gen",project_id=self.project["project"]["id"],capability="image.generate",provider_input={"prompt":"documentary portrait","num_images":2},model_id="fal-ai/flux-pro/kontext/text-to-image",max_cost=.05)
 def test_submit_sync_registers_asset_and_reconciles_cost(self):
  payload={"prompt":"a safe four second documentary shot","resolution":"720p","duration":"4","aspect_ratio":"16:9"}
  with patch.dict(os.environ,{"FAL_KEY":"test-secret"}):
   submitted=self.generation.submit(tenant_id="tenant_gen",project_id=self.project["project"]["id"],capability="video.text_to_video",provider_input=payload,actor_id="user:test",approved=True,idempotency_key="idem-generation",model_id="bytedance/seedance-2.0/fast/text-to-video",budget_limit=2)
   synced=self.generation.sync(tenant_id="tenant_gen",job_id=submitted["job"]["id"],actor_id="worker:test")
  self.assertEqual(synced["job"]["state"],"succeeded");self.assertEqual(len(synced["assets"]),1);self.assertEqual(synced["assets"][0]["source"]["provider"],"fal");self.assertAlmostEqual(self.ops.effective_spend("tenant_gen",self.project["project"]["id"]),round(.2419*4,6));self.assertEqual(len([c for c in self.http.calls if c[0]=="POST"]),1)
 def test_disabled_execution_mutates_nothing(self):
  disabled=GenerationService(repository=self.repo,catalog=self.catalog,router=OmniRouter(self.catalog),operations=self.ops,prompts=PromptLocker(ROOT/"prompt_locker"),fal=ExtendedFalProviderAdapter(self.catalog,FalSettings(execution_enabled=False),self.http))
  with patch.dict(os.environ,{"FAL_KEY":"test-secret"}):
   with self.assertRaises(GenerationExecutionUnavailable):disabled.submit(tenant_id="tenant_gen",project_id=self.project["project"]["id"],capability="video.text_to_video",provider_input={"prompt":"safe"},actor_id="u",approved=True,idempotency_key="disabled",model_id="bytedance/seedance-2.0/fast/text-to-video")
  self.assertEqual(self.ops.list_jobs("tenant_gen"),[])
 def test_workflow_plan_preserves_step_costs(self):
  plan=self.generation.plan_workflow(tenant_id="tenant_gen",project_id=self.project["project"]["id"],workflow_id="seedance.product.launch",variables={"dialogue":"This is a useful product.","setting":"a real studio","wardrobe":"charcoal overshirt","tone":"calm","image_urls":["https://cdn.example/product.png"],"video_urls":[],"audio_urls":[]})
  self.assertEqual(len(plan["steps"]),3);self.assertGreater(plan["estimatedCost"]["amount"],0)
if __name__=="__main__":unittest.main(verbosity=2)
