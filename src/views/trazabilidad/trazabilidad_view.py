from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QTableWidgetItem, QHeaderView, QStackedWidget,
    QTableWidget, QTabWidget, QDateEdit, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, QDate
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

        # Stack principal: estado 0 = búsqueda, estado 1 = resultados
        self.stack = QStackedWidget()

        # ── ESTADO 0: Vista de búsqueda ────────────────────────────────────
        self.search_state = QWidget()
        search_layout = QVBoxLayout(self.search_state)
        search_layout.setContentsMargins(30, 30, 30, 30)
        search_layout.setSpacing(20)

        # Título principal del módulo
        search_top_bar = QHBoxLayout()
        search_top_bar.addSpacing(56)  # Alineado con el botón "volver" del estado de resultados

        title_wrapper = QVBoxLayout()
        title_0 = QLabel("TRAZABILIDAD")
        title_0.setStyleSheet("color: #0f172a; font-size: 24px; font-weight: bold;")
        subtitle_0 = QLabel(" ")  # Espacio para igualar altura con el estado de resultados
        subtitle_0.setStyleSheet("font-size: 14px;")
        title_wrapper.addWidget(title_0)
        title_wrapper.addWidget(subtitle_0)

        search_top_bar.addLayout(title_wrapper)
        search_top_bar.addStretch()
        search_layout.addLayout(search_top_bar)

        # Tarjeta azul dinámica que muestra el nombre del tab activo
        self.dynamic_header_stack = QStackedWidget()
        self.dynamic_header_stack.setFixedHeight(72)

        # Tarjeta para el tab "Consulta mediante RUN"
        page_tab1 = QWidget()
        page1_layout = QVBoxLayout(page_tab1)
        page1_layout.setContentsMargins(0, 0, 0, 0)
        card1 = QFrame()
        card1.setStyleSheet("background-color: #eff6ff; border-radius: 12px; border: 1px solid #dbeafe;")
        card1_layout = QHBoxLayout(card1)
        card1_layout.setContentsMargins(20, 15, 20, 15)
        lbl1 = QLabel("Consulta Mediante RUN")
        lbl1.setStyleSheet("font-weight: bold; color: #1e40af; font-size: 16px;")
        card1_layout.addWidget(lbl1)
        card1_layout.addStretch()
        page1_layout.addWidget(card1)

        # Tarjeta para el tab "Registro de Solicitudes"
        page_tab2 = QWidget()
        page2_layout = QVBoxLayout(page_tab2)
        page2_layout.setContentsMargins(0, 0, 0, 0)
        card2 = QFrame()
        card2.setStyleSheet("background-color: #eff6ff; border-radius: 12px; border: 1px solid #dbeafe;")
        card2_layout = QHBoxLayout(card2)
        card2_layout.setContentsMargins(20, 15, 20, 15)
        lbl2 = QLabel("Registro de Solicitudes o Reporte de Incidencias")
        lbl2.setStyleSheet("font-weight: bold; color: #1e40af; font-size: 16px;")
        card2_layout.addWidget(lbl2)
        card2_layout.addStretch()
        page2_layout.addWidget(card2)

        self.dynamic_header_stack.addWidget(page_tab1)
        self.dynamic_header_stack.addWidget(page_tab2)
        search_layout.addWidget(self.dynamic_header_stack)

        # El header dinámico sigue al tab activo
        self.main_tabs = QTabWidget()
        self.main_tabs.currentChanged.connect(self.dynamic_header_stack.setCurrentIndex)

        self.main_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
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

        # ── Tab 1: Consulta mediante RUN ───────────────────────────────────
        tab1_search = QWidget()
        tab1_search_layout = QVBoxLayout(tab1_search)
        tab1_search_layout.setAlignment(Qt.AlignCenter)

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

        tab1_search_layout.addWidget(self.card)
        self.main_tabs.addTab(tab1_search, "  Consulta mediante RUN  ")

        # ── Tab 2: Formulario de registro de solicitudes ───────────────────
        tab2_reports = QWidget()
        tab2_reports_layout = QVBoxLayout(tab2_reports)

        # El formulario va centrado horizontalmente
        center_form_layout = QHBoxLayout()
        center_form_layout.addStretch()

        form_card = QFrame()
        form_card.setObjectName("ReportFormCard")
        form_card.setFixedWidth(550)
        form_card.setStyleSheet("""
            QFrame#ReportFormCard {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #e0e6ed;
            }
        """)

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(15)

        # Estilo de etiquetas de campo
        def make_field_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 600; margin-top: 5px;")
            return lbl

        # Estilo compartido para todos los inputs del formulario
        common_style = """
            QWidget {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
                color: #1e293b;
                background-color: white;
            }
            QWidget:focus {
                border: 2px solid #3b82f6;
                background-color: #f8fafc;
            }
        """

        # Fecha de solicitud (solo lectura, se toma del sistema)
        form_layout.addWidget(make_field_label("Fecha de solicitud"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setReadOnly(True)
        self.date_input.setButtonSymbols(QDateEdit.NoButtons)
        self.date_input.setToolTip("Indique fecha de cuando se genera la solicitud")
        self.date_input.setStyleSheet(common_style + "QWidget { background-color: #f1f5f9; color: #64748b; }")
        form_layout.addWidget(self.date_input)

        # Tipo de solicitud
        form_layout.addWidget(make_field_label("Tipo"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Seleccione...", "Solicitud de datos", "Reportar incidencia"])
        self.combo_type.setStyleSheet(common_style + "QComboBox::drop-down { border: none; width: 30px; }")
        form_layout.addWidget(self.combo_type)

        # Descripción libre
        form_layout.addWidget(make_field_label("Descripción de la solicitud"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setFixedHeight(70)
        self.txt_desc.setToolTip("Describa detalladamente la solicitud de datos")
        self.txt_desc.setStyleSheet(common_style)
        form_layout.addWidget(self.txt_desc)

        # Persona responsable (editable, permite buscar o escribir)
        form_layout.addWidget(make_field_label("Persona responsable"))
        self.combo_resp = QComboBox()
        self.combo_resp.setEditable(True)
        self.combo_resp.addItems(["Seleccione...", "Juan Pérez", "María Silva", "Carlos Muñoz", "Ana Rojas", "Pedro Soto"])
        self.combo_resp.setToolTip("Nombre de persona que dará respuesta a la solicitud")
        self.combo_resp.setStyleSheet(common_style + "QComboBox::drop-down { border: none; width: 30px; }")
        form_layout.addWidget(self.combo_resp)

        # Estado de la solicitud
        form_layout.addWidget(make_field_label("Estado de la solicitud"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Seleccione...", "Pendiente", "Resuelta", "Cancelada", "Otro"])
        self.combo_status.setStyleSheet(common_style + "QComboBox::drop-down { border: none; width: 30px; }")
        form_layout.addWidget(self.combo_status)

        # Campo extra que aparece solo si el estado es "Otro"
        self.txt_other_status = QLineEdit()
        self.txt_other_status.setPlaceholderText("Especifique otro estado...")
        self.txt_other_status.setStyleSheet(common_style)
        self.txt_other_status.setVisible(False)
        form_layout.addWidget(self.txt_other_status)

        self.combo_status.currentTextChanged.connect(
            lambda t: self.txt_other_status.setVisible(t == "Otro")
        )

        # Botón de envío
        self.btn_send_report = QPushButton("ENVIAR")
        self.btn_send_report.setCursor(Qt.PointingHandCursor)
        self.btn_send_report.setFixedHeight(50)
        self.btn_send_report.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 4px;
                margin-top: 15px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_send_report.clicked.connect(self._on_send_report)
        form_layout.addWidget(self.btn_send_report)

        center_form_layout.addWidget(form_card)
        center_form_layout.addStretch()

        tab2_reports_layout.addStretch()
        tab2_reports_layout.addLayout(center_form_layout)
        tab2_reports_layout.addStretch()

        self.main_tabs.addTab(tab2_reports, "  Registro de Solicitudes o Reporte de Incidencias  ")

        search_layout.addWidget(self.main_tabs)
        self.stack.addWidget(self.search_state)

        # ── ESTADO 1: Vista de resultados ──────────────────────────────────
        self.results_state = QWidget()
        self.results_layout = QVBoxLayout(self.results_state)
        self.results_layout.setContentsMargins(30, 30, 30, 30)
        self.results_layout.setSpacing(20)

        # Barra superior con botón volver y título
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

        # Tarjeta azul con el RUN consultado y botón refrescar
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

        # Grillas de resultados en tabs
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

        # Tab resultados 1: Consultas personales RIS
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
        self.tabs.addTab(tab1_widget, "  Consulta Datos Personales RIS  ")

        # Tab resultados 2: Consultas por institución
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
        self.tabs.addTab(tab2_widget, "  Consultas realizadas por Instituciones  ")

        self.results_layout.addLayout(top_bar)
        self.results_layout.addWidget(self.summary_card)
        self.results_layout.addWidget(self.tabs)

        self.stack.addWidget(self.results_state)
        self.layout.addWidget(self.stack)

    def _apply_grid_style(self, grid: QTableWidget):
        """Aplica el estilo visual estándar a una grilla de resultados."""
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
        """Conecta botones con acciones y el viewmodel con los manejadores de respuesta."""
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

    # ── Acciones del usuario ───────────────────────────────────────────────

    def on_consultar(self):
        """Valida el RUN ingresado e inicia la consulta al viewmodel."""
        run = self.txt_run_card.text().strip()
        if not run:
            self._show_alert("RUN Requerido", "Debe ingresar un RUN para realizar la consulta.")
            return
        self._last_run = run
        self.lbl_summary_run.setText(f"Consultando RUN: {run}")
        self._clear_grids()
        self.viewmodel.consultar_todo(run)

    def _on_send_report(self):
        """Muestra confirmación al enviar el formulario de solicitud."""
        resp = self.combo_resp.currentText().strip()
        if not resp or resp == "Seleccione...":
            resp = "[PERSONA RESPONSABLE]"

        msg = (
            f'Se enviará correo a {resp}, el cual tendrá como remitente '
            f'e-mail SINGDAP@desarrollosocial.gob.cl, con el ASUNTO: "Tiene un Requerimiento SINGDAP."'
        )

        AlertDialog(
            title="Requerimiento Enviado",
            message=msg,
            icon_path="src/resources/icons/check-circle.svg",
            confirm_text="Cerrar",
            cancel_text=None,
            parent=self
        ).exec()

    def _on_refresh(self):
        """Repite la última consulta sin salir de la vista de resultados."""
        if self._last_run:
            self.lbl_summary_run.setText(f"Consultando RUN: {self._last_run}")
            self._clear_grids()
            self.viewmodel.consultar_todo(self._last_run)

    def _go_back(self):
        """Vuelve a la pantalla de búsqueda."""
        self.stack.setCurrentIndex(0)

    def _clear_grids(self):
        """Limpia las grillas y resetea los títulos de los tabs de resultados."""
        self.grid_consultas.setRowCount(0)
        self.grid_instituciones.setRowCount(0)
        self.tabs.setTabText(0, "  Consulta Datos Personales RIS  ")
        self.tabs.setTabText(1, "  Consultas realizadas por Instituciones  ")

    # ── Llenado de grillas con datos del viewmodel ─────────────────────────

    def populate_grid_consultas(self, results):
        """Recibe los resultados de consultas personales y los muestra en la grilla."""
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)

        self.lbl_summary_run.setText(f"Resultados para RUN: {self._last_run}")
        self.tabs.setTabText(0, f"  Consulta Datos Personales RIS ({len(results)})  ")

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
        """Recibe los resultados por institución y los muestra en la grilla."""
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)

        self.lbl_summary_run.setText(f"Resultados para RUN: {self._last_run}")
        self.tabs.setTabText(1, f"  Consultas realizadas por Instituciones ({len(results)})  ")

        self.grid_instituciones.setRowCount(len(results))
        for i, item in enumerate(results):
            self.grid_instituciones.setItem(i, 0, self._cell(item.get("institucion", "N/A")))
            self.grid_instituciones.setItem(i, 1, self._cell(item.get("periodo", "")))
            cantidad = self._cell(str(item.get("cantidad", 0)))
            cantidad.setTextAlignment(Qt.AlignCenter)
            self.grid_instituciones.setItem(i, 2, cantidad)

    def _handle_instituciones_error(self, message):
        """Marca el tab de instituciones con error si la consulta falla."""
        self.tabs.setTabText(1, "  Consultas realizadas por Instituciones (error)  ")
        print(f"[Trazabilidad] Error al cargar instituciones: {message}")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _cell(self, text: str) -> QTableWidgetItem:
        """Crea una celda de tabla con el texto centrado."""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def handle_loading(self, is_loading: bool):
        """Activa/desactiva los botones de consulta mientras se carga."""
        self.btn_consultar_card.setEnabled(not is_loading)
        self.btn_force_refresh.setEnabled(not is_loading)
        if is_loading:
            self.btn_consultar_card.setText("CONSULTANDO...")
            self.setCursor(Qt.WaitCursor)
        else:
            self.btn_consultar_card.setText("CONSULTAR")
            self.setCursor(Qt.ArrowCursor)

    def handle_error(self, message: str):
        """Muestra un diálogo de error genérico."""
        self._show_alert("Error", message)

    def handle_validation_error(self, message: str):
        """Muestra un diálogo de error de validación."""
        self._show_alert("Validación", message)

    def _show_alert(self, title: str, message: str):
        """Abre el diálogo estándar de alerta del sistema."""
        AlertDialog(
            title=title,
            message=message,
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Entendido",
            cancel_text=None,
            parent=self
        ).exec()

    def show_detail(self, row_data):
        """Abre el diálogo de detalle de una fila de consulta API."""
        api_name = row_data.get("api_nombre", "Detalle de API") if isinstance(row_data, dict) else "Detalle de API"
        dialog = ApiDetailDialog(row_data, title=api_name, parent=self)
        dialog.exec()
