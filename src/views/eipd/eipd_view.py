from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QScrollArea,
    QFormLayout,
    QLineEdit,
    QComboBox,
)
from PySide6.QtCore import Qt
from src.components.loading_overlay import LoadingOverlay


class EipdView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

        self.setObjectName("eipdView")

        # ===============================
        # Layout principal
        # ===============================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)

        # ===============================
        # Tabs (mismo estilo ActivoDialog)
        # ===============================
        self.tabs = QTabWidget()
        self.tabs.setObjectName("dialogTabs")

        self.tabs.addTab(self._wrap_scroll(self._tab_nivel_1()), "Nivel 1 · RAT")
        self.tabs.addTab(self._wrap_scroll(self._tab_nivel_2()), "Nivel 2 · Detalle RAT")
        self.tabs.addTab(self._wrap_scroll(self._tab_nivel_3()), "Nivel 3 · Evaluación")
        self.tabs.addTab(self._wrap_scroll(self._tab_riesgos()), "Riesgos")
        self.tabs.addTab(self._wrap_scroll(self._tab_mitigacion()), "Mitigación")
        self.tabs.addTab(self._wrap_scroll(self._tab_administracion()), "Administración")

        main_layout.addWidget(self.tabs)

        # ===============================
        # Footer
        # ===============================
        footer = QHBoxLayout()
        footer.addStretch()

        save_btn = QPushButton("Guardar Evaluación EIPD")
        save_btn.setObjectName("primaryButton")
        footer.addWidget(save_btn)

        main_layout.addLayout(footer)

    # ======================================================
    # Helpers (idénticos a ActivoDialog)
    # ======================================================

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def _form(self):
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(16)
        return form

    def _large_input(self, height=120):
        inp = QLineEdit()
        inp.setFixedHeight(height)
        inp.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        inp.setObjectName("formLargeInput")
        return inp

    def _section(self, title: str):
        lbl = QLabel(title)
        lbl.setObjectName("sectionTitle")
        return lbl

    # ======================================================
    # Tabs
    # ======================================================

    def _tab_nivel_1(self):
        w = QWidget()
        l = QVBoxLayout(w)
        f = self._form()

        f.addRow("Identificación del RAT", QLineEdit())
        f.addRow("Marco normativo aplicable", QLineEdit())
        f.addRow("Descripción general del tratamiento", self._large_input())
        f.addRow("Resultados esperados del tratamiento", self._large_input())
        f.addRow("Finalidad(es) del tratamiento", self._large_input())
        f.addRow("Justificación aplicación EIPD", self._large_input())

        l.addLayout(f)
        l.addStretch()
        return w

    def _tab_nivel_2(self):
        w = QWidget()
        l = QVBoxLayout(w)
        f = self._form()

        f.addRow("Categorías de datos personales tratados", self._large_input())
        f.addRow("Titulares de los datos", self._large_input())
        f.addRow("Origen y recolección de los datos", self._large_input())
        f.addRow("Unidades o perfiles con acceso", self._large_input())
        f.addRow("Diagrama de flujo de datos personales", self._large_input(80))
        f.addRow("Alcance y exclusiones del análisis", self._large_input())
        f.addRow("Conclusiones del RAT", self._large_input())

        l.addLayout(f)
        l.addStretch()
        return w

    def _tab_nivel_3(self):
        w = QWidget()
        l = QVBoxLayout(w)

        for title in [
            "Licitud y Lealtad",
            "Finalidad",
            "Proporcionalidad",
            "Calidad",
            "Responsabilidad",
            "Seguridad",
            "Transparencia e Información",
            "Confidencialidad",
            "Coordinación",
        ]:
            l.addWidget(self._section(f"{title} – Nivel 3"))
            f = self._form()
            f.addRow("Criterios de evaluación", self._large_input())
            f.addRow("Resumen del ámbito", self._large_input())
            f.addRow("Nivel de desarrollo", QComboBox())
            f.addRow("Evaluación de riesgos", QComboBox())
            l.addLayout(f)

        l.addStretch()
        return w

    def _tab_riesgos(self):
        w = QWidget()
        l = QVBoxLayout(w)
        f = self._form()

        f.addRow("Matriz de Riesgos Transversales", self._large_input())

        l.addLayout(f)
        l.addStretch()
        return w

    def _tab_mitigacion(self):
        w = QWidget()
        l = QVBoxLayout(w)
        f = self._form()

        f.addRow("Plan de Mitigación y Seguimiento", self._large_input())

        l.addLayout(f)
        l.addStretch()
        return w

    def _tab_administracion(self):
        w = QWidget()
        l = QVBoxLayout(w)
        f = self._form()

        f.addRow("Responsable EIPD", QLineEdit())
        f.addRow("Fecha de revisión", QLineEdit())
        f.addRow("Observaciones internas", self._large_input())

        l.addLayout(f)
        l.addStretch()
        return w
