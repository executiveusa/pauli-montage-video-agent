"""Phase 09 durable operation and router tests."""
from __future__ import annotations
import os,tempfile,unittest
from pathlib import Path
from yappy_clipz.operations import BudgetExceeded,JsonOperationStore,OperationsService,PostgresOperationStore
from yappy_clipz.providers import ProviderCatalog
from yappy_clipz.router import OmniRouter
from yappy_clipz.postgres_repository import apply_migrations

class OperationsTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.ops=OperationsService(JsonOperationStore(Path(self.temp.name)/"ops.json"))
 def tearDown(self):self.temp.cleanup()
 def test_job_idempotency_lease_retry_events_approval_and_budget(self):
  first=self.ops.create_job(tenant_id="t",project_id="p",job_type="generation",capability="video.text_to_video",idempotency_key="same")
  again=self.ops.create_job(tenant_id="t",project_id="p",job_type="generation",capability="video.text_to_video",idempotency_key="same")
  self.assertEqual(first["id"],again["id"]);claimed=self.ops.claim("t","worker",60);self.assertEqual(claimed["state"],"claimed")
  self.ops.transition("t",first["id"],"running");self.ops.transition("t",first["id"],"failed",error={"code":"x","message":"retry","retryable":True,"details":{}});self.ops.retry("t",first["id"])
  approval=self.ops.request_approval(tenant_id="t",project_id="p",scope_type="cost",subject_id=first["id"],requested_by="u");self.assertEqual(self.ops.decide_approval("t",approval["id"],"approved","u")["status"],"approved")
  self.ops.reserve_cost(tenant_id="t",project_id="p",job_id=first["id"],amount=2,budget_limit=3)
  with self.assertRaises(BudgetExceeded):self.ops.reserve_cost(tenant_id="t",project_id="p",job_id=first["id"],amount=2,budget_limit=3)
  self.assertGreater(len(self.ops.store.list_events("t","p")),4)
 def test_router_is_explainable_and_cost_aware(self):
  router=OmniRouter(ProviderCatalog(Path("providers")));plan=router.plan(capability="video.text_to_video",payload={"duration":"8","resolution":"720p"},quality_lane="economy",max_cost=3)
  self.assertEqual(plan["chosen"]["providerId"],"fal");self.assertLessEqual(plan["chosen"]["estimate"]["amount"],3);self.assertIn("Selected",router.explain(plan)["summary"])

@unittest.skipUnless(os.environ.get("PHASE09_DATABASE_URL"),"PHASE09_DATABASE_URL not configured")
class PostgresOperationsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.url=os.environ["PHASE09_DATABASE_URL"];apply_migrations(cls.url,sorted(Path("migrations").glob("*.sql")))
 def test_postgres_idempotency_and_lease(self):
  service=OperationsService(PostgresOperationStore(self.url));job=service.create_job(tenant_id="phase09",project_id="p",job_type="generation",capability="video.text_to_video",idempotency_key="pg-same");same=service.create_job(tenant_id="phase09",project_id="p",job_type="generation",capability="video.text_to_video",idempotency_key="pg-same");self.assertEqual(job["id"],same["id"]);self.assertEqual(service.claim("phase09","worker",30)["id"],job["id"])
if __name__=="__main__":unittest.main(verbosity=2)
