from pathlib import Path
import tempfile
import unittest

from PIL import Image

from face_detection import prepare_portrait_upload


class FaceDetectionTest(unittest.TestCase):
    def test_prepare_portrait_upload_rejects_tiny_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "tiny.jpg"
            Image.new("RGB", (80, 80), "white").save(image_path)

            result = prepare_portrait_upload(str(image_path))

        self.assertFalse(result.is_usable)
        self.assertIn("too small", result.message)

    def test_prepare_portrait_upload_normalizes_large_image_to_jpeg(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "portrait.png"
            Image.new("RGB", (900, 1200), "white").save(image_path)

            result = prepare_portrait_upload(str(image_path))

        self.assertTrue(result.is_usable)
        self.assertTrue(result.image_bytes.startswith(b"\xff\xd8"))
        self.assertEqual(len(result.image_hash), 64)
        self.assertEqual(result.content_type, "image/jpeg")


if __name__ == "__main__":
    unittest.main()
