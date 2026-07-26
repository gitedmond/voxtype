from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPropertyAnimation, Property, QMetaObject, Q_ARG, Slot

class RecordingOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(36, 36)

        # Reposition to top-right of primary screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 50, 15)

        self._opacity_val = 1.0
        self.anim = QPropertyAnimation(self, b"dotOpacity")
        self.anim.setDuration(600)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.2)
        self.anim.setLoopCount(-1)

    def getDotOpacity(self) -> float:
        return self._opacity_val

    def setDotOpacity(self, val: float) -> None:
        self._opacity_val = val
        self.update()

    dotOpacity = Property(float, getDotOpacity, setDotOpacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Pulse red circle
        color = QColor(255, 59, 48, int(255 * self._opacity_val))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 28, 28)

    @Slot()
    def show_recording(self):
        self.show()
        self.anim.start()

    @Slot()
    def hide_recording(self):
        self.anim.stop()
        self.hide()

    def safe_show(self):
        QMetaObject.invokeMethod(self, "show_recording", Qt.ConnectionType.QueuedConnection)

    def safe_hide(self):
        QMetaObject.invokeMethod(self, "hide_recording", Qt.ConnectionType.QueuedConnection)
