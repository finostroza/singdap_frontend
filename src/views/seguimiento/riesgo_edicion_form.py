from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QLineEdit, QComboBox, QPushButton,
    QDateEdit, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, QDate, Signal
from datetime import date

class RiesgoEdicionForm(QFrame):
    save_requested = Signal(dict)

    def __init__(self, data):
        super().__init__()
        self.setObjectName("riesgoEdicionForm")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame#riesgoEdicionForm {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-left: 4px solid #3b82f6;
                border-radius: 8px;
                margin: 5px 40px 15px 40px;
            }
            QLabel {
                font-weight: 600;
                color: #334155;
            }
            QTextEdit, QDateEdit, QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px;
                background-color: #f8fafc;
            }
            QTextEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1.5px solid #3b82f6;
                background-color: #ffffff;
            }
        """)
        
        self.data = data
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.acciones_comprometidas = QTextEdit()
        self.acciones_comprometidas.setPlaceholderText("Ingrese acciones comprometidas...")
        self.acciones_comprometidas.setText(data.get("acciones_comprometidas", ""))
        self.acciones_comprometidas.setMaximumHeight(80)
        
        self.acciones_realizadas = QTextEdit()
        self.acciones_realizadas.setPlaceholderText("Ingrese acciones realizadas...")
        self.acciones_realizadas.setText(data.get("acciones_realizadas", ""))
        self.acciones_realizadas.setMaximumHeight(80)
        
        self.fecha_estimada = QDateEdit()
        self.fecha_estimada.setCalendarPopup(True)
        self.fecha_estimada.setDisplayFormat("dd-MM-yyyy")
        f_est = data.get("fecha_estimada_solucion")
        if f_est:
            if isinstance(f_est, str):
                d = QDate.fromString(f_est, "yyyy-MM-dd")
                if d.isValid():
                    self.fecha_estimada.setDate(d)
                else:
                    self.fecha_estimada.setDate(QDate.currentDate())
            elif isinstance(f_est, date):
                self.fecha_estimada.setDate(QDate(f_est.year, f_est.month, f_est.day))
        else:
            self.fecha_estimada.setDate(QDate.currentDate())
            
        self.estado_riesgo = QComboBox()
        # Mapping: Display -> Backend Key
        self.estado_map = {
            "Por subsanar": "PENDIENTE",
            "Subsanadas": "SUBSANADO",
            "No Aplica": "NO_APLICA"
        }
        self.estado_riesgo.addItems(list(self.estado_map.keys()))
        
        current_estado = data.get("estado_riesgo")
        # Reverse map to set current text if it comes as backend key
        reverse_map = {v: k for k, v in self.estado_map.items()}
        if current_estado in reverse_map:
            self.estado_riesgo.setCurrentText(reverse_map[current_estado])
        elif current_estado in self.estado_map:
            self.estado_riesgo.setCurrentText(current_estado)
            
        form_layout.addRow("Acciones comprometidass:", self.acciones_comprometidas)
        form_layout.addRow("Acciones Realizadas:", self.acciones_realizadas)
        
        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("Fecha estimada de solución:"))
        h_row.addWidget(self.fecha_estimada)
        h_row.addSpacing(20)
        h_row.addWidget(QLabel("Estado del Riesgo:"))
        h_row.addWidget(self.estado_riesgo)
        h_row.addStretch()
        
        layout.addLayout(form_layout)
        layout.addLayout(h_row)
        
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.btn_guardar = QPushButton("Guardar cambios")
        self.btn_guardar.setObjectName("primaryButton")
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self._on_save)
        
        btns.addWidget(self.btn_guardar)
        layout.addLayout(btns)

    def _on_save(self):
        display_state = self.estado_riesgo.currentText()
        backend_state = self.estado_map.get(display_state, "PENDIENTE")
        
        payload = {
            "acciones_comprometidas": self.acciones_comprometidas.toPlainText(),
            "acciones_realizadas": self.acciones_realizadas.toPlainText(),
            "fecha_estimada_solucion": self.fecha_estimada.date().toString("yyyy-MM-dd"),
            "estado_riesgo": backend_state
        }
        self.save_requested.emit(payload)
