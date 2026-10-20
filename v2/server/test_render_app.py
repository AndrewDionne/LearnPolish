"""Offline tests for Render Free V2 readiness, privacy, and no-data-loss mode."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from render_app import create_render_app, _trusted_origin


class RenderHostTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.dist = root / "dist"
        (self.dist / "generated").mkdir(parents=True)
        (self.dist / "assets").mkdir()
        (self.dist / "index.html").write_text("<html>V2</html>", encoding="utf-8")
        (self.dist / "sw.js").write_text("//offline", encoding="utf-8")
        (self.dist / "assets" / "bundle.js").write_text("export {}", encoding="utf-8")
        (self.dist / "generated" / "lessons.json").write_text(json.dumps({
            "schemaVersion": 1, "lessons": [{
                "id": "greeting", "kind": "vocabulary",
                "items": [{"id": "greeting:0", "polish": "Cześć", "english": "Hello"}]
            }]
        }), encoding="utf-8")
        private = root / "private"
        private.mkdir(mode=0o700)
        self.db = private / "family.sqlite"

    def tearDown(self):
        self.folder.cleanup()

    def preview(self):
        return create_render_app(dist_path=self.dist, family_mode="disabled")

    def family(self):
        return create_render_app(dist_path=self.dist, family_mode="enabled",
                                 database_path=str(self.db),
                                 public_origin="http://127.0.0.1:4173",
                                 require_email=False)

    def test_free_mode_serves_v2_only_when_static_content_is_ready(self):
        client = self.preview().test_client()
        self.assertEqual(client.get("/health/ready").json,
                         {"ready": True, "family_available": False})
        self.assertEqual(client.get("/").status_code, 200)
        self.assertIn(b"V2", client.get("/").data)
        self.assertEqual(client.get("/assets/bundle.js").status_code, 200)
        self.assertEqual(client.get("/").headers["Cache-Control"], "no-store")

        (self.dist / "generated" / "lessons.json").unlink()
        self.assertEqual(client.get("/health/ready").status_code, 503)
        self.assertEqual(client.get("/").status_code, 503)
        self.assertEqual(client.get("/assets/bundle.js").status_code, 503)

    def test_explicit_neon_uses_remote_ready_probe_not_sqlite_disk(self):
        from flask import Flask
        from unittest.mock import patch
        import render_app

        def fake_family(**kwargs):
            self.assertEqual(kwargs["postgres_url"],
                             "postgresql://v2:secret@neon.example.com/Path_to_Polish_DB")
            self.assertIsNone(kwargs["database_path"])
            self.assertTrue(kwargs["allowed_origins"])
            api = Flask("isolated-v2-neon")
            @api.get("/api/v2/family/health")
            def health():
                return {"ok": True}
            return api

        url = "postgresql://v2:secret@neon.example.com/Path_to_Polish_DB"
        with patch.object(render_app, "create_family_app", side_effect=fake_family), \
             patch.object(render_app, "postgres_ready", return_value=True) as probe, \
             patch.object(render_app, "monotonic", return_value=0) as clock:
            app = create_render_app(dist_path=self.dist, family_mode="enabled",
                                    postgres_url=url,
                                    public_origin="https://path-to-polish.onrender.com",
                                    require_email=False)
            client = app.test_client()
            self.assertEqual(client.get("/health/ready").json,
                             {"ready": True, "family_available": True})
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/api/v2/family/health").status_code, 200)
            probe.assert_called_once_with(url)
            # Repeat bundled asset fetches within one ready window do not
            # open new Neon connections, avoiding free-compute waste.
            self.assertEqual(client.get("/assets/bundle.js").status_code, 200)
            probe.assert_called_once_with(url)
            probe.return_value = False
            clock.return_value = 31
            self.assertEqual(client.get("/").status_code, 503)
            self.assertEqual(client.get("/health/ready").status_code, 503)

    def test_free_mode_never_creates_ephemeral_family_accounts(self):
        with patch.dict(os.environ, {"PTP_FAMILY_DB": str(self.db),
                                     "PTP_RENDER_REQUIRE_EMAIL": "0"}):
            client = self.preview().test_client()
        self.assertFalse(self.db.exists())
        for method, path in (("get", "/api/v2/family/health"),
                             ("post", "/api/v2/family/signup"),
                             ("post", "/api/v2/family/groups/1/activity")):
            response = getattr(client, method)(path)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json["error"], "family_service_not_connected")
        self.assertFalse(self.db.exists())

    def test_explicit_durable_family_mode_checks_db_and_api_together(self):
        client = self.family().test_client()
        self.assertEqual(client.get("/health/ready").json,
                         {"ready": True, "family_available": True})
        self.assertEqual(client.get("/api/v2/family/health").status_code, 200)
        self.db.unlink()
        self.assertEqual(client.get("/health/ready").status_code, 503)
        self.assertEqual(client.get("/").status_code, 503)
        self.assertEqual(client.get("/assets/bundle.js").status_code, 503)

    def test_no_private_path_or_api_fallback_servable(self):
        for host in (self.preview, self.family):
            client = host().test_client()
            for path in ("/.env", "/generated/../../render_wsgi.py",
                         "/api/nonexistent", "/health/private", "/no-such-file.js"):
                self.assertEqual(client.get(path).status_code, 404, path)

    def test_invalid_origin_and_unguarded_family_enabling_fail_closed(self):
        for value in ("https://*.example.com", "http://example.com",
                      "https://user:password@example.com", "https://example.com/path"):
            with self.assertRaises(RuntimeError):
                _trusted_origin(value)
        with self.assertRaises(RuntimeError):
            create_render_app(dist_path=self.dist, family_mode="enabled",
                              database_path="family.sqlite",
                              public_origin="https://example.com", require_email=False)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                create_render_app(dist_path=self.dist, family_mode="enabled",
                                  database_path=str(self.db),
                                  public_origin="https://example.com", require_email=True)
        with self.assertRaises(RuntimeError):
            create_render_app(dist_path=self.dist, family_mode="unknown")


if __name__ == "__main__":
    unittest.main()
