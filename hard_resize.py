import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QFileDialog, QSpinBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QCheckBox, QDialog, QFormLayout
)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QCursor
from PyQt6.QtCore import Qt, QRectF, QPointF


class CropSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Crop Size")
        layout = QFormLayout()

        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 10000)
        self.width_spinbox.setValue(800)
        layout.addRow("Width:", self.width_spinbox)

        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 10000)
        self.height_spinbox.setValue(600)
        layout.addRow("Height:", self.height_spinbox)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_sizes(self):
        return self.width_spinbox.value(), self.height_spinbox.value()


class DraggableCropRect(QGraphicsRectItem):
    def __init__(self, x, y, width, height, parent_app):
        super().__init__(x, y, width, height)
        self.parent_app = parent_app
        self.setPen(QPen(Qt.GlobalColor.red, 2))
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.dragging_edge = None
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def hoverMoveEvent(self, event):
        rect = self.rect()
        pos = event.pos()
        margin = 10

        if abs(pos.x() - rect.left()) < margin:
            self.dragging_edge = "left"
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif abs(pos.x() - rect.right()) < margin:
            self.dragging_edge = "right"
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif abs(pos.y() - rect.top()) < margin:
            self.dragging_edge = "top"
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif abs(pos.y() - rect.bottom()) < margin:
            self.dragging_edge = "bottom"
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.dragging_edge = None
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_edge:
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_edge:
            rect = self.rect()
            pos = event.pos()

            if self.dragging_edge == "left":
                rect.setLeft(max(0, pos.x()))
            elif self.dragging_edge == "right":
                rect.setRight(min(self.parentItem().boundingRect().width(), pos.x()))
            elif self.dragging_edge == "top":
                rect.setTop(max(0, pos.y()))
            elif self.dragging_edge == "bottom":
                rect.setBottom(min(self.parentItem().boundingRect().height(), pos.y()))

            self.setRect(rect)
            self.parent_app.update_crop_overlay()
        else:
            rect = self.rect()
            new_pos = event.pos() - event.buttonDownPos(Qt.MouseButton.LeftButton) + rect.topLeft()

            max_x = self.parentItem().boundingRect().width() - rect.width()
            max_y = self.parentItem().boundingRect().height() - rect.height()

            new_x = max(0, min(new_pos.x(), max_x))
            new_y = max(0, min(new_pos.y(), max_y))

            self.setRect(QRectF(QPointF(new_x, new_y), rect.size()))
            self.parent_app.update_crop_overlay()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)


class ImageResizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Resizer")
        self.setGeometry(100, 100, 1000, 700)

        self.image_path = None
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.crop_rect_item = None
        self.overlay_item = None  # Добавляем переменную для хранения оверлея
        self.current_scale = 1.0

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        controls_panel = QWidget()
        controls_panel.setFixedWidth(250)
        controls_layout = QVBoxLayout(controls_panel)

        self.open_button = QPushButton("Open Image")
        self.open_button.clicked.connect(self.open_image)
        controls_layout.addWidget(self.open_button)

        controls_layout.addWidget(QLabel("Target Size:"))

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Width:"))
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 10000)
        self.width_spinbox.setValue(800)
        self.width_spinbox.valueChanged.connect(self.size_changed)
        size_layout.addWidget(self.width_spinbox)
        controls_layout.addLayout(size_layout)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Height:"))
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 10000)
        self.height_spinbox.setValue(600)
        self.height_spinbox.valueChanged.connect(self.size_changed)
        size_layout.addWidget(self.height_spinbox)
        controls_layout.addLayout(size_layout)

        self.keep_aspect_checkbox = QCheckBox("Keep aspect ratio")
        self.keep_aspect_checkbox.setChecked(True)
        controls_layout.addWidget(self.keep_aspect_checkbox)

        self.resize_button = QPushButton("Resize")
        self.resize_button.clicked.connect(self.resize_image)
        controls_layout.addWidget(self.resize_button)

        self.set_crop_button = QPushButton("Set Crop Size")
        self.set_crop_button.clicked.connect(self.set_crop_size)
        self.set_crop_button.setEnabled(False)
        controls_layout.addWidget(self.set_crop_button)

        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.crop_image)
        self.done_button.setEnabled(False)
        controls_layout.addWidget(self.done_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        controls_layout.addWidget(self.save_button)

        controls_layout.addWidget(QLabel("Zoom:"))

        zoom_layout = QHBoxLayout()
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.zoom_out_button)

        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.zoom_in_button)

        self.reset_zoom_button = QPushButton("Reset")
        self.reset_zoom_button.clicked.connect(self.reset_zoom)
        zoom_layout.addWidget(self.reset_zoom_button)

        controls_layout.addLayout(zoom_layout)
        controls_layout.addStretch()

        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)

        main_layout.addWidget(controls_panel)
        main_layout.addWidget(self.graphics_view, 1)

    def size_changed(self):
        if self.keep_aspect_checkbox.isChecked() and self.original_pixmap:
            sender = self.sender()
            if sender == self.width_spinbox:
                new_height = int(self.width_spinbox.value() / (self.original_pixmap.width() / self.original_pixmap.height()))
                self.height_spinbox.blockSignals(True)
                self.height_spinbox.setValue(new_height)
                self.height_spinbox.blockSignals(False)
            elif sender == self.height_spinbox:
                new_width = int(self.height_spinbox.value() * (self.original_pixmap.width() / self.original_pixmap.height()))
                self.width_spinbox.blockSignals(True)
                self.width_spinbox.setValue(new_width)
                self.width_spinbox.blockSignals(False)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.image_path = file_path
            self.original_pixmap = QPixmap(file_path)
            self.display_image(self.original_pixmap)
            self.width_spinbox.setValue(self.original_pixmap.width())
            self.height_spinbox.setValue(self.original_pixmap.height())
            self.set_crop_button.setEnabled(False)
            self.done_button.setEnabled(False)
            self.reset_zoom()

    def display_image(self, pixmap):
        self.scene.clear()
        self.crop_rect_item = None
        self.overlay_item = None

        pixmap_item = self.scene.addPixmap(pixmap)
        pixmap_item.setPos(0, 0)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.fit_to_view()

    def fit_to_view(self):
        self.graphics_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.current_scale = self.graphics_view.transform().m11()
        self.update_zoom_label()

    def update_zoom_label(self):
        self.zoom_label.setText(f"{int(self.current_scale * 100)}%")

    def zoom_in(self):
        self.graphics_view.scale(1.2, 1.2)
        self.current_scale *= 1.2
        self.update_zoom_label()

    def zoom_out(self):
        self.graphics_view.scale(1/1.2, 1/1.2)
        self.current_scale /= 1.2
        self.update_zoom_label()

    def reset_zoom(self):
        self.graphics_view.resetTransform()
        self.current_scale = 1.0
        self.fit_to_view()

    def resize_image(self):
        if not self.original_pixmap:
            return

        target_width = self.width_spinbox.value()
        target_height = self.height_spinbox.value()

        self.scaled_pixmap = self.original_pixmap.scaled(
            target_width, target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.display_image(self.scaled_pixmap)
        self.set_crop_button.setEnabled(True)
        self.done_button.setEnabled(False)

    def set_crop_size(self):
        if not self.scaled_pixmap:
            return

        dialog = CropSizeDialog(self)
        if dialog.exec():
            crop_width, crop_height = dialog.get_sizes()
            crop_width = min(crop_width, self.scaled_pixmap.width())
            crop_height = min(crop_height, self.scaled_pixmap.height())
            self.display_image_with_crop_rect(crop_width, crop_height)
            self.done_button.setEnabled(True)

    def display_image_with_crop_rect(self, crop_width, crop_height):
        if not self.scaled_pixmap:
            return

        self.scene.clear()
        pixmap_item = self.scene.addPixmap(self.scaled_pixmap)
        pixmap_item.setPos(0, 0)

        crop_x = (self.scaled_pixmap.width() - crop_width) // 2
        crop_y = (self.scaled_pixmap.height() - crop_height) // 2

        crop_x = max(0, min(crop_x, self.scaled_pixmap.width() - crop_width))
        crop_y = max(0, min(crop_y, self.scaled_pixmap.height() - crop_height))

        self.crop_rect_item = DraggableCropRect(crop_x, crop_y, crop_width, crop_height, self)
        self.crop_rect_item.setParentItem(pixmap_item)
        self.scene.addItem(self.crop_rect_item)

        self.update_crop_overlay()
        self.scene.setSceneRect(0, 0, self.scaled_pixmap.width(), self.scaled_pixmap.height())
        self.fit_to_view()

    def update_crop_overlay(self):
        if not self.crop_rect_item:
            return

        # Удаляем старый оверлей, если он существует
        if self.overlay_item:
            self.scene.removeItem(self.overlay_item)
            self.overlay_item = None

        img_width = self.scaled_pixmap.width()
        img_height = self.scaled_pixmap.height()
        crop_rect = self.crop_rect_item.rect()

        overlay = QPixmap(img_width, img_height)
        overlay.fill(Qt.GlobalColor.transparent)  # Исправлено на правильное значение

        painter = QPainter(overlay)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setOpacity(0.5)

        # Приводим все значения к целым числам
        if crop_rect.left() > 0:
            painter.drawRect(0, 0, int(crop_rect.left()), img_height)
        if crop_rect.right() < img_width:
            painter.drawRect(int(crop_rect.right()), 0, int(img_width - crop_rect.right()), img_height)
        if crop_rect.top() > 0:
            painter.drawRect(int(crop_rect.left()), 0, int(crop_rect.width()), int(crop_rect.top()))
        if crop_rect.bottom() < img_height:
            painter.drawRect(int(crop_rect.left()), int(crop_rect.bottom()), int(crop_rect.width()), int(img_height - crop_rect.bottom()))

        painter.end()

        self.overlay_item = self.scene.addPixmap(overlay)
        self.overlay_item.setPos(0, 0)
        self.overlay_item.setZValue(1)

    def crop_image(self):
        if not self.scaled_pixmap or not self.crop_rect_item:
            return

        crop_rect = self.crop_rect_item.rect()
        cropped_pixmap = QPixmap(int(crop_rect.width()), int(crop_rect.height()))
        cropped_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(cropped_pixmap)
        painter.drawPixmap(
            QRectF(0, 0, crop_rect.width(), crop_rect.height()),
            self.scaled_pixmap,
            crop_rect
        )
        painter.end()

        self.scaled_pixmap = cropped_pixmap
        self.display_image(self.scaled_pixmap)
        self.set_crop_button.setEnabled(True)
        self.done_button.setEnabled(False)

        self.width_spinbox.setValue(self.scaled_pixmap.width())
        self.height_spinbox.setValue(self.scaled_pixmap.height())

    def save_image(self):
        if not self.scaled_pixmap:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)"
        )

        if file_path:
            if file_path.endswith('.png'):
                self.scaled_pixmap.save(file_path, 'PNG')
            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                self.scaled_pixmap.save(file_path, 'JPEG')
            elif file_path.endswith('.bmp'):
                self.scaled_pixmap.save(file_path, 'BMP')
            else:
                self.scaled_pixmap.save(file_path + '.png', 'PNG')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageResizerApp()
    window.show()
    sys.exit(app.exec())