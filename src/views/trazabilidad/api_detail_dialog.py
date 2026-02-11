from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QFrame, QPushButton,
    QHBoxLayout, QScrollArea, QWidget, QSplitter
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QIcon

class ApiDetailDialog(QDialog):
    def __init__(self, data, title="Contenido de Respuesta", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalle de Información")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.resize(1100, 800)
        self.setStyleSheet("background-color: #f8fafc;")
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- Header ---
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("background-color: white; border-bottom: 1px solid #e2e8f0;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 0, 30, 0)
        
        title_container = QVBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #0f172a; font-size: 20px; font-weight: bold;")
        self.lbl_subtitle = QLabel("Exploración detallada de la información retornada por el servicio.")
        self.lbl_subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        title_container.addWidget(self.lbl_title)
        title_container.addWidget(self.lbl_subtitle)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        
        self.btn_close_top = QPushButton("×")
        self.btn_close_top.setFixedSize(30, 30)
        self.btn_close_top.setCursor(Qt.PointingHandCursor)
        self.btn_close_top.setStyleSheet("""
            QPushButton { 
                border: none; color: #94a3b8; font-size: 24px; font-weight: bold; background: transparent; 
            }
            QPushButton:hover { color: #0f172a; }
        """)
        self.btn_close_top.clicked.connect(self.reject)
        header_layout.addWidget(self.btn_close_top)
        
        self.main_layout.addWidget(header_frame)
        
        # --- Content Area ---
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        self.content_layout.setSpacing(20)
        
        # Extract 'data' field strictly
        clean_data = None
        if isinstance(data, dict):
            clean_data = data.get("data")
        
        if clean_data is not None:
            view_widget = self.create_data_view(clean_data)
            self.content_layout.addWidget(view_widget)
        else:
            self.show_empty_state()
            
        self.main_layout.addWidget(self.content_container)
        
        # --- Footer ---
        footer_frame = QFrame()
        footer_frame.setFixedHeight(70)
        footer_frame.setStyleSheet("background-color: #f1f5f9; border-top: 1px solid #e2e8f0;")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(30, 0, 30, 0)
        
        footer_layout.addStretch()
        
        self.btn_accept = QPushButton("Finalizar Vista")
        self.btn_accept.setFixedSize(140, 40)
        self.btn_accept.setCursor(Qt.PointingHandCursor)
        self.btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: white;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1e293b; }
        """)
        self.btn_accept.clicked.connect(self.accept)
        footer_layout.addWidget(self.btn_accept)
        
        self.main_layout.addWidget(footer_frame)

    def create_data_view(self, data):
        """Standardizes how complex data is shown."""
        container = QFrame()
        container.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(1, 1, 1, 1) # Internal border space
        
        if isinstance(data, list):
            if not data:
                return self._no_data_label("Lista de resultados vacía.")
            
            # If it's a list of dicts, use Table. Otherwise use Tree.
            if all(isinstance(item, dict) for item in data[:5]): # Check first few items
                widget = self.create_modern_table(data)
            else:
                widget = self.create_modern_tree(data)
        elif isinstance(data, dict):
            if not data:
                return self._no_data_label("Objeto de datos sin propiedades.")
            widget = self.create_modern_tree(data)
        else:
            # Primitive data
            widget = QLabel(str(data))
            widget.setWordWrap(True)
            widget.setStyleSheet("padding: 30px; color: #334155; font-size: 15px;")
            
        layout.addWidget(widget)
        return container

    def create_modern_table(self, data: list):
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        
        headers = sorted(list(all_keys))
        
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(data))
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        table.setStyleSheet("""
            QTableWidget { border: none; background-color: white; border-radius: 11px; }
            QTableWidget::item { padding: 15px; border-bottom: 1px solid #f1f5f9; color: #334155; }
            QHeaderView::section { 
                background-color: #f8fafc; padding: 15px; border: none; 
                border-bottom: 2px solid #e2e8f0; font-weight: bold; color: #475569;
                font-size: 13px; text-transform: uppercase;
            }
        """)
        
        for i, row_data in enumerate(data):
            for j, key in enumerate(headers):
                val = row_data.get(key, "—")
                item = QTableWidgetItem(str(val) if val is not None else "—")
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, j, item)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def create_modern_tree(self, data):
        tree = QTreeWidget()
        tree.setHeaderLabels(["Atributo / Propiedad", "Valor"])
        tree.setAlternatingRowColors(True)
        tree.setIndentation(30)
        tree.setColumnCount(2)
        tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        tree.setColumnWidth(0, 350)
        
        tree.setStyleSheet("""
            QTreeWidget { border: none; background-color: white; border-radius: 11px; outline: none; }
            QTreeWidget::item { padding: 8px; color: #334155; border-bottom: 1px solid #f8fafc; }
            QHeaderView::section { 
                background-color: #f8fafc; padding: 15px; border: none; 
                border-bottom: 2px solid #e2e8f0; font-weight: bold; color: #475569;
                font-size: 13px;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings { border-image: none; image: none; }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  { border-image: none; image: none; }
        """)
        
        self.populate_tree(tree.invisibleRootItem(), data)
        tree.expandAll()
        return tree

    def populate_tree(self, parent_item, data):
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem(parent_item)
                item.setText(0, str(key))
                item.setForeground(0, QColor("#1e40af")) # Dark blue for keys
                
                if isinstance(value, (dict, list)):
                    self.populate_tree(item, value)
                else:
                    item.setText(1, str(value if value is not None else "—"))
                    item.setForeground(1, QColor("#334155"))
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QTreeWidgetItem(parent_item)
                item.setText(0, f"Ítem #{i+1}")
                item.setForeground(0, QColor("#64748b")) # Slate for array indices
                
                if isinstance(value, (dict, list)):
                    self.populate_tree(item, value)
                else:
                    item.setText(1, str(value if value is not None else "—"))

    def _no_data_label(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #94a3b8; font-size: 16px; padding: 60px;")
        return lbl

    def show_empty_state(self):
        empty_widget = QFrame()
        empty_widget.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        layout = QVBoxLayout(empty_widget)
        
        msg = QLabel("No se encontró el campo 'data' en la respuesta.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #94a3b8; font-size: 16px; font-weight: 500; padding-top: 100px; padding-bottom: 100px;")
        layout.addWidget(msg)
        
        self.content_layout.addWidget(empty_widget)

