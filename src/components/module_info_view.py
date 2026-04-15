from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal

class ModuleInfoView(QWidget):
    back_requested = Signal()

    def __init__(self, title, content_html, footer_text=None):
        super().__init__()
        self.title_text = title
        self.content_html = content_html
        self.footer_text = footer_text or (
            "Este sistema es una de las medidas adoptadas por la División de Información Social para avanzar en la "
            "responsabilidad proactiva, fortaleciendo la transparencia, la seguridad de la información y el cumplimiento "
            "normativo, en línea con la actualización de la Ley N° 19.628, a través de la Ley N° 21.719 sobre protección de datos personales."
        )
        self.setObjectName("moduleInfoView")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header with back button
        header_layout = QHBoxLayout()
        back_btn = QPushButton("← Volver")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #004a99;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)
        header_layout.addStretch()
        layout.addLayout(header_layout)

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
            font-size: 28px;
            font-weight: bold;
            color: #004a99;
            margin-bottom: 20px;
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

        # Doblar el espacio antes del pie de página
        card_layout.addSpacing(50)

        # Footer / Legal section
        footer_label = QLabel(self.footer_text)
        footer_label.setWordWrap(True)
        footer_label.setStyleSheet("""
            font-size: 14px; 
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
