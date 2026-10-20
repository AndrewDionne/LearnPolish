"""Regression guard: user's Render deployment must be FREE and never store accounts on ephemeral disk."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class FreeDeploymentContract(unittest.TestCase):
    def test_render_blueprint_has_no_billable_plan_or_disk(self):
        blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertRegex(blueprint, r"(?m)^\s+plan: free$")
        self.assertNotRegex(blueprint, r"(?m)^\s+(?:disk|databases):")
        self.assertNotRegex(blueprint, r"(?m)^\s+plan: (?:starter|standard|pro)")
        self.assertRegex(blueprint, r"(?m)^\s+healthCheckPath: /health/ready$")
        self.assertRegex(blueprint, r"(?m)^\s+value: disabled$")
        for item in ("PTP_FAMILY_DB", "PTP_FAMILY_SMTP_", "AZURE_SPEECH_KEY"):
            self.assertNotIn(item, blueprint)

    def test_free_docker_image_does_not_turn_on_sync_or_paid_speech(self):
        docker = (ROOT / "Dockerfile.v2").read_text(encoding="utf-8")
        self.assertIn("VITE_FAMILY_API_URL= VITE_SPEECH_ASSESSMENT_ENABLED=false", docker)
        self.assertIn("PTP_RENDER_FAMILY_MODE=disabled", docker)
        self.assertIn("PTP_SPEECH_ENABLED=0", docker)
        self.assertNotIn("PTP_RENDER_FAMILY_MODE=enabled", docker)


if __name__ == "__main__":
    unittest.main()
