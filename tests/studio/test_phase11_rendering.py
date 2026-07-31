"""Phase 11 deterministic render and verification tests."""
from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path

from yappy_clipz.assets import AssetService
from yappy_clipz.costing import BudgetedOperationsService
from yappy_clipz.operations import JsonOperationStore
from yappy_clipz.rendering import RenderPolicyDenied,RenderService
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService
from yappy_clipz.storage import LocalObjectStorage,TransferSigner

class FakeRunner:
 def run(self,argv,*,output_path): output_path.write_bytes(b"rendered-video");return {"returnCode":0,"argv":argv}
 def probe(self,argv): return {"format":{"duration":"8.0"},"streams":[{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":960,"height":540}]}

class RenderTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name);self.repo=FileProjectRepository(root/"projects");self.studio=StudioService(self.repo);self.project=self.studio.create_project(tenant_id="t",slug="render",title="Render",objective="Render",deliverables=["master"]);self.pid=self.project["project"]["id"];self.storage=LocalObjectStorage(root/"objects");self.assets=AssetService(self.repo,self.storage,TransferSigner("a"*48));info=self.storage.put_bytes("source/input.mp4",b"source-video",content_type="video/mp4");self.asset=self.assets.create_derivative(tenant_id="t",project_id=self.pid,parent_asset_ids=[],kind="video",role="source",name="input.mp4",storage_key=info.key,mime_type="video/mp4",bytes_count=info.bytes,checksum_sha256=info.checksum_sha256,created_by="test")
  timeline=self.studio.get_timeline(tenant_id="t",project_id=self.pid);timeline["canvas"]["durationSeconds"]=4;timeline["tracks"]=[{"id":"v","type":"video","name":"Video","order":0,"muted":False,"locked":False,"items":[{"id":"i","kind":"asset","assetId":self.asset["id"],"shotId":None,"startSeconds":0,"durationSeconds":4,"sourceStartSeconds":0,"sourceEndSeconds":4,"text":None,"effects":[],"extensions":{}}]}];self.studio.replace_timeline(tenant_id="t",project_id=self.pid,expected_version=1,timeline=timeline);self.ops=BudgetedOperationsService(JsonOperationStore(root/"operations.json"));self.render=RenderService(repository=self.repo,storage=self.storage,assets=self.assets,operations=self.ops,runner=FakeRunner(),workspace_root=root/"renders")
 def tearDown(self):self.temp.cleanup()
 def test_plan_execute_verify_and_package_evidence(self):
  plan=self.render.plan(tenant_id="t",project_id=self.pid,preset_id="preview",mode="preview");self.assertTrue(plan["manifestDigest"].startswith("sha256:"));self.assertNotIn("shell",plan)
  submitted=self.render.submit(tenant_id="t",project_id=self.pid,preset_id="preview",mode="preview",idempotency_key="preview",approved=True);executed=self.render.execute(tenant_id="t",job_id=submitted["job"]["id"],worker_id="fake");self.assertEqual(executed["job"]["state"],"succeeded");self.assertTrue(self.render.verify(tenant_id="t",project_id=self.pid,asset_id=executed["asset"]["id"])["verified"])
 def test_final_requires_approval_and_verified_inputs(self):
  with self.assertRaises(RenderPolicyDenied):self.render.submit(tenant_id="t",project_id=self.pid,preset_id="youtube_1080p",mode="final",idempotency_key="final",approved=False)
if __name__=="__main__":unittest.main(verbosity=2)
