from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class HomeView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("homeView")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Main Card / Container
        card = QFrame()
        card.setObjectName("homeCard")
        card.setStyleSheet("""
            #homeCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(24)

        # Title
        title_label = QLabel("Bienvenida/o al SINGDAP")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #004a99;
            margin-bottom: 10px;
        """)
        card_layout.addWidget(title_label)

        # Subtitle / Description
        subtitle = "Sistema de Inventario y Gestión de Datos Personales"
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 18px; color: #555; font-weight: 500;")
        card_layout.addWidget(subtitle_label)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        card_layout.addWidget(line)

        # Main Text
        main_text = (
            "Aquí podrá acceder al inventario de datos, al Registro de Actividades de Tratamiento (RAT) "
            "y la trazabilidad de los datos de los ciudadanos, de la información del Registro de Información Social (RIS).<br><br>"
            "Asimismo, podrá visualizar los riesgos identificados, los controles implementados y las Evaluaciones "
            "de Impacto a la Protección de Datos, facilitando el monitoreo y el cumplimiento en materia de protección de datos."
        )
        main_label = QLabel(main_text)
        main_label.setWordWrap(True)
        main_label.setStyleSheet("font-size: 16px; line-height: 1.6; color: #333;")
        card_layout.addWidget(main_label)

        # Components section
        comp_title = QLabel("Componentes del sistema:")
        comp_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #004a99; margin-top: 10px;")
        card_layout.addWidget(comp_title)

        components_html = """
        <ul style="margin-left: 0px; padding-left: 20px; color: #333; font-size: 15px;">
            <li style="margin-bottom: 15px;">
                <b>Inventario de activos de datos personales.</b><br>
                <span style="color: #666;">Que permite identificar y clasificar los datos personales que se administran en el RIS.</span>
            </li>
            <li style="margin-bottom: 15px;">
                <b>Registro de Actividades de Tratamiento (RAT).</b><br>
                <span style="color: #666;">Como mecanismo estructurado para documentar y controlar los tratamientos de datos realizados con los datos personales.</span>
            </li>
            <li style="margin-bottom: 15px;">
                <b>Trazabilidad por ciudadano.</b><br>
                <span style="color: #666;">Asegurando visibilidad sobre el uso y circulación de los datos de los ciudadanos contenidos en el RIS.</span>
            </li>
            <li style="margin-bottom: 15px;">
                <b>Evaluación de Impacto en Protección de Datos (EIPD).</b><br>
                <span style="color: #666;">Para identificar y mitigar riesgos asociados al tratamiento de datos personales, especialmente en iniciativas de alto impacto.</span>
            </li>
            <li style="margin-bottom: 15px;">
                <b>Seguimiento de los riesgos identificados en los RAT o EIPD.</b><br>
                <span style="color: #666;">Asegurando su monitoreo continuo lo que permite gestionar planes de mitigación y verificar la implementación efectiva de medidas de control.</span>
            </li>
        </ul>
        """
        comp_label = QLabel(components_html)
        comp_label.setWordWrap(True)
        card_layout.addWidget(comp_label)

        # Footer / Legal law section
        footer_text = (
            "Este sistema es una de las medidas adoptadas por la División de Información Social para avanzar en la "
            "responsabilidad proactiva, fortaleciendo la transparencia, la seguridad de la información y el cumplimiento "
            "normativo, en línea con la actualización de la Ley N° 19.628, a través de la Ley N° 21.719 sobre protección de datos personales."
        )
        footer_label = QLabel(footer_text)
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
