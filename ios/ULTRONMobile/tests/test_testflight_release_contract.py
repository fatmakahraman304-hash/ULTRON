"""Guard against accidental auto-deploy or unsigned TestFlight releases.

Static workflow contract tests only; Apple secrets/signing and TestFlight
publication need the account owner and are intentionally not run in CI.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "ios-testflight.yml"


class TestFlightReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_release_is_explicitly_manual_only(self):
        self.assertIn("  workflow_dispatch:", self.workflow)
        self.assertNotIn("\n  push:", self.workflow)
        self.assertNotIn("\n  pull_request:", self.workflow)
        self.assertNotIn("\n  schedule:", self.workflow)
        self.assertIn("environment: testflight", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)

    def test_signing_credentials_are_environment_secrets(self):
        self.assertIn("secrets.APPSTORE_API_PRIVATE_KEY", self.workflow)
        self.assertIn("secrets.APPSTORE_CERTIFICATES_FILE_BASE64", self.workflow)
        self.assertIn("secrets.APPSTORE_CERTIFICATES_PASSWORD", self.workflow)
        self.assertIn("Verify required Apple configuration", self.workflow)
        self.assertIn("Missing GitHub testflight environment configuration", self.workflow)
        self.assertNotIn("echo \"$APPSTORE_API_PRIVATE_KEY\"", self.workflow)

    def test_signed_archive_and_export_are_required_for_upload(self):
        self.assertIn("apple-actions/import-codesign-certs@v7", self.workflow)
        self.assertIn("apple-actions/download-provisioning-profiles@v6", self.workflow)
        self.assertIn("xcodebuild \\", self.workflow)
        self.assertIn("CODE_SIGN_STYLE=Manual", self.workflow)
        self.assertIn("-exportArchive", self.workflow)
        self.assertIn("apple-actions/upload-testflight-build@v5", self.workflow)
        self.assertNotIn("ULTRONMobile-unsigned.ipa", self.workflow)

    def test_build_provides_unique_version_and_app_store_icon(self):
        self.assertIn("CURRENT_PROJECT_VERSION=${{ github.run_number }}", self.workflow)
        self.assertIn("rsvg-convert -w 1024 -h 1024", self.workflow)
        self.assertIn("ASSETCATALOG_COMPILER_APPICON_NAME=AppIcon", self.workflow)
        self.assertIn("ultron/cloud_service/static/ultron-icon.svg", self.workflow)


if __name__ == "__main__":
    unittest.main()
