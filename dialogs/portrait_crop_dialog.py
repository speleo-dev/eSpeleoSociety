# dialogs/portrait_crop_dialog.py
"""Interactive portrait cropping dialog.

Lets the operator turn any photo - a full body shot, a selfie or an unframed
snapshot - into a portrait with the proportions of the eCP card frame. The crop
rectangle is locked to that aspect ratio, so the result always fills the card
instead of being letterboxed.
"""

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from face_detection import (
    PORTRAIT_ASPECT_RATIO,
    compute_center_crop_box,
    compute_face_crop_box,
)

PREVIEW_MAX_SIZE = QSize(560, 560)
MIN_CROP_HEIGHT = 48


class _CropCanvas(QWidget):
    """Displays the photo with a draggable, aspect-locked crop rectangle."""

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.source_image = image
        self.scaled_pixmap = QPixmap.fromImage(
            image.scaled(PREVIEW_MAX_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.scale = self.scaled_pixmap.width() / image.width() if image.width() else 1.0
        self.setFixedSize(self.scaled_pixmap.size())
        self.setCursor(Qt.OpenHandCursor)

        self._crop = QRect()
        self._drag_offset = None

    # -- geometry helpers -------------------------------------------------
    def source_crop_box(self) -> tuple[int, int, int, int]:
        """Crop rectangle in original image coordinates."""
        if self.scale <= 0:
            return (0, 0, self.source_image.width(), self.source_image.height())
        left = int(round(self._crop.left() / self.scale))
        top = int(round(self._crop.top() / self.scale))
        right = int(round(self._crop.right() / self.scale))
        bottom = int(round(self._crop.bottom() / self.scale))
        left = max(0, min(left, self.source_image.width()))
        top = max(0, min(top, self.source_image.height()))
        right = max(left + 1, min(right, self.source_image.width()))
        bottom = max(top + 1, min(bottom, self.source_image.height()))
        return (left, top, right, bottom)

    def set_source_crop_box(self, box) -> None:
        left, top, right, bottom = box
        rect = QRect(
            int(round(left * self.scale)),
            int(round(top * self.scale)),
            max(1, int(round((right - left) * self.scale))),
            max(1, int(round((bottom - top) * self.scale))),
        )
        self._crop = self._constrain(rect)
        self.update()

    def crop_height(self) -> int:
        return self._crop.height()

    def set_crop_height(self, height: int) -> None:
        center = self._crop.center()
        height = max(MIN_CROP_HEIGHT, min(height, self.height()))
        width = max(1, int(round(height * PORTRAIT_ASPECT_RATIO)))
        rect = QRect(0, 0, width, height)
        rect.moveCenter(center)
        self._crop = self._constrain(rect)
        self.update()

    def _constrain(self, rect: QRect) -> QRect:
        height = min(max(rect.height(), MIN_CROP_HEIGHT), self.height())
        width = int(round(height * PORTRAIT_ASPECT_RATIO))
        if width > self.width():
            width = self.width()
            height = int(round(width / PORTRAIT_ASPECT_RATIO))
        rect.setWidth(max(1, width))
        rect.setHeight(max(1, height))

        if rect.left() < 0:
            rect.moveLeft(0)
        if rect.top() < 0:
            rect.moveTop(0)
        if rect.right() > self.width():
            rect.moveRight(self.width())
        if rect.bottom() > self.height():
            rect.moveBottom(self.height())
        return rect

    # -- interaction ------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._crop.contains(event.pos()):
                self._drag_offset = event.pos() - self._crop.topLeft()
            else:
                rect = QRect(self._crop)
                rect.moveCenter(event.pos())
                self._crop = self._constrain(rect)
                self._drag_offset = event.pos() - self._crop.topLeft()
                self.update()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            rect = QRect(self._crop)
            rect.moveTopLeft(event.pos() - self._drag_offset)
            self._crop = self._constrain(rect)
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        self.setCursor(Qt.OpenHandCursor)

    def wheelEvent(self, event):
        step = 20 if event.angleDelta().y() > 0 else -20
        self.set_crop_height(self._crop.height() + step)
        self.crop_changed()

    def crop_changed(self):
        parent = self.parent()
        if hasattr(parent, "sync_slider_with_canvas"):
            parent.sync_slider_with_canvas()

    # -- painting ---------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.scaled_pixmap)

        overlay = QColor(0, 0, 0, 120)
        painter.setPen(Qt.NoPen)
        painter.setBrush(overlay)
        painter.drawRect(QRect(0, 0, self.width(), self._crop.top()))
        painter.drawRect(QRect(0, self._crop.bottom() + 1, self.width(), self.height() - self._crop.bottom()))
        painter.drawRect(QRect(0, self._crop.top(), self._crop.left(), self._crop.height()))
        painter.drawRect(
            QRect(
                self._crop.right() + 1,
                self._crop.top(),
                self.width() - self._crop.right(),
                self._crop.height(),
            )
        )

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d5a93f"), 2))
        painter.drawRect(self._crop)

        painter.setPen(QPen(QColor(255, 255, 255, 140), 1))
        third_h = self._crop.height() / 3.0
        third_w = self._crop.width() / 3.0
        for index in (1, 2):
            y = int(self._crop.top() + third_h * index)
            x = int(self._crop.left() + third_w * index)
            painter.drawLine(self._crop.left(), y, self._crop.right(), y)
            painter.drawLine(x, self._crop.top(), x, self._crop.bottom())
        painter.end()


class PortraitCropDialog(QDialog):
    """Returns a crop box in original image coordinates via :meth:`crop_box`."""

    def __init__(self, image_path: str, face_box=None, suggested_crop=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Crop Portrait Photo"))
        self.face_box = face_box

        image = QImage(image_path)
        if image.isNull():
            raise ValueError(f"Cannot open image: {image_path}")

        layout = QVBoxLayout(self)

        hint = QLabel(
            self.tr(
                "Drag the frame to position it, use the slider or the mouse wheel to zoom. "
                "The frame keeps the proportions of the eCP card portrait."
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        canvas_row = QHBoxLayout()
        canvas_row.addStretch()
        self.canvas = _CropCanvas(image, self)
        canvas_row.addWidget(self.canvas)
        canvas_row.addStretch()
        layout.addLayout(canvas_row)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(MIN_CROP_HEIGHT)
        self.zoom_slider.setMaximum(max(MIN_CROP_HEIGHT + 1, self.canvas.height()))
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.zoom_slider)

        buttons_row = QHBoxLayout()
        self.btn_auto = QPushButton(self.tr("Auto-crop to face"))
        self.btn_auto.clicked.connect(self.apply_auto_crop)
        self.btn_auto.setEnabled(face_box is not None)
        if face_box is None:
            self.btn_auto.setToolTip(self.tr("No face was detected in this photo."))
        buttons_row.addWidget(self.btn_auto)

        self.btn_center = QPushButton(self.tr("Center"))
        self.btn_center.clicked.connect(self.apply_center_crop)
        buttons_row.addWidget(self.btn_center)
        buttons_row.addStretch()
        layout.addLayout(buttons_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        initial = suggested_crop or (
            compute_face_crop_box((image.width(), image.height()), face_box)
            if face_box
            else compute_center_crop_box((image.width(), image.height()))
        )
        self.canvas.set_source_crop_box(initial)
        self.sync_slider_with_canvas()

    # -- actions ----------------------------------------------------------
    def apply_auto_crop(self):
        if not self.face_box:
            return
        size = (self.canvas.source_image.width(), self.canvas.source_image.height())
        self.canvas.set_source_crop_box(compute_face_crop_box(size, self.face_box))
        self.sync_slider_with_canvas()

    def apply_center_crop(self):
        size = (self.canvas.source_image.width(), self.canvas.source_image.height())
        self.canvas.set_source_crop_box(compute_center_crop_box(size))
        self.sync_slider_with_canvas()

    def _on_slider_changed(self, value):
        if value != self.canvas.crop_height():
            self.canvas.set_crop_height(value)

    def sync_slider_with_canvas(self):
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(self.canvas.crop_height())
        self.zoom_slider.blockSignals(False)

    def crop_box(self) -> tuple[int, int, int, int]:
        return self.canvas.source_crop_box()
