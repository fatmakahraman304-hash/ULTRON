"""Desktop scene design answers known shapes locally, before any model or cloud call."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for sub in ("ultron/backend",):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

import scene_design_api as api  # noqa: E402


class FakeRequest:
    def __init__(self, body):
        self._body, self.app = body, {}

    async def json(self):
        return self._body


class DesktopLibraryTests(unittest.TestCase):
    def test_known_shape_never_touches_cloud_or_model(self):
        with patch("ultron.backend.cloud_client.CloudClient") as client, patch("integration.local_cloud_brain.local_chat_ready") as ready:
            response = asyncio.run(api.design_request(FakeRequest({"description": "8 köşeli yıldız"})))
        self.assertEqual(response.status, 200)
        import json
        body = json.loads(response.text)
        self.assertEqual((body["source"], len(body["design"]["parts"])), ("library", 9))
        client.assert_not_called()
        ready.assert_not_called()

    def test_invalid_description_is_rejected(self):
        response = asyncio.run(api.design_request(FakeRequest({"description": ""})))
        self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
