from dataclasses import dataclass
from io import BytesIO
import hashlib

from PIL import Image, ImageOps


MIN_PORTRAIT_WIDTH = 240
MIN_PORTRAIT_HEIGHT = 240
MAX_PORTRAIT_SIZE = (900, 1200)


@dataclass(frozen=True)
class PortraitPreparationResult:
    is_usable: bool
    face_detected: bool
    face_count: int
    message: str
    image_bytes: bytes = b""
    image_hash: str = ""
    content_type: str = "image/jpeg"


def _detect_faces(image: Image.Image) -> tuple[bool, int, str]:
    try:
        import cv2
        import numpy as np
    except Exception:
        return False, 0, "OpenCV is not installed; portrait was normalized but face detection could not run."

    try:
        gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return False, 0, "OpenCV face cascade is unavailable."
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        face_count = len(faces)
        if face_count:
            return True, face_count, f"Detected {face_count} face(s)."
        return False, 0, "No face was detected in the portrait."
    except Exception as exc:
        return False, 0, f"Face detection failed: {exc}"


def prepare_portrait_upload(image_path: str) -> PortraitPreparationResult:
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

    face_detected, face_count, face_message = _detect_faces(image)
    image.thumbnail(MAX_PORTRAIT_SIZE, Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    image_bytes = buffer.getvalue()
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    return PortraitPreparationResult(
        is_usable=True,
        face_detected=face_detected,
        face_count=face_count,
        message=face_message,
        image_bytes=image_bytes,
        image_hash=image_hash,
    )
