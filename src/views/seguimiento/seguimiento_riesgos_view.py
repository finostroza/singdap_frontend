from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class SeguimientoRiesgosView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Seguimiento de Riesgos")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        
        subtitle = QLabel("Modulo en desarrollo - Seguimiento de Riesgos de RAT y EIPD")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setStyleSheet("font-size: 16px; color: #666;")
        
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
