"""Phase 08 asset transfer and provenance tests."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path

from yappy_clipz.assets import AssetError, AssetService
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService
from yappy_clipz.storage import LocalObjectStorage, TransferInvalid, TransferSigner


class AssetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp=tempfile.TemporaryDirectory(); root=Path(self.temp.name)
        self.repo=FileProjectRepository(root/"projects"); self.studio=StudioService(self.repo)
        self.project=self.studio.create_project(tenant_id="tenant_assets",slug="assets",title="Assets",objective="Prove ingest",deliverables=["master"])
        self.assets=AssetService(self.repo,LocalObjectStorage(root/"objects"),TransferSigner("a"*48),max_upload_bytes=1024)
        self.project_id=self.project["project"]["id"]
    def tearDown(self): self.temp.cleanup()

    def test_verified_upload_round_trip_and_archive(self):
        data=b"asset bytes"; checksum=hashlib.sha256(data).hexdigest()
        reservation=self.assets.request_upload(tenant_id="tenant_assets",project_id=self.project_id,filename="frame.png",kind="image",role="source",mime_type="image/png",bytes_expected=len(data),checksum_sha256=checksum)
        token=reservation["complete"]["input"]["transferToken"]
        self.assets.accept_upload(tenant_id="tenant_assets",token=token,data=data,content_type="image/png")
        asset=self.assets.complete_upload(tenant_id="tenant_assets",project_id=self.project_id,transfer_token=token,created_by="test")
        self.assertEqual(asset["checksum"]["value"],checksum); self.assertEqual(len(self.assets.list(tenant_id="tenant_assets",project_id=self.project_id)),1)
        self.assets.attach_rights(tenant_id="tenant_assets",project_id=self.project_id,asset_id=asset["id"],rights={"commercialUse":True,"consentRecordIds":[],"releaseAssetIds":[],"expiresAt":None},license_name="owned")
        self.assets.archive(tenant_id="tenant_assets",project_id=self.project_id,asset_id=asset["id"])
        self.assertEqual(self.assets.list(tenant_id="tenant_assets",project_id=self.project_id),[])
        self.assertEqual(self.assets.download(tenant_id="tenant_assets",token=self.assets.request_download(tenant_id="tenant_assets",project_id=self.project_id,asset_id=asset["id"])["path"].rsplit("/",1)[1])[0],data)

    def test_bad_checksum_and_cross_tenant_token_fail_before_canonical_write(self):
        data=b"bad"; reservation=self.assets.request_upload(tenant_id="tenant_assets",project_id=self.project_id,filename="bad.bin",kind="other",role="source",mime_type=None,bytes_expected=len(data),checksum_sha256="0"*64)
        token=reservation["complete"]["input"]["transferToken"]
        with self.assertRaises(TransferInvalid): self.assets.accept_upload(tenant_id="tenant_other",token=token,data=data,content_type=None)
        with self.assertRaises(AssetError): self.assets.accept_upload(tenant_id="tenant_assets",token=token,data=data,content_type=None)
        self.assertEqual(self.assets.list(tenant_id="tenant_assets",project_id=self.project_id),[])


if __name__=="__main__": unittest.main(verbosity=2)
