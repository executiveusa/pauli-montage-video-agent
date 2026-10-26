"""MediaBrain media library source tests."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from yappy_clipz.actions import ActionContext
from yappy_clipz.assets import AssetError, AssetService
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.media_library import (
    ClipNotFound,
    MediaLibraryError,
    MediaLibraryNotConfigured,
    MediaLibraryService,
)
from yappy_clipz.rendering import RenderError, _asset_uri
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService
from yappy_clipz.settings import Settings
from yappy_clipz.storage import LocalObjectStorage, TransferSigner

SAMPLE_CLIP = {
    "id": "1aTi6kB_DlrSYzeCIKZUV-3lKuRbCce7L",
    "account": "samsungjoe2020@gmail.com",
    "remote": "gdrive-samsung",
    "source": "gdrive",
    "name": "Project 22_12_2022.mp4",
    "path": "Organized Files/Videos/2022/12-December",
    "mime": "video/mp4",
    "bytes": 250171546,
    "md5": "b10a8db164e0754105b7a99be72e3fe5",
    "modtime": "2022-12-22 10:11:12",
    "capture_date": "2022-12",
    "date_basis": "filename",
    "link": "https://drive.google.com/file/d/1aTi6kB_DlrSYzeCIKZUV-3lKuRbCce7L/view",
    "kind": "footage",
    "canonical_id": None,
    "vision": "todo",
    "tier": "T0-metadata",
}

_COLUMNS = ("id","account","remote","source","name","path","mime","bytes","md5","modtime",
            "capture_date","date_basis","link","kind","canonical_id","vision","tier")


def build_index(path: Path, rows: list[dict]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE clips (id TEXT PRIMARY KEY, account TEXT, remote TEXT, source TEXT, name TEXT, "
            "path TEXT, mime TEXT, bytes INTEGER, md5 TEXT, modtime TEXT, capture_date TEXT, date_basis TEXT, "
            "link TEXT, kind TEXT, canonical_id TEXT, vision TEXT, tier TEXT)"
        )
        connection.execute(
            "CREATE VIRTUAL TABLE clips_fts USING fts5(id UNINDEXED, name, path, capture_date, text, tokenize='unicode61')"
        )
        # Real index shape: standalone FTS with its own rowids. A leading row for an
        # unrelated id misaligns every later rowid against clips.rowid.
        connection.execute("INSERT INTO clips_fts (id, name, path, capture_date, text) VALUES ('orphan','','','','')")
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO meta VALUES ('schema', 'media-brain-1')")
        for row in rows:
            values = [row.get(column) for column in _COLUMNS]
            cursor = connection.execute(
                f"INSERT INTO clips ({','.join(_COLUMNS)}) VALUES ({','.join('?' for _ in _COLUMNS)})", values
            )
            connection.execute(
                "INSERT INTO clips_fts (id, name, path, capture_date, text) VALUES (?, ?, ?, ?, '')",
                (row["id"], row.get("name"), row.get("path"), row.get("capture_date")),
            )
            if row.get("vision") and row.get("vision") != "todo":
                connection.execute(
                    "INSERT INTO clips_fts (id, name, path, capture_date, text) VALUES (?, '', '', '', ?)",
                    (row["id"], "VISION " + row["vision"]),
                )
        connection.commit()
    finally:
        connection.close()


def second_clip(**overrides) -> dict:
    clip = dict(SAMPLE_CLIP)
    clip.update({"id": "clip-2", "name": "timelapse build site.mov", "path": "Organized Files/Videos/2023/03-March",
                 "mime": "video/quicktime", "capture_date": "2023-03", "link": None, "vision": "trees timelapse workers"})
    clip.update(overrides)
    return clip


class MediaLibraryVisionSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.index = Path(self.temp.name) / "media-index.snapshot.db"
        build_index(self.index, [SAMPLE_CLIP, second_clip()])
        self.service = MediaLibraryService(index_path=self.index, host_root="/mnt/mb-gdrive-samsung", enabled=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def add_vision_tables(self) -> None:
        connection = sqlite3.connect(self.index)
        connection.execute("CREATE TABLE vtags (clip_id TEXT PRIMARY KEY, duration REAL, tags TEXT, secs REAL)")
        connection.execute("CREATE TABLE frames (clip_id TEXT, t REAL, emb BLOB, PRIMARY KEY (clip_id, t))")
        connection.execute(
            "CREATE TABLE photos (id TEXT PRIMARY KEY, zip TEXT, member TEXT, album TEXT, name TEXT, kind TEXT, "
            "bytes INTEGER, taken TEXT, year TEXT, lat REAL, lon REAL, description TEXT, vision TEXT)"
        )
        connection.execute("INSERT INTO vtags VALUES (?,?,?,?)", (SAMPLE_CLIP["id"], 30.0, '["a boxer hits a heavy bag","a gym with red mats"]', 5.0))
        connection.execute("INSERT INTO vtags VALUES (?,?,?,?)", ("clip-2", 20.0, '["workers pour concrete"]', 5.0))
        for t in (0.0, 5.0):
            connection.execute("INSERT INTO frames VALUES (?,?,?)", (SAMPLE_CLIP["id"], t, b"\x00" * 1024))
        connection.execute("INSERT INTO photos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("takeout:z1:IMG_1.jpg", "z1", "IMG_1.jpg", "Trips", "IMG_1.jpg", "photo", 1000, "2021-05-01", "2021", None, None, "a boxer at a gym", "done"))
        connection.commit()
        connection.close()

    def test_missing_tables_are_reported_not_errors(self):
        result = self.service.search_vision(query="boxer")
        self.assertEqual(result["visionTablesPresent"], {"photos": False, "frames": False, "vtags": False})
        self.assertEqual((result["clips"], result["photos"]), ([], []))
        self.assertEqual(self.service.status()["visionTablesPresent"]["vtags"], False)

    def test_vtags_and_photos_match_with_all_words(self):
        self.add_vision_tables()
        result = self.service.search_vision(query="boxer gym")
        self.assertEqual([c["id"] for c in result["clips"]], [SAMPLE_CLIP["id"]])
        self.assertIn("a boxer hits a heavy bag", result["clips"][0]["matchedTags"])
        self.assertEqual(result["clips"][0]["frameTimes"], [0.0, 5.0])
        self.assertEqual([p["id"] for p in result["photos"]], ["takeout:z1:IMG_1.jpg"])
        self.assertEqual(result["photos"][0]["visionStatus"], "done")
        self.assertEqual(self.service.search_vision(query="boxer concrete")["clips"], [])

    def test_wildcards_in_query_are_literal(self):
        self.add_vision_tables()
        self.assertEqual(self.service.search_vision(query="%")["clips"], [])
        self.assertEqual(self.service.search_vision(query="b_xer")["photos"], [])
        with self.assertRaises(MediaLibraryError):
            self.service.search_vision(query="  ")


class MediaLibraryMultiRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.index = Path(self.temp.name) / "media-index.snapshot.db"
        other = second_clip(id="exec-1", remote="gdrive-exec", account="exec@example.test", path="Footage/2024")
        stray = second_clip(id="stray-1", remote="gdrive-other", account="other@example.test")
        build_index(self.index, [SAMPLE_CLIP, other, stray])
        self.roots = {"remote:gdrive-samsung": "/mnt/mb-gdrive-samsung", "remote:gdrive-exec": "/mnt/mb-gdrive-exec"}
        self.service = MediaLibraryService(index_path=self.index, host_root="/mnt/mb-gdrive-samsung", enabled=True, host_roots=self.roots)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_each_remote_maps_to_its_own_root(self):
        self.assertTrue(self.service.get_clip(SAMPLE_CLIP["id"])["hostPath"].startswith("/mnt/mb-gdrive-samsung/"))
        self.assertEqual(self.service.get_clip("exec-1")["hostPath"], "/mnt/mb-gdrive-exec/Footage/2024/timelapse build site.mov")

    def test_unmapped_remote_fails_closed(self):
        with self.assertRaises(MediaLibraryError):
            self.service.get_clip("stray-1")

    def test_listings_skip_and_flag_unmapped_clips(self):
        page = self.service.list_clips(limit=10)
        self.assertEqual(sorted(i["id"] for i in page["items"]), sorted([SAMPLE_CLIP["id"], "exec-1"]))
        self.assertEqual([x["id"] for x in page["unmappedSkipped"]], ["stray-1"])
        found = self.service.search(query="timelapse")
        self.assertEqual([i["id"] for i in found["items"]], ["exec-1"])
        self.assertEqual([x["id"] for x in found["unmappedSkipped"]], ["stray-1"])

    def test_account_key_is_used_when_remote_is_not_mapped(self):
        service = MediaLibraryService(index_path=self.index, host_root="/mnt/x", enabled=True,
                                      host_roots={"account:other@example.test": "/mnt/mb-other"})
        self.assertTrue(service.get_clip("stray-1")["hostPath"].startswith("/mnt/mb-other/"))

    def test_invalid_mapping_is_rejected(self):
        for bad in ({"drive:x": "/mnt/a"}, {"remote:x": "relative/path"}, {"remote:": "/mnt/a"}):
            with self.assertRaises(MediaLibraryError):
                MediaLibraryService(index_path=self.index, host_root="/mnt/x", host_roots=bad)

    def test_status_lists_roots(self):
        self.assertEqual(self.service.status()["hostRoots"], self.roots)


class MediaLibraryFtsJoinTests(unittest.TestCase):
    def test_fts_matches_join_on_id_not_rowid_and_dedupe(self):
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "media-index.snapshot.db"
            build_index(index, [SAMPLE_CLIP, second_clip(), second_clip(id="clip-3", name="trees at dusk.mov", vision="trees dusk")])
            service = MediaLibraryService(index_path=index, host_root="/mnt/mb-gdrive-samsung", enabled=True)
            hit = service.search(query="timelapse")
            self.assertEqual(hit["mode"], "fts")
            self.assertEqual([i["id"] for i in hit["items"]], ["clip-2"])
            # clip-2 has a name row and a VISION row that both match "trees": one result.
            ids = [i["id"] for i in service.search(query="trees")["items"]]
            self.assertEqual(sorted(ids), ["clip-2", "clip-3"])
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual([i["id"] for i in service.search(query="dusk")["items"]], ["clip-3"])


class MediaLibraryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.index = root / "media-index.snapshot.db"
        build_index(self.index, [SAMPLE_CLIP, second_clip()])
        self.service = MediaLibraryService(index_path=self.index, host_root="/mnt/mb-gdrive-samsung", enabled=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_status_reports_counts_and_snapshot_age(self):
        status = self.service.status()
        self.assertEqual(status["counts"]["clips"], 2)
        self.assertEqual(status["counts"]["byKind"], {"footage": 2})
        self.assertTrue(status["ftsAvailable"])
        self.assertFalse(status["remoteWriteEnabled"])
        self.assertEqual(status["byteAccess"], "deferred-mount-pending")
        self.assertIsNotNone(status["snapshotAgeSeconds"])

    def test_list_paging_and_host_path_mapping(self):
        page = self.service.list_clips(limit=1)
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        clip = self.service.get_clip(SAMPLE_CLIP["id"])
        self.assertEqual(clip["hostPath"], "/mnt/mb-gdrive-samsung/Organized Files/Videos/2022/12-December/Project 22_12_2022.mp4")
        self.assertEqual(clip["provider"], "medialibrary")

    def test_search_fts_matches_vision_text(self):
        result = self.service.search(query="timelapse")
        self.assertEqual(result["mode"], "fts")
        self.assertEqual([item["id"] for item in result["items"]], ["clip-2"])

    def test_search_falls_back_to_like_without_fts(self):
        plain = Path(self.temp.name) / "plain.db"
        connection = sqlite3.connect(plain)
        connection.execute("CREATE TABLE clips (id TEXT PRIMARY KEY, name TEXT, path TEXT, mime TEXT, bytes INTEGER, kind TEXT, tier TEXT, vision TEXT)")
        connection.execute("INSERT INTO clips VALUES ('x1', 'boxing fundraiser.mp4', 'Organized Files', 'video/mp4', 10, 'footage', 'T0', 'boxing')")
        connection.commit(); connection.close()
        service = MediaLibraryService(index_path=plain, host_root="/mnt/mb-gdrive-samsung", enabled=True)
        result = service.search(query="boxing")
        self.assertEqual(result["mode"], "like")
        self.assertEqual(len(result["items"]), 1)

    def test_growing_index_is_served_fresh(self):
        build_index_row = second_clip(id="clip-3", name="new arrival.mp4")
        connection = sqlite3.connect(self.index)
        connection.execute(
            "INSERT INTO clips (id, name, path, mime, bytes, kind, tier, vision) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("clip-3", "new arrival.mp4", "Organized Files", "video/mp4", 5, "footage", "T0-metadata", "todo"),
        )
        connection.commit(); connection.close()
        self.assertEqual(self.service.status()["counts"]["clips"], 3)
        self.assertEqual(self.service.get_clip("clip-3")["name"], "new arrival.mp4")

    def test_snapshot_swap_is_served_fresh(self):
        replacement = Path(self.temp.name) / "replacement.db"
        build_index(replacement, [SAMPLE_CLIP])
        os.replace(replacement, self.index)
        self.assertEqual(self.service.status()["counts"]["clips"], 1)

    def test_path_escape_is_rejected(self):
        service = self.service
        evil = dict(SAMPLE_CLIP); evil["id"] = "evil"; evil["path"] = "../../etc"
        with self.assertRaises(MediaLibraryError):
            service._normalize(evil)
        evil2 = dict(SAMPLE_CLIP); evil2["name"] = "../secret.mp4"
        with self.assertRaises(MediaLibraryError):
            service._normalize(evil2)

    def test_unknown_clip_and_disabled_source(self):
        with self.assertRaises(ClipNotFound):
            self.service.get_clip("missing")
        disabled = MediaLibraryService(index_path=self.index, host_root="/mnt/mb-gdrive-samsung", enabled=False)
        with self.assertRaises(MediaLibraryNotConfigured):
            disabled.status()
        missing = MediaLibraryService(index_path=Path(self.temp.name) / "absent.db", host_root="/mnt/mb-gdrive-samsung", enabled=True)
        with self.assertRaises(MediaLibraryNotConfigured):
            missing.status()


class MediaLibraryRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.index = root / "media-index.snapshot.db"
        build_index(self.index, [SAMPLE_CLIP, second_clip()])
        self.library = MediaLibraryService(index_path=self.index, host_root="/mnt/mb-gdrive-samsung", enabled=True)
        self.repo = FileProjectRepository(root / "projects")
        self.studio = StudioService(self.repo)
        self.project = self.studio.create_project(tenant_id="tenant_owner", slug="library", title="Library", objective="Use library footage", deliverables=["master"])
        self.project_id = self.project["project"]["id"]
        self.assets = AssetService(self.repo, LocalObjectStorage(root / "objects"), TransferSigner("b" * 48))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _clip(self, clip_id: str = SAMPLE_CLIP["id"]) -> dict:
        return self.library.get_clip(clip_id)

    def test_register_creates_provenance_reference_asset(self):
        outcome = self.assets.register_library_reference(tenant_id="tenant_owner", project_id=self.project_id, clip=self._clip(), role="source", created_by="test")
        self.assertFalse(outcome["duplicate"])
        asset = outcome["asset"]
        self.assertEqual(asset["storage"], {"type": "provider", "key": f"medialibrary://{SAMPLE_CLIP['id']}", "bucket": None, "url": None})
        self.assertEqual(asset["source"]["type"], "imported")
        self.assertEqual(asset["source"]["provider"], "medialibrary")
        self.assertEqual(asset["source"]["externalId"], SAMPLE_CLIP["id"])
        self.assertEqual(asset["source"]["sourceUrl"], SAMPLE_CLIP["link"])
        self.assertIsNone(asset["checksum"])
        extra = asset["extensions"]["medialibrary"]
        self.assertEqual(extra["hostPath"], "/mnt/mb-gdrive-samsung/Organized Files/Videos/2022/12-December/Project 22_12_2022.mp4")
        self.assertEqual(extra["md5Attestation"], "media-brain-index")
        self.assertEqual(extra["byteAccess"], "deferred-mount-pending")
        stored = self.assets.get(tenant_id="tenant_owner", project_id=self.project_id, asset_id=asset["id"])
        self.assertEqual(stored["name"], SAMPLE_CLIP["name"])

    def test_register_is_idempotent_per_project(self):
        first = self.assets.register_library_reference(tenant_id="tenant_owner", project_id=self.project_id, clip=self._clip(), role="source")
        second = self.assets.register_library_reference(tenant_id="tenant_owner", project_id=self.project_id, clip=self._clip(), role="source")
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["asset"]["id"], second["asset"]["id"])
        self.assertEqual(len(self.assets.list(tenant_id="tenant_owner", project_id=self.project_id)), 1)

    def test_register_rejects_non_media_clip(self):
        clip = self._clip(); clip["mime"] = "application/pdf"
        with self.assertRaises(AssetError):
            self.assets.register_library_reference(tenant_id="tenant_owner", project_id=self.project_id, clip=clip, role="source")

    def test_render_uri_stays_blocked_until_mount_enabled(self):
        outcome = self.assets.register_library_reference(tenant_id="tenant_owner", project_id=self.project_id, clip=self._clip(), role="source")
        asset = outcome["asset"]
        with self.assertRaises(RenderError):
            _asset_uri(asset)
        self.assertEqual(_asset_uri(asset, mount_visible=True), asset["extensions"]["medialibrary"]["hostPath"])


class MediaLibraryDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.index = root / "media-index.snapshot.db"
        build_index(self.index, [SAMPLE_CLIP, second_clip()])
        self.settings = Settings(
            project_root=root / "data",
            media_library_enabled=True,
            media_library_index=str(self.index),
        )
        self.runtime = create_runtime(settings=self.settings)
        project = self.runtime.service.create_project(tenant_id="tenant_owner", slug="dispatch", title="Dispatch", objective="Wire the library", deliverables=["master"])
        self.project_id = project["project"]["id"]
        self.context = ActionContext(tenant_id="tenant_owner", actor_id="user:test", scopes=("project:read", "project:write", "asset:read", "asset:write"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(self, action_id: str, payload: dict, context: ActionContext | None = None) -> dict:
        return self.runtime.dispatcher.dispatch(action_id, payload, context=context or self.context)

    def test_capabilities_advertise_library_actions(self):
        listed = {row["actionId"] for row in self.runtime.capabilities.list()}
        for action_id in ("library.media.status", "library.media.list", "library.media.search", "library.media.get", "library.media.register"):
            self.assertIn(action_id, listed)

    def test_status_list_search_actions(self):
        status = self._run("library.media.status", {})["result"]
        self.assertEqual(status["counts"]["clips"], 2)
        listed = self._run("library.media.list", {"limit": 10})["result"]
        self.assertEqual(listed["total"], 2)
        found = self._run("library.media.search", {"query": "timelapse"})["result"]
        self.assertEqual([item["id"] for item in found["items"]], ["clip-2"])

    def test_register_footage_round_trip(self):
        result = self._run("library.media.register", {"projectId": self.project_id, "clipIds": [SAMPLE_CLIP["id"]]})["result"]
        self.assertEqual(result["counts"], {"registered": 1, "duplicates": 0})
        asset = result["registered"][0]
        self.assertEqual(asset["source"]["provider"], "medialibrary")
        self.assertEqual(asset["extensions"]["medialibrary"]["hostPath"].rsplit("/", 1)[-1], SAMPLE_CLIP["name"])
        again = self._run("library.media.register", {"projectId": self.project_id, "clipIds": [SAMPLE_CLIP["id"], "clip-2"]})["result"]
        self.assertEqual(again["counts"], {"registered": 1, "duplicates": 1})

    def test_register_rejects_unknown_clip_without_write(self):
        with self.assertRaises(ActionProblem) as caught:
            self._run("library.media.register", {"projectId": self.project_id, "clipIds": ["missing"]})
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(self.runtime.assets.list(tenant_id="tenant_owner", project_id=self.project_id), [])

    def test_scopes_are_enforced(self):
        reader = ActionContext(tenant_id="tenant_owner", actor_id="user:test", scopes=("asset:read",))
        with self.assertRaises(ActionProblem) as caught:
            self._run("library.media.register", {"projectId": self.project_id, "clipIds": [SAMPLE_CLIP["id"]]}, context=reader)
        self.assertEqual(caught.exception.status, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
