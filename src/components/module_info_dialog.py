from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt

class ModuleInfoDialog(QDialog):
    def __init__(self, title, content_html, footer_text=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Información del Módulo")
        self.setMinimumSize(900, 700)
        
        self.title_text = title
        self.content_html = content_html
        self.footer_text = footer_text or (
            "Este sistema es una de las medidas adoptadas por la División de Información Social para avanzar en la "
            "responsabilidad proactiva, fortaleciendo la transparencia, la seguridad de la información y el cumplimiento "
            "normativo, en línea con la actualización de la Ley N° 19.628, a través de la Ley N° 21.719 sobre protección de datos personales."
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Main Card / Container
        card = QFrame()
        card.setObjectName("infoCard")
        card.setStyleSheet("""
            #infoCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(24)

        # Title
        title_label = QLabel(self.title_text)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-size: 26px;
            font-weight: bold;
            color: #004a99;
            margin-bottom: 10px;
        """)
        card_layout.addWidget(title_label)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        card_layout.addWidget(line)

        # Main Content
        content_label = QLabel(self.content_html)
        content_label.setWordWrap(True)
        card_layout.addWidget(content_label)

        # Spacing before footer
        card_layout.addSpacing(30)

        # Footer / Legal section
        footer_label = QLabel(self.footer_text)
        footer_label.setWordWrap(True)
        footer_label.setStyleSheet("""
            font-size: 13px; 
            color: #777; 
            font-style: italic; 
            background-color: #f9f9f9; 
            padding: 15px; 
            border-left: 4px solid #004a99;
        """)
        card_layout.addWidget(footer_label)
        
        card_layout.addStretch()

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(card)
        
        layout.addWidget(scroll)

        # Close button at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setFixedWidth(100)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                padding: 8px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
