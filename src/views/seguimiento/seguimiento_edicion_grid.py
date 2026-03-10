from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QHeaderView, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from utils import icon

class SeguimientoEdicionGrid(QWidget):
    # Signal: row_index, data, should_expand (True for +, False for -)
    expand_requested = Signal(int, dict, bool)
    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)
        
        # Header with back button - Trazabilidad style
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 0)
        
        self.btn_back = QPushButton()
        self.btn_back.setIcon(icon("src/resources/icons/arrow-left.svg"))
        self.btn_back.setFixedSize(36, 36)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border-radius: 18px;
                border: 1px solid #e2e8f0;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        
        title_box = QVBoxLayout()
        self.title_label = QLabel("Edición de Riesgos")
        self.title_label.setStyleSheet("color: #0f172a; font-size: 20px; font-weight: bold;")
        self.subtitle_label = QLabel("Gestione el detalle de los riesgos identificados")
        self.subtitle_label.setStyleSheet("color: #64748b; font-size: 13px;")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        
        header_layout.addWidget(self.btn_back)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        
        # Table - Trazabilidad style
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Nombre del Riesgo", "Descripción del Riesgo", "Acciones"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Description stretches everything else
        header.setSectionResizeMode(2, QHeaderView.Fixed) # Only actions is fixed
        self.table.setColumnWidth(2, 60)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e2e8f0;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: bold;
                color: #475569;
                text-align: left;
            }
        """)
        
        self.layout.addWidget(self.table)
        
        # Track expanded states
        self.expanded_rows = {} # map row_index -> bool

    def populate(self, data):
        self.expanded_rows.clear()
        nombre_tratamiento = data.get("nombre_tratamiento", "Sin nombre")
        self.title_label.setText(f"Edición de Riesgos")
        self.subtitle_label.setText(f"Tratamiento: {nombre_tratamiento}")
        
        riesgos = data.get("riesgos", [])
        self.table.setRowCount(len(riesgos))
        
        for row, riesgo in enumerate(riesgos):
            nombre = riesgo.get("nombre_riesgo") or riesgo.get("ambito_codigo", "")
            self.table.setItem(row, 0, QTableWidgetItem(str(nombre)))
            self.table.setItem(row, 1, QTableWidgetItem(str(riesgo.get("descripcion", ""))))
            
            # Button Container
            btn_container = QWidget()
            btn_container.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(0)
            btn_layout.setAlignment(Qt.AlignCenter)
            
            expand_btn = QPushButton("+")
            expand_btn.setFixedSize(28, 28)
            expand_btn.setCursor(Qt.PointingHandCursor)
            expand_btn.setStyleSheet("""
                QPushButton {
                    background-color: #eff6ff;
                    color: #3b82f6;
                    border: 1.5px solid #dbeafe;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 0px 0px 2px 0px; /* Offset for text vertical align */
                }
                QPushButton:hover {
                    background-color: #dbeafe;
                    border-color: #3b82f6;
                }
            """)
            
            rid = riesgo.get("riesgo_id") or riesgo.get("id")
            riesgo["_id_internal"] = str(rid)
            
            expand_btn.clicked.connect(lambda checked=False, r=row, d=riesgo, btn=expand_btn: self._on_expand_clicked(r, d, btn))
            
            btn_layout.addWidget(expand_btn)
            self.table.setCellWidget(row, 2, btn_container)
            
            self.table.item(row, 0).setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.item(row, 1).setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

    def _on_expand_clicked(self, row, data, btn):
        is_expanded = self.expanded_rows.get(row, False)
        new_state = not is_expanded
        self.expanded_rows[row] = new_state
        self.set_button_state(btn, new_state)
        self.expand_requested.emit(row, data, new_state)

    def set_button_state(self, btn, is_expanded):
        if is_expanded:
            btn.setText("-")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #fef2f2;
                    color: #ef4444;
                    border: 1.5px solid #fee2e2;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 0px 0px 2px 0px;
                }
                QPushButton:hover {
                    background-color: #fee2e2;
                    border-color: #ef4444;
                }
            """)
        else:
            btn.setText("+")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #eff6ff;
                    color: #3b82f6;
                    border: 1.5px solid #dbeafe;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 0px 0px 2px 0px;
                }
                QPushButton:hover {
                    background-color: #dbeafe;
                    border-color: #3b82f6;
                }
            """)

    def reset_all_buttons(self, exclude_row=None):
        # Clear states except exclude_row
        old_states = self.expanded_rows.copy()
        self.expanded_rows.clear()
        if exclude_row is not None and exclude_row in old_states:
            self.expanded_rows[exclude_row] = old_states[exclude_row]

        for row in range(self.table.rowCount()):
            if exclude_row is not None and row == exclude_row:
                continue
            btn_container = self.table.cellWidget(row, 2)
            if btn_container:
                btn = btn_container.findChild(QPushButton)
                if btn:
                    self.set_button_state(btn, False)
