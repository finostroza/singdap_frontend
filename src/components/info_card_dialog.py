from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class InfoCardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Información del Módulo")
        self.setMinimumSize(850, 650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Card / Container
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(24)

        # Title
        title_label = QLabel("Sistema de Inventario y Gestión de Datos Personales - SINGDAP")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #004a99;
            border: none;
        """)
        card_layout.addWidget(title_label)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px; border: none;")
        card_layout.addWidget(line)

        # Main Content
        content_text = """
        <div style="font-size: 15px; color: #333; line-height: 1.6;">
            <p><b>Inventario.</b><br>
            Catastro de activos de datos personales, bases, sistemas, archivos y repositorios gestionados por la institución.</p>

            <p style="font-size: 18px; font-weight: bold; color: #004a99; margin-top: 20px;">¿Qué es el Inventario?</p>

            <p>El Inventario es el registro estructurado de los activos de datos que existen en la institución. Incluye, entre otros elementos, bases de datos, sistemas, archivos, registros y otros repositorios que contienen o utilizan datos personales.</p>
            
            <p>Su objetivo es entregar una visión general y organizada de los recursos de información disponibles, permitiendo identificar qué activos existen, quiénes son responsables de ellos, qué nivel de confidencialidad poseen, en qué estado se encuentran y en qué unidad se administran.</p>
            
            <p>Este módulo constituye una base para la gobernanza de datos, ya que permite conocer el universo de activos institucionales y apoyar procesos de control, priorización, resguardo, interoperabilidad y mejora continua.</p>
        </div>
        """
        content_label = QLabel(content_text)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("border: none;")
        card_layout.addWidget(content_label)

        # Footer / Legal section
        footer_text = (
            "Este sistema es una de las medidas adoptadas por la División de Información Social para avanzar en la "
            "responsabilidad proactiva, fortaleciendo la transparencia, la seguridad de la información y el cumplimiento "
            "normativo, en línea con la actualización de la Ley N° 19.628, a través de la Ley N° 21.719 sobre protección de datos personales."
        )
        footer_label = QLabel(footer_text)
        footer_label.setWordWrap(True)
        footer_label.setStyleSheet("""
            font-size: 13px; 
            color: #666; 
            font-style: italic; 
            background-color: #f9f9f9; 
            padding: 20px; 
            border-left: 5px solid #004a99;
            border-radius: 0px;
        """)
        card_layout.addWidget(footer_label)
        
        card_layout.addStretch()

        # Wrap in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(card)
        
        layout.addWidget(scroll)

        # Close button
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
        
        footer_btn_layout = QVBoxLayout()
        footer_btn_layout.addWidget(close_btn, 0, Qt.AlignRight)
        layout.addLayout(footer_btn_layout)
