import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jsonschema import Draft202012Validator

from yappy_clipz.capabilities import default_registry
from yappy_clipz.icm_runtime import IcmRuntime, IcmRuntimeError
from yappy_clipz.prompt_locker import PromptLocker, PromptLockerError
from yappy_clipz.providers import FalApprovalRequired, FalExecutionDisabled, FalProviderAdapter, FalProviderValidationError, FalSettings, ProviderCatalog

ROOT = Path(__file__).resolve().parents[2]


class FakeResponse:
    def __init__(self, status_code, body): self.status_code, self._body = status_code, body
    def json(self): return self._body


class FakeHttp:
    def __init__(self): self.calls=[]
    def request(self, method, url, **kwargs):
        self.calls.append((method,url,kwargs))
        if method == 'POST': return FakeResponse(200, {'request_id':'12345678-abcd','queue_position':1})
        if url.endswith('/status?logs=1'): return FakeResponse(200, {'status':'IN_PROGRESS','logs':[]})
        if method == 'PUT': return FakeResponse(200, {'status':'CANCELLATION_REQUESTED'})
        return FakeResponse(200, {'video':{'url':'https://cdn.example/output.mp4'},'seed':42})


class FoundationTests(unittest.TestCase):
    def test_all_phase06_json_schemas_are_valid(self):
        schema_files = sorted((ROOT / "packages" / "contracts" / "actions").glob("*.schema.json")) + sorted((ROOT / "packages" / "contracts" / "icm").glob("*.schema.json"))
        self.assertGreaterEqual(len(schema_files), 9)
        for path in schema_files:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_registry_has_transport_mapping_and_snapshot(self):
        registry=default_registry()
        self.assertGreaterEqual(len(registry.action_ids()),30)
        self.assertNotIn('icm.run.inspect',registry.action_ids())
        self.assertIn('icm.run.get',registry.action_ids())
        for item in registry.list():
            self.assertTrue(item['cli']['command']); self.assertTrue(item['api']['path']); self.assertTrue(item['mcp']['tool'])
        snapshot=json.loads((ROOT/'packages/contracts/snapshots/capability-registry.v1.json').read_text(encoding='utf-8'))
        self.assertEqual(snapshot,{'schemaVersion':'1.0.0','capabilities':registry.list()})

    def test_prompt_locker_compiles_typed_workflow_inputs(self):
        locker=PromptLocker(ROOT/'prompt_locker')
        self.assertEqual(len(locker.list_prompts()),6)
        result=locker.compile_workflow('seedance.ugc.ab-test',{'dialogue':'This product solved a real workflow problem.','setting':'a working edit studio','wardrobe':'a charcoal overshirt','tone':'calm and specific','image_urls':['https://media.example/product.jpg'],'audio_urls':['https://media.example/voice.wav']})
        self.assertEqual(len(result['steps']),4)
        self.assertEqual(result['steps'][0]['providerInput']['image_urls'],['https://media.example/product.jpg'])
        self.assertIs(result['steps'][0]['providerInput']['generate_audio'],True)
        self.assertIn('00:01',result['steps'][0]['prompt']['text'])
        self.assertTrue(all(step['requiresApproval'] for step in result['steps']))

    def test_prompt_locker_rejects_unsafe_identifier(self):
        with self.assertRaises(PromptLockerError): PromptLocker(ROOT/'prompt_locker').get_prompt('../../secret')

    def test_fal_plan_redacts_key_and_estimates_cost(self):
        adapter=FalProviderAdapter(ProviderCatalog(ROOT/'providers'),FalSettings(),FakeHttp())
        with patch.dict(os.environ,{'FAL_KEY':'super-secret'}):
            plan=adapter.plan(model_id='bytedance/seedance-2.0/fast/reference-to-video',input_payload={'prompt':'@Image1 demonstrates the product.','image_urls':['https://media.example/product.jpg'],'resolution':'720p','duration':'8','aspect_ratio':'9:16','generate_audio':True})
        self.assertNotIn('super-secret',json.dumps(plan)); self.assertEqual(plan['estimatedCost']['amount'],round(.2419*8,4)); self.assertTrue(plan['approvalRequired'])

    def test_fal_rejects_private_references_and_unknown_fields(self):
        adapter=FalProviderAdapter(ProviderCatalog(ROOT/'providers'),FalSettings(),FakeHttp())
        for payload in [{'prompt':'x','image_urls':['https://127.0.0.1/a.jpg']},{'prompt':'x','surprise':True}]:
            with self.assertRaises(FalProviderValidationError): adapter.plan(model_id='bytedance/seedance-2.0/fast/reference-to-video',input_payload=payload)

    def test_fal_submission_requires_approval_and_server_gate(self):
        client=FakeHttp(); catalog=ProviderCatalog(ROOT/'providers'); adapter=FalProviderAdapter(catalog,FalSettings(execution_enabled=False),client)
        payload={'prompt':'a safe scene','resolution':'720p','duration':'4','aspect_ratio':'16:9'}
        with patch.dict(os.environ,{'FAL_KEY':'secret'}):
            with self.assertRaises(FalApprovalRequired): adapter.submit(model_id='bytedance/seedance-2.0/fast/text-to-video',input_payload=payload,approved=False,idempotency_key='idem-1')
            with self.assertRaises(FalExecutionDisabled): adapter.submit(model_id='bytedance/seedance-2.0/fast/text-to-video',input_payload=payload,approved=True,idempotency_key='idem-1')
        self.assertEqual(client.calls,[])

    def test_fal_queue_lifecycle_with_fake_client(self):
        client=FakeHttp(); adapter=FalProviderAdapter(ProviderCatalog(ROOT/'providers'),FalSettings(execution_enabled=True),client)
        payload={'prompt':'a safe scene','resolution':'720p','duration':'4','aspect_ratio':'16:9'}
        with patch.dict(os.environ,{'FAL_KEY':'secret'}):
            submitted=adapter.submit(model_id='bytedance/seedance-2.0/fast/text-to-video',input_payload=payload,approved=True,idempotency_key='idem-1')
            status=adapter.status(model_id='bytedance/seedance-2.0/fast/text-to-video',request_id=submitted['requestId'])
            result=adapter.result(model_id='bytedance/seedance-2.0/fast/text-to-video',request_id=submitted['requestId'])
            cancelled=adapter.cancel(model_id='bytedance/seedance-2.0/fast/text-to-video',request_id=submitted['requestId'],approved=True)
        self.assertEqual(status['status'],'IN_PROGRESS'); self.assertIn('result',result); self.assertEqual(cancelled['status'],'CANCELLATION_REQUESTED')
        self.assertNotIn('secret',json.dumps({'submitted':submitted,'status':status,'result':result,'cancelled':cancelled},default=str))

    def test_icm_run_prepare_verify_handoff_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            icm=IcmRuntime(tmp); run=icm.create_run(tenant_id='tenant_1',project_id='prj_123456',actor_id='agent_test')
            prepared=icm.prepare_stage(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],stage_id='04_prompt_compile',input_refs=[{'kind':'studio_project','id':'prj_123456','version':'1','digest':'sha256:abc'}],allowed_action_ids=['prompt.compile','workflow.compile'])
            self.assertEqual(prepared['state']['status'],'ready')
            icm.start_stage(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],stage_id='04_prompt_compile')
            verified=icm.verify_stage(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],stage_id='04_prompt_compile',outputs=[{'kind':'compiled_workflow','ref':'workflow:seedance.ugc.ab-test'}],verification=[{'check':'prompt_contract_valid','status':'passed','evidenceRef':'evidence/test.json'}])
            self.assertEqual(verified['state']['status'],'verified')
            handoff=icm.handoff_stage(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],stage_id='04_prompt_compile',action_ids=['workflow.compile'],next_stage_id='06_animation')
            self.assertTrue(handoff['resume']['safe'])
            resumed=icm.resume_run(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],actor_id='agent_2')
            self.assertEqual(resumed['run']['status'],'active')
            with self.assertRaises(IcmRuntimeError): icm.resolve_artifact(tenant_id='tenant_1',project_id='prj_123456',run_id=run['runId'],relative_path='../../outside')


if __name__=='__main__': unittest.main()
