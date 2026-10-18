import unittest
from integration.image_download_policy import generated_image_filename


class ImageDownloadPolicyTests(unittest.TestCase):
    def test_only_authenticated_local_generated_route_is_eligible_for_save_dialog(self):
        base = "http://127.0.0.1:8765"
        self.assertEqual(
            generated_image_filename(
                base + "/api/merged/image-studio/generated/42", "image/png", base
            ),
            "golge-gorsel-42.png",
        )
        self.assertEqual(
            generated_image_filename(
                base + "/api/merged/image-studio/generated/42", "image/jpeg", base
            ),
            "golge-gorsel-42.jpg",
        )
        for url in [
            "https://evil.test/api/merged/image-studio/generated/42",
            base + "/api/merged/image-studio/generated/42?token=x",
            base + "/api/merged/image-studio/generated/../settings",
            base + "/api/merged/image-studio/generated/0",
            base + "/uploads/evil.png",
            "data:image/png,evil",
            "file:///private/image.png",
        ]:
            self.assertIsNone(generated_image_filename(url, "image/png", base))
        self.assertIsNone(
            generated_image_filename(
                base + "/api/merged/image-studio/generated/42",
                "application/octet-stream",
                base,
            )
        )


if __name__ == "__main__":
    unittest.main()
