from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Block inputs
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def show_loading(self):
        self.resize(self.parent().size())
        self.show()
        self.raise_()
        self.timer.start(50)

    def hide_loading(self):
        self.timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Semi-transparent background
        painter.fillRect(self.rect(), QColor(255, 255, 255, 180))
        
        # Draw Spinner
        painter.translate(self.width() // 2, self.height() // 2)
        painter.rotate(self.angle)
        
        pen = QPen(QColor("#004B8D")) # Brand color (Gobierno blue)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Draw arc
        painter.drawArc(-20, -20, 40, 40, 0, 270 * 16)
        
        painter.end()

    def resizeEvent(self, event):
        self.resize(self.parent().size())
        super().resizeEvent(event)
