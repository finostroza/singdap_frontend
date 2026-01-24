from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QRectF, Property, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

class Spinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60 FPS

    def _rotate(self):
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center point
        center = self.rect().center()
        radius = 20
        
        # Pen for the spinner
        pen = QPen()
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)

        # Draw track (light gray circle)
        pen.setColor(QColor("#e0e0e0"))
        painter.setPen(pen)
        painter.drawEllipse(center, radius, radius)

        # Draw rotating arc (Primary Blue #006FB3)
        pen.setColor(QColor("#006FB3"))
        painter.setPen(pen)
        
        # Draw span of 90 degrees
        rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        start_angle = -self._angle * 16
        span_angle = -100 * 16 # Negative for clockwise visual
        
        painter.drawArc(rect, start_angle, span_angle)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent:
            self.resize(parent.size())
            parent.installEventFilter(self)

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Block input
        self.setVisible(False)

        # Layout to center spinner
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.spinner = Spinner()
        layout.addWidget(self.spinner)
        
        # Label text
        self.label = QLabel("Cargando...")
        self.label.setStyleSheet("color: #006FB3; font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(self.label, 0, Qt.AlignCenter)

    def paintEvent(self, event):
        # Semi-transparent white background
        painter = QPainter(self)
        painter.setBrush(QBrush(QColor(255, 255, 255, 200))) # White with Alpha
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def eventFilter(self, obj, event):
        # Auto-resize when parent resizes
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.resize(event.size())
        return super().eventFilter(obj, event)

    def show_loading(self):
        self.raise_()
        self.show()

    def hide_loading(self):
        self.hide()
