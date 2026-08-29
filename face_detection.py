from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import os

from PIL import Image, ImageOps


MIN_PORTRAIT_WIDTH = 240
MIN_PORTRAIT_HEIGHT = 240
MAX_PORTRAIT_SIZE = (900, 1200)

# Matches PORTRAIT_BOX in ecp_card.py (220 x 300), so a cropped portrait fills
# the card frame instead of being letterboxed.
PORTRAIT_ASPECT_RATIO = 220 / 300

# Share of the crop height occupied by the detected face, and the headroom kept
# above it. Tuned to produce a head-and-shoulders ID style photo.
FACE_HEIGHT_RATIO = 0.62
FACE_TOP_MARGIN_RATIO = 0.22

# OpenCV 5 removed cv2.CascadeClassifier and no longer ships the Haar XML files;
# its replacement (FaceDetectorYN) needs an ONNX model that we do not vendor.
YUNET_MODEL_ENV_VAR = "ESPELEO_FACE_MODEL"
YUNET_MODEL_FILENAMES = (
    "face_detection_yunet_2023mar.onnx",
    "face_detection_yunet.onnx",
)


@dataclass(frozen=True)
class PortraitPreparationResult:
    is_usable: bool
    face_detected: bool
    face_count: int
    message: str
    image_bytes: bytes = b""
    image_hash: str = ""
    content_type: str = "image/jpeg"
    face_box: tuple[int, int, int, int] | None = None
    suggested_crop: tuple[int, int, int, int] | None = None
    was_cropped: bool = False


def _yunet_model_path() -> str | None:
    configured = os.environ.get(YUNET_MODEL_ENV_VAR)
    if configured and Path(configured).is_file():
        return configured
    models_dir = Path(__file__).parent / "models"
    for name in YUNET_MODEL_FILENAMES:
        candidate = models_dir / name
        if candidate.is_file():
            return str(candidate)
    return None


def _detect_faces_haar(cv2, np, image: Image.Image):
    """OpenCV <= 4 path."""
    cascade_dir = getattr(getattr(cv2, "data", None), "haarcascades", None)
    if not cascade_dir:
        return None, "OpenCV Haar cascade data is unavailable."
    cascade_path = Path(cascade_dir) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        return None, "OpenCV Haar cascade file is unavailable."
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        return None, "OpenCV face cascade could not be loaded."
    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return [tuple(int(v) for v in face) for face in faces], ""


def _detect_faces_yunet(cv2, np, image: Image.Image):
    """OpenCV 5 path, requires a YuNet ONNX model."""
    model_path = _yunet_model_path()
    if not model_path:
        return None, (
            "Face detection is unavailable: this OpenCV build needs a YuNet model. "
            f"Place face_detection_yunet_2023mar.onnx in the models/ directory or set {YUNET_MODEL_ENV_VAR}."
        )
    rgb = np.array(image.convert("RGB"))
    bgr = rgb[:, :, ::-1]
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(model_path, "", (width, height))
    detector.setInputSize((width, height))
    _retval, faces = detector.detect(np.ascontiguousarray(bgr))
    if faces is None:
        return [], ""
    return [tuple(int(v) for v in face[:4]) for face in faces], ""


