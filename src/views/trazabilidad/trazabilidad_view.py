from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFrame, QMessageBox, QTableWidgetItem, QHeaderView, QStackedWidget
)
from PySide6.QtCore import Qt
from src.viewmodels.trazabilidad_viewmodel import TrazabilidadViewModel
from src.views.trazabilidad.api_detail_dialog import ApiDetailDialog
from PySide6.QtWidgets import QTableWidget
from utils import icon

class TrazabilidadView(QWidget):
    def __init__(self):
        super().__init__()
        self.viewmodel = TrazabilidadViewModel()
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        # Principal layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked Widget for States
        self.stack = QStackedWidget()
        
        # --- STATE 0: Centered Search ---
        self.search_state = QWidget()
        search_layout = QVBoxLayout(self.search_state)
        search_layout.setAlignment(Qt.AlignCenter)
        
        # Card Container
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
        
        # Title
        title = QLabel("Trazabilidad Básica")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a2332; font-size: 26px; font-weight: bold;")
        
        # Subtitle
        subtitle = QLabel("Acceso mediante RUN")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 15px; margin-bottom: 2px;")

        label_run = QLabel("Ingrese RUN")
        label_run.setAlignment(Qt.AlignLeft)
        label_run.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 600; margin-bottom: 0px;")
        
        # Input Field
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
        
        # Button
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
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(label_run)
        card_layout.addWidget(self.txt_run_card)
        card_layout.addWidget(self.btn_consultar_card)
        
        search_layout.addWidget(self.card)
        self.stack.addWidget(self.search_state)
        
        # --- STATE 1: Results Page (Top Search + Grid) ---
        self.results_state = QWidget()
        self.results_layout = QVBoxLayout(self.results_state)
        self.results_layout.setContentsMargins(30, 30, 30, 30)
        self.results_layout.setSpacing(25)
        
        # Top Bar (Header & Search)
        top_bar = QHBoxLayout()
        
        # Back Button + Title
        title_group = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setIcon(icon("src/resources/icons/arrow-left.svg")) # Using arrow-left.svg
        self.btn_back.setFixedSize(40, 40)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border-radius: 20px;
                border: 1px solid #e2e8f0;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        
        res_title_layout = QVBoxLayout()
        res_title = QLabel("Resultados de Trazabilidad")
        res_title.setStyleSheet("color: #0f172a; font-size: 24px; font-weight: bold;")
        res_subtitle = QLabel("Mostrando resultados para el RUN consultado")
        res_subtitle.setStyleSheet("color: #64748b; font-size: 14px;")
        res_title_layout.addWidget(res_title)
        res_title_layout.addWidget(res_subtitle)
        
        title_group.addWidget(self.btn_back)
        title_group.addLayout(res_title_layout)
        
        top_bar.addLayout(title_group)
        top_bar.addStretch()
        
        # Mini Search Box
        self.mini_search_input = QLineEdit()
        self.mini_search_input.setPlaceholderText("Cambiar RUN...")
        self.mini_search_input.setFixedWidth(250)
        self.mini_search_input.setFixedHeight(40)
        self.mini_search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding-left: 10px;
                background-color: #f8fafc;
            }
        """)
        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(icon("src/resources/icons/search.svg"))
        self.btn_refresh.setFixedSize(40, 40)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        
        top_bar.addWidget(self.mini_search_input)
        top_bar.addWidget(self.btn_refresh)
        
        # Summary Box
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #eff6ff; border-radius: 12px; border: 1px solid #dbeafe;")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(20, 15, 20, 15)
        
        self.lbl_summary_run = QLabel("RUN: -")
        self.lbl_summary_run.setStyleSheet("font-weight: bold; color: #1e40af; font-size: 16px;")
        summary_layout.addWidget(self.lbl_summary_run)
        summary_layout.addStretch()
        
        # Explicit Refresh Button
        self.btn_force_refresh = QPushButton(" REFRESCAR DATOS")
        self.btn_force_refresh.setIcon(icon("src/resources/icons/search_white.svg"))
        self.btn_force_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_force_refresh.setFixedHeight(40)
        self.btn_force_refresh.setFixedWidth(180)
        self.btn_force_refresh.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        summary_layout.addWidget(self.btn_force_refresh)
        
        # Grid
        self.grid = QTableWidget()
        self.grid.setColumnCount(5)
        self.grid.setHorizontalHeaderLabels(["Origen", "Nombre API", "Tipo", "Fecha Consulta", "Acciones"])
        
        # Proportions
        header = self.grid.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch) # API Name stretches
        
        self.grid.setColumnWidth(0, 140) # Origen
        self.grid.setColumnWidth(2, 110) # Tipo
        self.grid.setColumnWidth(3, 200) # Fecha
        self.grid.setColumnWidth(4, 180) # Acciones
        
        # Row height for buttons
        self.grid.verticalHeader().setVisible(False)
        self.grid.verticalHeader().setDefaultSectionSize(64) # Ample space for buttons
        
        self.grid.setAlternatingRowColors(True)
        self.grid.setSelectionBehavior(QTableWidget.SelectRows)
        self.grid.setEditTriggers(QTableWidget.NoEditTriggers)
        self.grid.setShowGrid(False)
        self.grid.setWordWrap(True)
        self.grid.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 0px; 
                border-bottom: 1px solid #f1f5f9;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: bold;
                color: #475569;
            }
        """)
        
        self.results_layout.addLayout(top_bar)
        self.results_layout.addWidget(self.summary_card)
        self.results_layout.addWidget(self.grid)
        
        self.stack.addWidget(self.results_state)
        self.layout.addWidget(self.stack)

    def connect_signals(self):
        self.btn_consultar_card.clicked.connect(self.on_consultar)
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_force_refresh.clicked.connect(self.on_refresh)
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.txt_run_card.returnPressed.connect(self.on_consultar)
        self.mini_search_input.returnPressed.connect(self.on_refresh)
        
        self.viewmodel.on_loading.connect(self.handle_loading)
        self.viewmodel.on_error.connect(self.handle_error)
        self.viewmodel.on_validation_error.connect(self.handle_validation_error)
        self.viewmodel.on_results_ready.connect(self.populate_grid)
        
    def on_consultar(self):
        run = self.txt_run_card.text()
        self.lbl_summary_run.setText(f"Consultando RUN: {run}")
        self.viewmodel.consultar_trazabilidad(run)
        
    def on_refresh(self):
        run = self.mini_search_input.text()
        if run:
            self.lbl_summary_run.setText(f"Consultando RUN: {run}")
            self.viewmodel.consultar_trazabilidad(run)
        
    def populate_grid(self, results):
        if not results:
            QMessageBox.information(self, "Sin resultados", "No se encontraron datos para el RUN consultado.")
            return

        if self.stack.currentIndex() == 0:
            self.mini_search_input.setText(self.txt_run_card.text())
            self.stack.setCurrentIndex(1)
        
        current_run = self.mini_search_input.text()
        self.lbl_summary_run.setText(f"Resultados para RUN: {current_run}")
        
        self.grid.setRowCount(len(results))
        for i, row_data in enumerate(results):
            self.grid.setItem(i, 0, self._create_item(row_data.get("origen", "")))
            self.grid.setItem(i, 1, self._create_item(row_data.get("api_nombre", "")))
            self.grid.setItem(i, 2, self._create_item(row_data.get("tipo", "API")))
            self.grid.setItem(i, 3, self._create_item(row_data.get("fecha_consulta", "")))
            
            # Action Button
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(5, 5, 5, 5) 
            btn_layout.setSpacing(0)
            btn_layout.setAlignment(Qt.AlignCenter)
            
            btn_detail = QPushButton(" Ver Contenido")
            btn_detail.setIcon(icon("src/resources/icons/file.svg"))
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.setFixedHeight(34)
            btn_detail.setMinimumWidth(150)
            btn_detail.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border-radius: 8px;
                    font-size: 13px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            btn_detail.clicked.connect(lambda checked=False, data=row_data.get("response_payload"): self.show_detail(data))
            btn_layout.addWidget(btn_detail)
            
            self.grid.setCellWidget(i, 4, btn_container)

    def _create_item(self, text):
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignCenter)
        return it

    def handle_loading(self, is_loading):
        self.btn_consultar_card.setEnabled(not is_loading)
        self.btn_refresh.setEnabled(not is_loading)
        if is_loading:
            self.btn_consultar_card.setText("CONSULTANDO...")
            self.setCursor(Qt.WaitCursor)
        else:
            self.btn_consultar_card.setText("CONSULTAR AHORA")
            self.setCursor(Qt.ArrowCursor)
            
    def handle_error(self, message):
        QMessageBox.critical(self, "Error", message)
        
    def handle_validation_error(self, message):
        QMessageBox.warning(self, "Validación", message)

    def show_detail(self, data):
        dialog = ApiDetailDialog(data, parent=self)
        dialog.exec()
