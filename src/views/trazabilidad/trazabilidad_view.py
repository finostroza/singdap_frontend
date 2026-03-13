from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QTableWidgetItem, QHeaderView, QStackedWidget,
    QTableWidget, QTabWidget
)
from PySide6.QtCore import Qt
from src.viewmodels.trazabilidad_viewmodel import TrazabilidadViewModel
from src.views.trazabilidad.api_detail_dialog import ApiDetailDialog
from src.components.alert_dialog import AlertDialog
from utils import icon


class TrazabilidadView(QWidget):
    def __init__(self):
        super().__init__()
        self._last_run = ""
        self.viewmodel = TrazabilidadViewModel()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # ── ESTADO 0: Card de búsqueda ────────────────────────────────────
        self.search_state = QWidget()
        search_layout = QVBoxLayout(self.search_state)
        search_layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("TraceabilityCard")
        self.card.setFixedWidth(480)
        self.card.setStyleSheet("""
            QFrame#TraceabilityCard {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #e0e6ed;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(50, 50, 50, 50)
        card_layout.setSpacing(20)

        title = QLabel("Trazabilidad")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a2332; font-size: 26px; font-weight: bold;")

        subtitle = QLabel("Acceso mediante RUN")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 15px; margin-bottom: 2px;")

        label_run = QLabel("Ingrese RUN")
        label_run.setAlignment(Qt.AlignLeft)
        label_run.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 600;")

        self.txt_run_card = QLineEdit()
        self.txt_run_card.setPlaceholderText("Ej: 12345678-9")
        self.txt_run_card.setFixedHeight(50)
        self.txt_run_card.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 5px 15px;
                font-size: 16px;
                color: #1e293b;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #f8fafc;
            }
        """)

        self.btn_consultar_card = QPushButton("CONSULTAR")
        self.btn_consultar_card.setCursor(Qt.PointingHandCursor)
        self.btn_consultar_card.setFixedHeight(55)
        self.btn_consultar_card.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 4px;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(label_run)
        card_layout.addWidget(self.txt_run_card)
        card_layout.addWidget(self.btn_consultar_card)

        search_layout.addWidget(self.card)
        self.stack.addWidget(self.search_state)

        # ── ESTADO 1: Resultados ─────────────────────────────────────────
        self.results_state = QWidget()
        self.results_layout = QVBoxLayout(self.results_state)
        self.results_layout.setContentsMargins(30, 30, 30, 30)
        self.results_layout.setSpacing(20)

        # Barra superior
        top_bar = QHBoxLayout()
        title_group = QHBoxLayout()

        self.btn_back = QPushButton()
        self.btn_back.setIcon(icon("src/resources/icons/arrow-left.svg"))
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border-radius: 20px;
                border: 1px solid #e2e8f0;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)

        res_title_layout = QVBoxLayout()
        res_title = QLabel("Trazabilidad")
        res_title.setStyleSheet("color: #0f172a; font-size: 24px; font-weight: bold;")
        res_subtitle = QLabel("Resultados de consulta por RUN")
        res_subtitle.setStyleSheet("color: #64748b; font-size: 14px;")
        res_title_layout.addWidget(res_title)
        res_title_layout.addWidget(res_subtitle)

        title_group.addWidget(self.btn_back)
        title_group.addSpacing(16)
        title_group.addLayout(res_title_layout)

        top_bar.addLayout(title_group)
        top_bar.addStretch()

        # Tarjeta de resumen con RUN y botón refrescar
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet(
            "background-color: #eff6ff; border-radius: 12px; border: 1px solid #dbeafe;"
        )
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(20, 15, 20, 15)

        self.lbl_summary_run = QLabel("RUN: -")
        self.lbl_summary_run.setStyleSheet("font-weight: bold; color: #1e40af; font-size: 16px;")
        summary_layout.addWidget(self.lbl_summary_run)
        summary_layout.addStretch()

        self.btn_force_refresh = QPushButton("  REFRESCAR")
        self.btn_force_refresh.setIcon(icon("src/resources/icons/search.svg"))
        self.btn_force_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_force_refresh.setFixedHeight(40)
        self.btn_force_refresh.setFixedWidth(150)
        self.btn_force_refresh.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        summary_layout.addWidget(self.btn_force_refresh)

        # ── QTabWidget con dos secciones ──────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 0 12px 12px 12px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f1f5f9;
                color: #475569;
                padding: 10px 24px;
                border: 1px solid #e2e8f0;
                border-bottom: none;
                border-radius: 8px 8px 0 0;
                font-weight: 600;
                font-size: 13px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #1e40af;
                border-bottom: 2px solid #3b82f6;
            }
            QTabBar::tab:hover:!selected { background-color: #e2e8f0; }
        """)

        # Tab 1 – Consultas API
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        tab1_layout.setContentsMargins(16, 16, 16, 16)

        self.grid_consultas = QTableWidget()
        self.grid_consultas.setColumnCount(5)
        self.grid_consultas.setHorizontalHeaderLabels(
            ["Origen", "Nombre API", "Tipo", "Fecha Consulta", "Acciones"]
        )
        self._apply_grid_style(self.grid_consultas)
        h1 = self.grid_consultas.horizontalHeader()
        h1.setSectionResizeMode(QHeaderView.Fixed)
        h1.setSectionResizeMode(1, QHeaderView.Stretch)
        self.grid_consultas.setColumnWidth(0, 140)
        self.grid_consultas.setColumnWidth(2, 110)
        self.grid_consultas.setColumnWidth(3, 200)
        self.grid_consultas.setColumnWidth(4, 160)
        self.grid_consultas.verticalHeader().setVisible(False)
        self.grid_consultas.verticalHeader().setDefaultSectionSize(56)

        tab1_layout.addWidget(self.grid_consultas)
        self.tabs.addTab(tab1_widget, "  Consultas API  ")

        # Tab 2 – Por Institución
        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout(tab2_widget)
        tab2_layout.setContentsMargins(16, 16, 16, 16)

        self.grid_instituciones = QTableWidget()
        self.grid_instituciones.setColumnCount(3)
        self.grid_instituciones.setHorizontalHeaderLabels(["Institución", "Período", "N° Consultas"])
        self._apply_grid_style(self.grid_instituciones)
        h2 = self.grid_instituciones.horizontalHeader()
        h2.setSectionResizeMode(QHeaderView.Fixed)
        h2.setSectionResizeMode(0, QHeaderView.Stretch)
        self.grid_instituciones.setColumnWidth(1, 160)
        self.grid_instituciones.setColumnWidth(2, 130)
        self.grid_instituciones.verticalHeader().setVisible(False)
        self.grid_instituciones.verticalHeader().setDefaultSectionSize(44)

        tab2_layout.addWidget(self.grid_instituciones)
        self.tabs.addTab(tab2_widget, "  Por Institución  ")

        self.results_layout.addLayout(top_bar)
        self.results_layout.addWidget(self.summary_card)
        self.results_layout.addWidget(self.tabs)

        self.stack.addWidget(self.results_state)
        self.layout.addWidget(self.stack)

    def _apply_grid_style(self, grid: QTableWidget):
        grid.setAlternatingRowColors(True)
        grid.setSelectionBehavior(QTableWidget.SelectRows)
        grid.setEditTriggers(QTableWidget.NoEditTriggers)
        grid.setShowGrid(False)
        grid.setWordWrap(True)
        grid.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
                color: #475569;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: bold;
                color: #475569;
            }
        """)

    def connect_signals(self):
        self.btn_consultar_card.clicked.connect(self.on_consultar)
        self.txt_run_card.returnPressed.connect(self.on_consultar)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_force_refresh.clicked.connect(self._on_refresh)

        self.viewmodel.on_loading.connect(self.handle_loading)
        self.viewmodel.on_error.connect(self.handle_error)
        self.viewmodel.on_validation_error.connect(self.handle_validation_error)
        self.viewmodel.on_results_ready.connect(self.populate_grid_consultas)
        self.viewmodel.on_instituciones_ready.connect(self.populate_grid_instituciones)
        self.viewmodel.on_instituciones_error.connect(self._handle_instituciones_error)

    # ── Acciones del usuario ──────────────────────────────────────────────

    def on_consultar(self):
        run = self.txt_run_card.text().strip()
        if not run:
            self._show_alert("RUN Requerido", "Debe ingresar un RUN para realizar la consulta.")
            return
        self._last_run = run
        self.lbl_summary_run.setText(f"Consultando RUN: {run}")
        self._clear_grids()
        self.viewmodel.consultar_todo(run)

    def _on_refresh(self):
        if self._last_run:
            self.lbl_summary_run.setText(f"Consultando RUN: {self._last_run}")
            self._clear_grids()
            self.viewmodel.consultar_todo(self._last_run)

    def _go_back(self):
        self.stack.setCurrentIndex(0)

    def _clear_grids(self):
        self.grid_consultas.setRowCount(0)
        self.grid_instituciones.setRowCount(0)
        self.tabs.setTabText(0, "  Consultas API  ")
        self.tabs.setTabText(1, "  Por Institución  ")

    # ── Poblado de grillas ────────────────────────────────────────────────

    def populate_grid_consultas(self, results):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)

        self.lbl_summary_run.setText(f"Resultados para RUN: {self._last_run}")
        self.tabs.setTabText(0, f"  Consultas API ({len(results)})  ")

        self.grid_consultas.setRowCount(len(results))
        for i, row_data in enumerate(results):
            self.grid_consultas.setItem(i, 0, self._cell(row_data.get("origen", "")))
            self.grid_consultas.setItem(i, 1, self._cell(row_data.get("api_nombre", "")))
            self.grid_consultas.setItem(i, 2, self._cell(row_data.get("tipo", "API")))
            self.grid_consultas.setItem(i, 3, self._cell(row_data.get("fecha_consulta", "")))

            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(6, 8, 6, 8)
            btn_layout.setAlignment(Qt.AlignCenter)

            btn_detail = QPushButton(" Ver Contenido")
            btn_detail.setIcon(icon("src/resources/icons/file.svg"))
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.setFixedHeight(34)
            btn_detail.setMinimumWidth(130)
            btn_detail.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border-radius: 8px;
                    font-size: 13px;
                    border: none;
                }
                QPushButton:hover { background-color: #2563eb; }
            """)
            btn_detail.clicked.connect(lambda checked=False, row=row_data: self.show_detail(row))
            btn_layout.addWidget(btn_detail)

            self.grid_consultas.setCellWidget(i, 4, btn_container)

    def populate_grid_instituciones(self, results):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)

        self.lbl_summary_run.setText(f"Resultados para RUN: {self._last_run}")
        self.tabs.setTabText(1, f"  Por Institución ({len(results)})  ")

        self.grid_instituciones.setRowCount(len(results))
        for i, item in enumerate(results):
            self.grid_instituciones.setItem(i, 0, self._cell(item.get("institucion", "N/A")))
            self.grid_instituciones.setItem(i, 1, self._cell(item.get("periodo", "")))
            cantidad = self._cell(str(item.get("cantidad", 0)))
            cantidad.setTextAlignment(Qt.AlignCenter)
            self.grid_instituciones.setItem(i, 2, cantidad)

    def _handle_instituciones_error(self, message):
        self.tabs.setTabText(1, "  Por Institución (error)  ")
        print(f"[Trazabilidad] Error tab instituciones: {message}")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _cell(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def handle_loading(self, is_loading: bool):
        self.btn_consultar_card.setEnabled(not is_loading)
        self.btn_force_refresh.setEnabled(not is_loading)
        if is_loading:
            self.btn_consultar_card.setText("CONSULTANDO...")
            self.setCursor(Qt.WaitCursor)
        else:
            self.btn_consultar_card.setText("CONSULTAR")
            self.setCursor(Qt.ArrowCursor)

    def handle_error(self, message: str):
        self._show_alert("Error", message)

    def handle_validation_error(self, message: str):
        self._show_alert("Validación", message)

    def _show_alert(self, title: str, message: str):
        AlertDialog(
            title=title,
            message=message,
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Entendido",
            cancel_text=None,
            parent=self
        ).exec()

    def show_detail(self, row_data):
        api_name = row_data.get("api_nombre", "Detalle de API") if isinstance(row_data, dict) else "Detalle de API"
        dialog = ApiDetailDialog(row_data, title=api_name, parent=self)
        dialog.exec()