def detect_faces(image: Image.Image) -> tuple[list[tuple[int, int, int, int]], str]:
    """Return detected face boxes as ``(x, y, w, h)`` plus a status message.

    Never raises: face detection is an assistive feature and must not block a
    portrait upload.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return [], "OpenCV is not installed; portrait was normalized but face detection could not run."

    try:
        if hasattr(cv2, "CascadeClassifier"):
            faces, error = _detect_faces_haar(cv2, np, image)
        elif hasattr(cv2, "FaceDetectorYN"):
            faces, error = _detect_faces_yunet(cv2, np, image)
        else:
            return [], (
                f"Face detection is unavailable in the installed OpenCV "
                f"{getattr(cv2, '__version__', 'build')}."
            )
    except Exception as exc:
        return [], f"Face detection could not run: {exc}"

    if faces is None:
        return [], error
    return faces, ""


def _largest_face(faces) -> tuple[int, int, int, int] | None:
    if not faces:
        return None
    return max(faces, key=lambda face: face[2] * face[3])


def _clamp_box(box, image_size) -> tuple[int, int, int, int]:
    """Fit ``box`` (left, top, right, bottom) inside the image, keeping its size."""
    image_width, image_height = image_size
    left, top, right, bottom = box
    width = min(right - left, image_width)
    height = min(bottom - top, image_height)

    left = max(0, min(left, image_width - width))
    top = max(0, min(top, image_height - height))
    return int(round(left)), int(round(top)), int(round(left + width)), int(round(top + height))


def _box_for_height(center_x: float, top: float, height: float, aspect: float, image_size):
    image_width, image_height = image_size
    height = min(height, image_height)
    width = height * aspect
    if width > image_width:
        width = image_width
        height = width / aspect
    return _clamp_box((center_x - width / 2, top, center_x + width / 2, top + height), image_size)


def compute_center_crop_box(image_size, aspect: float = PORTRAIT_ASPECT_RATIO):
    """Largest centered box with ``aspect`` that fits the image."""
    image_width, image_height = image_size
    height = image_height
    width = height * aspect
    if width > image_width:
        width = image_width
        height = width / aspect
    left = (image_width - width) / 2
    top = (image_height - height) / 2
    return _clamp_box((left, top, left + width, top + height), image_size)


def compute_face_crop_box(image_size, face_box, aspect: float = PORTRAIT_ASPECT_RATIO):
    """Head-and-shoulders crop around ``face_box`` with portrait proportions.

    ``face_box`` is ``(x, y, w, h)`` as returned by :func:`detect_faces`.
    """
    if not face_box:
        return compute_center_crop_box(image_size, aspect)

    face_x, face_y, face_w, face_h = face_box
    crop_height = face_h / FACE_HEIGHT_RATIO
    top = face_y - FACE_TOP_MARGIN_RATIO * crop_height
    center_x = face_x + face_w / 2
    return _box_for_height(center_x, top, crop_height, aspect, image_size)



def prepare_portrait_upload(
    image_path: str,
    crop_box: tuple[int, int, int, int] | None = None,
    auto_crop: bool = False,
) -> PortraitPreparationResult:
    """Normalize a portrait for upload.

    ``crop_box`` is an explicit ``(left, top, right, bottom)`` region, typically
    produced by the portrait crop dialog. When ``auto_crop`` is set and no
    explicit box is given, a head-and-shoulders crop around the detected face is
    applied so full-body photos and selfies become usable portraits.
    """
    try:
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        return PortraitPreparationResult(
            is_usable=False,
            face_detected=False,
            face_count=0,
            message=f"Cannot read portrait image: {exc}",
        )

    if image.width < MIN_PORTRAIT_WIDTH or image.height < MIN_PORTRAIT_HEIGHT:
        return PortraitPreparationResult(
            is_usable=False,
            face_detected=False,
            face_count=0,
            message=(
                f"Portrait image is too small. Minimum size is "
                f"{MIN_PORTRAIT_WIDTH}x{MIN_PORTRAIT_HEIGHT}px."
            ),
        )

    faces, detector_message = detect_faces(image)
    face_box = _largest_face(faces)
    face_detected = face_box is not None
    face_count = len(faces)

    suggested_crop = (
        compute_face_crop_box(image.size, face_box)
        if face_detected
        else compute_center_crop_box(image.size)
    )

    applied_crop = crop_box or (suggested_crop if auto_crop else None)
    was_cropped = False
    if applied_crop:
        applied_crop = _clamp_box(applied_crop, image.size)
        if applied_crop[2] - applied_crop[0] > 0 and applied_crop[3] - applied_crop[1] > 0:
            image = image.crop(applied_crop)
            was_cropped = True

    if face_detected:
        message = f"Detected {face_count} face(s)."
    elif detector_message:
        message = detector_message
    else:
        message = "No face was detected in the portrait."
    if was_cropped:
        message = f"{message} Portrait was cropped to {image.width}x{image.height}px."

    image.thumbnail(MAX_PORTRAIT_SIZE, Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    image_bytes = buffer.getvalue()
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    return PortraitPreparationResult(
        is_usable=True,
        face_detected=face_detected,
        face_count=face_count,
        message=message,
        image_bytes=image_bytes,
        image_hash=image_hash,
        face_box=face_box,
        suggested_crop=suggested_crop,
        was_cropped=was_cropped,
    )
