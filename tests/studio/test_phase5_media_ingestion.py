from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from yappy_clipz.api import create_app
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings


class Phase5MediaIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old=dict(os.environ);os.environ["TEST_PHASE5_SECRET"]="phase-five-storage-and-auth-secret-"*2
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.settings=Settings(project_root=root/"projects",storage_root=root/"objects",auth_mode="hosted",auth_signing_secret_env="TEST_PHASE5_SECRET",account_store_path=root/"accounts.json",max_upload_bytes=1024*1024)
        self.runtime=create_runtime(self.settings);self.client=TestClient(create_app(runtime=self.runtime))
        self.alice=self.signup("alice-media@example.com");self.bob=self.signup("bob-media@example.com")
        response=self.client.post("/api/v1/projects",headers=self.headers(self.alice),json={"slug":"media","title":"Media","objective":"ingest","deliverables":["master"]})
        self.assertEqual(response.status_code,201,response.text);self.project_id=response.json()["project"]["id"]

    def tearDown(self) -> None:
        self.temp.cleanup();os.environ.clear();os.environ.update(self.old)

    def signup(self,email:str)->dict:
        response=self.client.post("/api/v1/accounts",json={"email":email,"password":"correct-horse-battery","display_name":"Media Owner"})
        self.assertEqual(response.status_code,201,response.text);return response.json()

    @staticmethod
    def headers(account:dict)->dict[str,str]: return {"Authorization":"Bearer "+account["accessToken"]}

    def action(self,account:dict,action_id:str,input_payload:dict,approved:bool=False):
        return self.client.post(f"/api/v1/actions/{action_id}",headers=self.headers(account),json={"input":input_payload,"approved":approved})

    def reserve(self,account:dict,name:str="clip.mp4",size:int=24):
        response=self.action(account,"asset.upload.request",{"projectId":self.project_id,"filename":name,"kind":"video","role":"source","mimeType":"video/mp4","bytes":size})
        self.assertEqual(response.status_code,200,response.text);return response.json()["result"]

    def test_stream_upload_preview_timeline_persistence_archive_and_deduplication(self) -> None:
        data=b"0000ftypisom-real-video"
        reservation=self.reserve(self.alice,size=len(data));token=reservation["complete"]["input"]["transferToken"]
        denied=self.client.put(reservation["upload"]["path"],headers={**self.headers(self.bob),"content-type":"video/mp4"},content=data)
        self.assertEqual(denied.status_code,403)
        uploaded=self.client.put(reservation["upload"]["path"],headers={**self.headers(self.alice),"content-type":"video/mp4"},content=data)
        self.assertEqual(uploaded.status_code,200,uploaded.text)
        completed=self.action(self.alice,"asset.upload.complete",{"projectId":self.project_id,"transferToken":token})
        self.assertEqual(completed.status_code,200,completed.text);asset=completed.json()["result"]
        preview=self.action(self.alice,"asset.download.request",{"projectId":self.project_id,"assetId":asset["id"]}).json()["result"]
        downloaded=self.client.get(preview["path"],headers=self.headers(self.alice));self.assertEqual(downloaded.content,data)
        used=self.action(self.alice,"asset.timeline.add",{"projectId":self.project_id,"assetId":asset["id"]})
        self.assertEqual(used.status_code,200,used.text);self.assertEqual(used.json()["result"]["timeline"]["tracks"][0]["items"][0]["assetId"],asset["id"])

        duplicate=self.reserve(self.alice,name="duplicate.mp4",size=len(data));duplicate_token=duplicate["complete"]["input"]["transferToken"]
        self.client.put(duplicate["upload"]["path"],headers={**self.headers(self.alice),"content-type":"video/mp4"},content=data)
        duplicate_result=self.action(self.alice,"asset.upload.complete",{"projectId":self.project_id,"transferToken":duplicate_token}).json()["result"]
        self.assertEqual(duplicate_result["id"],asset["id"])
        reopened=create_runtime(self.settings);self.assertEqual(len(reopened.assets.list(tenant_id=self.alice["workspace"]["tenantId"],project_id=self.project_id)),1)
        archived=self.action(self.alice,"asset.archive",{"projectId":self.project_id,"assetId":asset["id"]},approved=True)
        self.assertEqual(archived.status_code,200,archived.text);self.assertEqual(reopened.storage.get_bytes(asset["storage"]["key"]),data)

    def test_invalid_media_and_incomplete_transfer_fail_before_project_mutation(self) -> None:
        invalid=self.action(self.alice,"asset.upload.request",{"projectId":self.project_id,"filename":"wrong.mp4","kind":"video","role":"source","mimeType":"text/plain","bytes":4})
        self.assertEqual(invalid.status_code,400)
        reservation=self.reserve(self.alice,size=12)
        partial=self.client.put(reservation["upload"]["path"],headers={**self.headers(self.alice),"content-type":"video/mp4","content-length":"12"},content=b"short")
        self.assertEqual(partial.status_code,400)
        listed=self.action(self.alice,"asset.list",{"projectId":self.project_id})
        self.assertEqual(listed.json()["result"],[])

    def test_hosted_web_contract_has_progress_cancel_retry_preview_and_safe_archive(self) -> None:
        root=Path(__file__).resolve().parents[2]/"apps/studio-web"
        source=(root/"components/HostedAssetLibrary.tsx").read_text()
        for marker in ("XMLHttpRequest","onprogress","Upload cancelled","Retry upload","Preview","Use in timeline","Archive"):
            self.assertIn(marker,source)
        proxy=(root/"lib/studio-proxy.ts").read_text();self.assertIn('duplex="half"',proxy)
        self.assertTrue((root/"app/api/studio/assets/transfers/[token]/route.ts").is_file())


if __name__=="__main__": unittest.main()
