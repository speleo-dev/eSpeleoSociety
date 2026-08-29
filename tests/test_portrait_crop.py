import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from face_detection import (
    PORTRAIT_ASPECT_RATIO,
    compute_center_crop_box,
    compute_face_crop_box,
    detect_faces,
    prepare_portrait_upload,
)


def _aspect(box):
    left, top, right, bottom = box
    return (right - left) / (bottom - top)


class CropGeometryTest(unittest.TestCase):
    def test_center_crop_keeps_portrait_aspect(self):
        box = compute_center_crop_box((1600, 1200))
        self.assertAlmostEqual(_aspect(box), PORTRAIT_ASPECT_RATIO, places=2)
        self.assertEqual(box[3] - box[1], 1200)

    def test_center_crop_narrow_image_is_limited_by_width(self):
        box = compute_center_crop_box((300, 4000))
        self.assertEqual(box[2] - box[0], 300)
        self.assertAlmostEqual(_aspect(box), PORTRAIT_ASPECT_RATIO, places=2)

    def test_face_crop_centers_face_with_headroom(self):
        image_size = (2000, 3000)
        face_box = (900, 400, 200, 200)
        left, top, right, bottom = compute_face_crop_box(image_size, face_box)

        self.assertAlmostEqual(_aspect((left, top, right, bottom)), PORTRAIT_ASPECT_RATIO, places=2)
        self.assertAlmostEqual((left + right) / 2, 1000, delta=2)
        self.assertLess(top, 400, "crop must keep headroom above the face")
        self.assertGreater(bottom, 600, "crop must include shoulders below the face")

    def test_face_crop_is_clamped_to_image_bounds(self):
        image_size = (1000, 1000)
        # Face in the very top-left corner would push the crop outside the image.
        box = compute_face_crop_box(image_size, (0, 0, 300, 300))
        self.assertGreaterEqual(box[0], 0)
        self.assertGreaterEqual(box[1], 0)
        self.assertLessEqual(box[2], 1000)
        self.assertLessEqual(box[3], 1000)
        self.assertAlmostEqual(_aspect(box), PORTRAIT_ASPECT_RATIO, places=2)

    def test_face_crop_falls_back_to_center_without_face(self):
        self.assertEqual(
            compute_face_crop_box((800, 600), None),
            compute_center_crop_box((800, 600)),
        )


class DetectFacesTest(unittest.TestCase):
    def test_detect_faces_never_raises(self):
        faces, message = detect_faces(Image.new("RGB", (400, 400), "white"))
        self.assertIsInstance(faces, list)
        self.assertIsInstance(message, str)

    def test_detect_faces_reports_instead_of_crashing_on_unsupported_opencv(self):
        """OpenCV 5 dropped CascadeClassifier; the message must stay actionable."""
        faces, message = detect_faces(Image.new("RGB", (400, 400), "white"))
        self.assertFalse(any(word in message for word in ("Traceback", "AttributeError")))


class PreparePortraitCropTest(unittest.TestCase):
    def _sample(self, temp_dir, size=(1200, 2400)):
        path = Path(temp_dir) / "full_body.jpg"
        Image.new("RGB", size, "white").save(path)
        return str(path)

    def test_explicit_crop_box_is_applied(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._sample(temp_dir)
            result = prepare_portrait_upload(path, crop_box=(100, 200, 540, 800))

        self.assertTrue(result.is_usable)
        self.assertTrue(result.was_cropped)
        self.assertIn("cropped", result.message)

    def test_uncropped_call_keeps_original_framing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._sample(temp_dir)
            result = prepare_portrait_upload(path)

        self.assertTrue(result.is_usable)
        self.assertFalse(result.was_cropped)
        self.assertIsNotNone(result.suggested_crop)

    def test_auto_crop_produces_portrait_proportions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._sample(temp_dir)
            result = prepare_portrait_upload(path, auto_crop=True)
            self.assertTrue(result.was_cropped)

            output = Path(temp_dir) / "out.jpg"
            output.write_bytes(result.image_bytes)
            with Image.open(output) as cropped:
                ratio = cropped.width / cropped.height

        self.assertAlmostEqual(ratio, PORTRAIT_ASPECT_RATIO, places=1)

    def test_crop_box_outside_bounds_is_clamped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._sample(temp_dir, size=(600, 800))
            result = prepare_portrait_upload(path, crop_box=(-50, -50, 5000, 5000))

        self.assertTrue(result.is_usable)

    def test_auto_crop_frames_the_detected_face(self):
        """A full-body photo must be reduced to the head-and-shoulders area."""
        face_box = (400, 200, 200, 220)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._sample(temp_dir, size=(1000, 3000))
            with mock.patch("face_detection.detect_faces", return_value=([face_box], "")):
                result = prepare_portrait_upload(path, auto_crop=True)

        self.assertTrue(result.face_detected)
        self.assertTrue(result.was_cropped)
        left, top, right, bottom = result.suggested_crop
        self.assertLess(top, 200, "headroom above the face is required")
        self.assertGreater(bottom, 420, "shoulders below the face must be included")
        self.assertLess(bottom, 3000, "legs must be cropped away")
        self.assertAlmostEqual((left + right) / 2, 500, delta=2)


if __name__ == "__main__":
    unittest.main()
