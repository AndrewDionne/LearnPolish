"""Offline contract tests: same V2 host, DB readiness and static route privacy."""
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

    def host(self):
        return create_render_app(dist_path=self.dist, database_path=str(self.db),
                                 public_origin="http://127.0.0.1:4173", require_email=False)

    def test_single_host_serves_frontend_and_real_family_health(self):
        client = self.host().test_client()
        self.assertEqual(client.get("/health/ready").json, {"ready": True})
        self.assertEqual(client.get("/").status_code, 200)
        self.assertIn(b"V2", client.get("/").data)
        self.assertEqual(client.get("/assets/bundle.js").status_code, 200)
        response = client.get("/api/v2/family/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])
        self.assertEqual(client.get("/").headers["Cache-Control"], "no-store")

    def test_does_not_serve_shell_if_database_disappears(self):
        client = self.host().test_client()
        self.db.unlink()
        self.assertEqual(client.get("/health/ready").status_code, 503)
        self.assertEqual(client.get("/").status_code, 503)
        self.assertEqual(client.get("/assets/bundle.js").status_code, 503)
        self.assertNotIn(b"V2", client.get("/").data)

    def test_no_private_path_or_api_fallback_servable(self):
        client = self.host().test_client()
        for path in ("/.env", "/generated/../../render_wsgi.py",
                     "/api/nonexistent", "/health/private", "/no-such-file.js"):
            self.assertEqual(client.get(path).status_code, 404, path)

    def test_invalid_origin_and_missing_persistence_fail_closed(self):
        for value in ("https://*.example.com", "http://example.com",
                      "https://user:password@example.com", "https://example.com/path"):
            with self.assertRaises(RuntimeError):
                _trusted_origin(value)
        with self.assertRaises(RuntimeError):
            create_render_app(dist_path=self.dist, database_path="family.sqlite",
                              public_origin="https://example.com", require_email=False)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                create_render_app(dist_path=self.dist, database_path=str(self.db),
                                  public_origin="https://example.com", require_email=True)


if __name__ == "__main__":
    unittest.main()
