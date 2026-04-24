import json
import os
from functools import partial

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, 
    QComboBox, QFormLayout, QProgressBar, QDateEdit, QFileDialog, 
    QTextEdit, QPlainTextEdit, QApplication, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QThreadPool, QDate, Signal

from src.components.risk_matrix_widget import RiskMatrixWidget
from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.components.wizard_sidebar import WizardSidebar
from src.components.loading_overlay import LoadingOverlay
from src.services.catalogo_service import CatalogoService
from src.workers.combo_loader import ComboLoaderRunnable
from src.workers.api_worker import ApiWorker
from src.services.logger_service import LoggerService
from src.services.inventory_cache_service import InventoryCacheService
from src.components.custom_inputs import CheckableComboBox, RadioComboBox

EIPD_AMBITOS = [
    "Lícitud y Lealtad",
    "Finalidad",
    "Proporcionabilidad",
    "Calidad",
    "Responsabilidad",
    "Seguridad",
    "Transparencia e Información",
    "Confidencialidad",
    "Coordinación"
]

AMBITO_CODES = {
    "Lícitud y Lealtad": "LICITUD",
    "Finalidad": "FINALIDAD",
    "Proporcionabilidad": "PROPORCIONABILIDAD",
    "Calidad": "CALIDAD",
    "Responsabilidad": "RESPONSABILIDAD",
    "Seguridad": "SEGURIDAD",
    "Transparencia e Información": "TRANSPARENCIA",
    "Confidencialidad": "CONFIDENCIALIDAD",
    "Coordinación": "COORDINACION"
}

AMBITO_REVERSE_CODES = {v: k for k, v in AMBITO_CODES.items()}

class FilePickerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setPlaceholderText("Seleccione un archivo...")
        
        self.btn = QPushButton("Examinar")
        self.btn.clicked.connect(self._choose_file)
        
        layout.addWidget(self.line_edit)
        layout.addWidget(self.btn)
        
    def _choose_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo")
        if fname:
            self.line_edit.setText(fname)
            
    def text(self):
        return self.line_edit.text()
        
    def setText(self, text):
        self.line_edit.setText(text)

class FileTextWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.file_picker = FilePickerWidget()
        
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("fileTextInfo")
        self.text_edit.setPlaceholderText("Ingrese descripción o detalles...")
        self.text_edit.setFixedHeight(100)
        
        # Enforce border visibility with specific ID selector
        self.text_edit.setStyleSheet("""
            #fileTextInfo {
                background-color: white;
                border: 1px solid #94a3b8; /* Darker gray (Slate 400) */
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: #0f172a;
            }
            #fileTextInfo:focus {
                border: 2px solid #2563eb;
            }
        """)
        
        layout.addWidget(self.file_picker)
        layout.addWidget(self.text_edit)
        
    def get_data(self):
        return {
            "file": self.file_picker.text(),
            "text": self.text_edit.toPlainText()
        }
        
    def set_data(self, data):
        if not data: return
        if isinstance(data, dict):
            self.file_picker.setText(data.get("file", ""))
            self.text_edit.setPlainText(data.get("text", ""))
        else:
            # Fallback if single string provided
            self.text_edit.setPlainText(str(data))


class ComboTextWidget(QWidget):
    """A combo dropdown (single or multiple) + optional free text field below."""
    def __init__(self, field_config=None, parent=None):
        super().__init__(parent)
        field_config = field_config or {}
        self._is_multiple = field_config.get("multiple", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Combo
        if self._is_multiple:
            self.combo = CheckableComboBox()
        else:
            self.combo = QComboBox()
            self.combo.setPlaceholderText("Seleccione...")

        # Static options
        if field_config.get("combo_static_options"):
            for opt in field_config["combo_static_options"]:
                self.combo.addItem(opt["nombre"], opt.get("id", opt["nombre"]))
            if not self._is_multiple:
                self.combo.setCurrentIndex(-1)

        layout.addWidget(self.combo)

        # Text field
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Especifique otro...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                padding: 4px 8px;
                color: #0f172a;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
            }
        """)
        layout.addWidget(self.text_input)

    # --- API for GenericFormDialog ---
    def get_combo_value(self):
        if self._is_multiple:
            return self.combo.currentData()  # list of IDs
        return self.combo.currentData()  # single value

    def get_text_value(self):
        return self.text_input.text().strip()

    def get_data(self):
        return {
            "combo": self.get_combo_value(),
            "text": self.get_text_value()
        }

    def set_data(self, data):
        if not data:
            return
            
        # Parse JSON string if it looks like a dictionary or list from the API
        if isinstance(data, str) and (data.strip().startswith("{") or data.strip().startswith("[")):
            try:
                import json
                data = json.loads(data)
            except:
                pass

        if isinstance(data, dict):
            combo_val = data.get("combo")
            text_val = data.get("text", "")
        else:
            # Fallback for plain strings (legacy/simple storage)
            combo_val = None
            text_val = str(data)

        if combo_val is not None:
            if self._is_multiple and isinstance(self.combo, CheckableComboBox):
                # CheckableComboBox expects a list of IDs/values
                vals = combo_val if isinstance(combo_val, list) else [combo_val]
                self.combo.setCurrentData(vals)
            elif isinstance(self.combo, QComboBox):
                # Search for the value in itemData (ID) or itemText (Label) as fallback
                found = False
                for i in range(self.combo.count()):
                    val_str = str(combo_val)
                    if str(self.combo.itemData(i)) == val_str or self.combo.itemText(i) == val_str:
                        self.combo.setCurrentIndex(i)
                        found = True
                        break
                if not found:
                    self.combo.setCurrentIndex(-1)
        
        if text_val:
            self.text_input.setText(str(text_val))
        else:
            self.text_input.clear()

    def is_filled(self):
        """At least the combo or the text has a value."""
        if self._is_multiple:
            combo_ok = bool(self.combo.currentData())
        else:
            combo_ok = self.combo.currentIndex() != -1
        text_ok = bool(self.text_input.text().strip())
        return combo_ok or text_ok


class EditableTableWidget(QWidget):
    dataChanged = Signal()

    def __init__(self, field_config, parent=None):
        super().__init__(parent)
        self.columns = field_config.get("columns", [])
        self.column_keys = [col.get("key") for col in self.columns]
        self._row_meta = []
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels(
            [col.get("label", col.get("key", "")) for col in self.columns]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(140)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #334155;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.btn_remove = QPushButton("Eliminar fila")
        self.btn_remove.setObjectName("secondaryButton")
        self.btn_remove.clicked.connect(self.remove_selected_row)

        self.btn_add = QPushButton("Agregar fila")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self.add_empty_row)

        buttons.addWidget(self.btn_remove)
        buttons.addWidget(self.btn_add)
        layout.addLayout(buttons)
        self._buttons_layout = buttons

    def _build_cell_input(self, value=""):
        inp = QLineEdit()
        inp.setText("" if value is None else str(value))
        inp.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                padding: 6px 10px;
                color: #0f172a;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
            }
        """)
        inp.textChanged.connect(lambda *_: (None if self._loading else self.dataChanged.emit()))
        return inp

    def add_empty_row(self):
        self._append_row({}, {})
        self.dataChanged.emit()

    def _append_row(self, row_data, row_meta):
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        self._row_meta.append(row_meta or {})

        for col_idx, col in enumerate(self.columns):
            key = col.get("key")
            value = row_data.get(key, "")
            inp = self._build_cell_input(value)
            self.table.setCellWidget(row_idx, col_idx, inp)

    def remove_selected_row(self):
        row_idx = self.table.currentRow()
        if row_idx < 0:
            row_idx = self.table.rowCount() - 1
        if row_idx < 0:
            return

        self.table.removeRow(row_idx)
        if 0 <= row_idx < len(self._row_meta):
            self._row_meta.pop(row_idx)
        self.dataChanged.emit()

    def get_data(self):
        rows = []
        for row_idx in range(self.table.rowCount()):
            row = {}
            meta = self._row_meta[row_idx] if row_idx < len(self._row_meta) else {}
            row.update(meta)

            for col_idx, key in enumerate(self.column_keys):
                inp = self.table.cellWidget(row_idx, col_idx)
                row[key] = inp.text().strip() if isinstance(inp, QLineEdit) else None
            rows.append(row)
        return rows

    def set_data(self, rows):
        self._loading = True
        try:
            self.table.setRowCount(0)
            self._row_meta = []

            if not isinstance(rows, list):
                rows = []

            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_values = {k: row.get(k) for k in self.column_keys}
                row_meta = {k: v for k, v in row.items() if k not in self.column_keys}
                self._append_row(row_values, row_meta)
        finally:
            self._loading = False

    def has_non_empty_rows(self):
        for row in self.get_data():
            for key in self.column_keys:
                value = row.get(key)
                if value and str(value).strip():
                    return True
        return False

    def set_read_only(self, read_only: bool):
        self.btn_add.setVisible(not read_only)
        self.btn_remove.setVisible(not read_only)
        self.table.setSelectionMode(
            QTableWidget.NoSelection if read_only else QTableWidget.SingleSelection
        )

        for row_idx in range(self.table.rowCount()):
            for col_idx in range(len(self.column_keys)):
                inp = self.table.cellWidget(row_idx, col_idx)
                if isinstance(inp, QLineEdit):
                    inp.setReadOnly(read_only)

class GenericFormDialog(QDialog):
    def __init__(self, config_path, parent=None, record_id=None):
        super().__init__(parent)
        
        # Load Config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.record_id = record_id
        self.is_edit = record_id is not None
        
        # Services
        self.api = ApiClient()
        self.catalogo_service = CatalogoService()
        self.thread_pool = QThreadPool.globalInstance()
        self._active_runnables = [] # Keep refs
        self.asset_data = None
        self.pending_loads = 0
        self._allow_asset_reapply = self.is_edit
        self.is_setting_values = False
        self._raw_asset_data = None # Store virgin API response

        # UI Setup
        self.setObjectName("genericFormDialog")
        title = self.config.get("title_edit", "Editar") if self.is_edit else self.config.get("title_new", "Nuevo")
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setModal(True)
        
        # Screen-relative sizing
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Default: 90% of screen
        target_w = int(screen.width() * 0.9)
        target_h = int(screen.height() * 0.9)

        # Config override (optional, but capped)
        cfg_w = self.config.get("width")
        cfg_h = self.config.get("height")

        if cfg_w: target_w = min(int(cfg_w), screen.width())
        if cfg_h: target_h = min(int(cfg_h), screen.height())

        self.resize(target_w, target_h)
        
        # Main Dialog Background - Light Gray
        self.setStyleSheet("#genericFormDialog { background-color: #f1f5f9; }")
        
        # Inputs Registry: key -> widget
        self.inputs = {}
        # Dependency Map: trigger_key -> [dependent_keys]
        self.dependencies = {}
        # Dependency Config: key -> config
        # ... dependency map initialization ...
        self.visibility_map = {} # source_key -> list of {target_block, rule, key}
        self.dependency_configs = {}
        self.labels = {}  # Registry for field labels
        self.blocks = {}  # Registry for field block containers (QFrame)
        self.footer_layouts = {} # index -> QHBoxLayout

        self._init_ui()
        
        # Async Load
        self.loading_overlay = LoadingOverlay(self)
        QTimer.singleShot(0, self._init_async_load)
        
        title_log = self.config.get("title_edit", "Editar") if self.is_edit else self.config.get("title_new", "Nuevo")
        LoggerService().log_event(f"Abriendo formulario genérico: {title_log}")

    def _init_ui(self):
        # Layout principal (Vertical: Top Header + Body)
        # Body (Horizontal: Sidebar | Content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # =========================================
        # 1. Top Container (Header)
        # =========================================
        self.top_frame = QFrame()
        self.top_frame.setObjectName("topFrame")
        self.top_frame.setStyleSheet("""
            #topFrame { 
                background-color: white; 
                border-radius: 16px; 
            }
        """)
        # Minimal height to look like a header card
        self.top_frame.setMinimumHeight(150)
        
        top_layout = QVBoxLayout(self.top_frame)
        top_layout.setContentsMargins(32, 24, 32, 24)
        
        # Title in Header
        title_text = self.config.get("title_edit", "Editar") if self.is_edit else self.config.get("title_new", "Nuevo")
        
        header_title = QLabel(title_text)
        header_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        
        header_desc = QLabel("Complete la información solicitada en las siguientes secciones.")
        header_desc.setStyleSheet("font-size: 14px; color: #64748b; margin-top: 4px;")
        
        top_layout.addWidget(header_title)
        top_layout.addWidget(header_desc)
        
        # Global Progress Bar
        self.progress_label = QLabel("Progreso: 0% (0/0 campos requeridos)")
        self.progress_label.setStyleSheet("font-size: 12px; color: #475569; margin-top: 12px; font-weight: 500;")
        top_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e2e8f0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #0f172a;
                border-radius: 3px;
            }
        """)
        top_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.top_frame)
        
        # =========================================
        # Body Layout
        # =========================================
        body_layout = QHBoxLayout()
        body_layout.setSpacing(24)
        
        # 2. Left Container (Sidebar)
        sidebar_container = QFrame()
        sidebar_container.setObjectName("sidebarContainer")
        sidebar_container.setStyleSheet("""
            #sidebarContainer { 
                background-color: white; 
                border-radius: 16px; 
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        sections_config = self.config.get("sections", [])
        self.sidebar = WizardSidebar(sections_config)
        # Make sidebar transparent so container background shows
        self.sidebar.setStyleSheet("background: transparent; border: none;")
        self.sidebar.step_changed.connect(self._on_step_changed)
        
        # Ensure container fits the fixed-width sidebar
        sidebar_container.setSizePolicy(self.sidebar.sizePolicy())
        
        sidebar_layout.addWidget(self.sidebar)
        
        body_layout.addWidget(sidebar_container, 0)
        
        # 3. Right Container (Content)
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet("""
            #contentFrame { 
                background-color: white; 
                border-radius: 16px; 
            }
        """)
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # The Stack
        self.stack = QStackedWidget()
        
        for i, section in enumerate(sections_config):
            content_widget = self._build_section_form(section)
            
            page = self._wrap_step_content(
                content_widget,
                section["title"],
                section.get("description", ""),
                i,
                len(sections_config)
            )
            self.stack.addWidget(page)
            
        content_layout.addWidget(self.stack)
        
        # Setup visibility connections after all fields are created
        self._setup_visibility_connections()
        
        body_layout.addWidget(content_frame, 1) # Stretch Content
        
        main_layout.addLayout(body_layout, 1)

    def _build_section_form(self, section_config):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(24)
        layout.setContentsMargins(16, 16, 16, 16)

        for field in section_config.get("fields", []):

            # =========================
            # GROUP (ÁMBITO)
            # =========================
            if field.get("type") == "group":
                group_box = QFrame()
                group_box.setStyleSheet("""
                    QFrame {
                        background-color: transparent;
                        border: none;
                        border-radius: 0px;
                        padding: 0px;
                        margin-top: 16px; 
                    }
                """)

                v = QVBoxLayout(group_box)
                v.setContentsMargins(0, 8, 0, 8) # Minimal vertical spacing
                v.setSpacing(16)

                # ---- HEADER ----
                # Separator Line
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color: #e2e8f0; margin-bottom: 8px;")
                v.addWidget(line)

                # Sub-layout for title and description to control spacing specifically
                title_desc_box = QVBoxLayout()
                title_desc_box.setSpacing(2) 
                title_desc_box.setContentsMargins(0, 0, 0, 0)

                header_layout = QHBoxLayout()
                header_layout.setContentsMargins(0, 0, 0, 0)

                title = QLabel(field.get("label", ""))
                title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")

                header_layout.addWidget(title)
                header_layout.addStretch()
                title_desc_box.addLayout(header_layout)

                # Description for group
                group_desc = field.get("description", "")
                if group_desc:
                    desc_lbl = QLabel(group_desc)
                    # Removing negative margins as they often cause truncation in layout calculations
                    desc_lbl.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 4px;")
                    desc_lbl.setWordWrap(True)
                    # Essential for labels in scroll areas to ensure they calculate height correctly
                    desc_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
                    title_desc_box.addWidget(desc_lbl)
                
                v.addLayout(title_desc_box)

                # ---- construir subformularios ----
                for subfield in field.get("fields", []):
                    fake_section = {"fields": [subfield]}
                    sub_form = self._build_section_form(fake_section)
                    # Force subform to have no margins so it aligns perfectly
                    if sub_form.layout():
                         sub_form.layout().setContentsMargins(0, 0, 0, 0)
                    v.addWidget(sub_form)

                layout.addWidget(group_box)
                continue
            
            


            # =========================
            # FIELD NORMAL
            # =========================
            field_block = QWidget()
            field_block.setObjectName(f"fieldBlock_{field['key']}")
            self.blocks[field['key']] = field_block
            
            block_layout = QVBoxLayout(field_block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(6)

            # Label
            label_layout = QHBoxLayout()
            label_text = field.get("label", "")
            if field.get("required", False):
                label_text += " *"

            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #1e293b;")
            label_layout.addWidget(lbl)
            
            # Registry for access in sub-classes
            key = field["key"]
            self.labels[key] = lbl

            if field.get("required", False):
                req_lbl = QLabel("Obligatorio")
                req_lbl.setStyleSheet("font-size: 11px; color: #dc2626; font-weight: 600;")
                label_layout.addWidget(req_lbl, 0, Qt.AlignRight)

            block_layout.addLayout(label_layout)

            # Description
            desc_text = field.get("description", "")
            if desc_text:
                desc_lbl = QLabel(desc_text)
                desc_lbl.setStyleSheet("font-size: 12px; color: #64748b; margin-bottom: 2px;")
                desc_lbl.setWordWrap(True)
                block_layout.addWidget(desc_lbl)

            # Widget
            widget = self._create_input_widget(field)
            key = field["key"]
            self.inputs[key] = widget

            # Dependency & Signals
            if "triggers_reload" in field:
                self.dependencies[key] = field["triggers_reload"]
                if isinstance(widget, QComboBox):
                    # For CheckableComboBox, use selectionChanged
                    if hasattr(widget, "selectionChanged"):
                        widget.selectionChanged.connect(
                            partial(self._on_trigger_changed, key)
                        )
                    else:
                        widget.currentIndexChanged.connect(
                            partial(self._on_trigger_changed, key)
                        )

            if "depends_on" in field:
                self.dependency_configs[key] = field

            # Navigation & Validation
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, QPlainTextEdit):
                widget.textChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, CheckableComboBox):
                widget.selectionChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, EditableTableWidget):
                widget.dataChanged.connect(self._validate_steps_progress)

            # EIPD Sync Logic
            # If field key belongs to one of the 9 ambitos, monitor its changes
            for p in [c.lower() for c in EIPD_AMBITOS]:
                # Normalize prefix (e.g. "Licitud y Lealtad" -> "licitud")
                # Wait, EIPD_AMBITOS are full names. The keys use prefixes like "licitud"
                pass
            
            # Use AMBITO_CODES keys (full names) and map to prefixes
            prefix_map = {
                "Lícitud y Lealtad": "licitud",
                "Finalidad": "finalidad",
                "Proporcionabilidad": "proporcionabilidad",
                "Calidad": "calidad",
                "Responsabilidad": "responsabilidad",
                "Seguridad": "seguridad",
                "Transparencia e Información": "transparencia",
                "Confidencialidad": "confidencialidad",
                "Coordinación": "coordinacion"
            }

            for ambito_full, prefix in prefix_map.items():
                if key.startswith(f"{prefix}_"):
                    if isinstance(widget, (QComboBox, QTextEdit, QPlainTextEdit)):
                        # Connect to sync method
                        # We use lambda to pass the prefix
                        if isinstance(widget, (QTextEdit, QPlainTextEdit)):
                             widget.textChanged.connect(lambda p=prefix: self._sync_risk_matrix(p))
                        else:
                             widget.currentIndexChanged.connect(lambda *args, p=prefix: self._sync_risk_matrix(p))

            block_layout.addWidget(widget)

            # visible_when: conditional visibility from JSON config
            vis_rule = field.get("visible_when")
            if vis_rule:
                source_key = vis_rule.get("field")
                if source_key:
                    field_block.setVisible(False)  # hidden by default — shown by visibility engine
                    if source_key not in self.visibility_map:
                        self.visibility_map[source_key] = []
                    self.visibility_map[source_key].append({
                        "target_block": field_block,
                        "rule": vis_rule,
                        "key": key
                    })

            layout.addWidget(field_block)

        layout.addStretch()



        return w
    

    def _setup_visibility_connections(self):
        for source_key in self.visibility_map.keys():
            if source_key in self.inputs:
                self._connect_visibility_trigger(source_key, self.inputs[source_key])
                self._check_visibility(source_key)
        
        # DIRECT CONNECTIONS: For CheckableComboBox sources, add an additional
        # direct handler that bypasses _check_visibility entirely. This guarantees
        # visibility works even if the generic engine has timing or signal issues.
        self._setup_direct_checkable_visibility()

    def _setup_direct_checkable_visibility(self):
        """
        For every CheckableComboBox that is a source of a visibility rule
        ('contains' match), create a DIRECT signal → setVisible() connection.
        This is a fail-safe that works independently of _check_visibility.
        """
        for source_key, deps_list in self.visibility_map.items():
            widget = self.inputs.get(source_key)
            # Only for CheckableComboBox (not RadioComboBox)
            if not isinstance(widget, CheckableComboBox) or isinstance(widget, RadioComboBox):
                continue

            # Collect (target_block, rule_text) pairs that use 'contains'
            block_rules = []
            for dep in deps_list:
                contains_val = dep["rule"].get("contains", "")
                if contains_val and dep.get("target_block"):
                    block_rules.append((dep["target_block"], contains_val.strip().lower()))

            if not block_rules:
                continue

            # Create a closure that captures the widget and block_rules
            def make_direct_handler(combo_widget, rules, src_key):
                def _direct_handler():
                    texts = []
                    try:
                        texts = [t.strip().lower() for t in combo_widget.get_selected_texts()]
                    except Exception as e:
                        LoggerService().log_event(f"[DIRECT VIS] Error reading texts for '{src_key}': {e}")
                        return
                    LoggerService().log_event(f"[DIRECT VIS] '{src_key}' fired texts={texts}")
                    changed = False
                    for target_blk, rule_text in rules:
                        try:
                            matched = any(rule_text in t for t in texts)
                            LoggerService().log_event(f"[DIRECT VIS] rule='{rule_text}' match={matched}")
                            was = target_blk.isVisible()
                            target_blk.setVisible(matched)
                            if matched != was:
                                changed = True
                        except RuntimeError as e:
                            LoggerService().log_event(f"[DIRECT VIS] RuntimeError: {e}")
                    if changed:
                        self._force_layout_update()
                return _direct_handler

            handler = make_direct_handler(widget, block_rules, source_key)
            LoggerService().log_event(f"[DIRECT VIS] Registered handler for '{source_key}'")
            widget.selectionChanged.connect(handler)
            if not hasattr(self, '_direct_visibility_handlers'):
                self._direct_visibility_handlers = {}
            self._direct_visibility_handlers[source_key] = handler

    def _apply_all_direct_visibility(self):
        """
        Invoke all stored direct visibility handlers.
        Call this after programmatically setting values in edit mode
        to ensure hidden/shown blocks reflect the current selections.
        """
        handlers = getattr(self, '_direct_visibility_handlers', {})
        for key, handler in handlers.items():
            try:
                handler()
            except Exception:
                pass

    def _force_layout_update(self):
        """
        Force Qt to recalculate and repaint layouts after a visibility change.
        Needed because QScrollArea with setWidgetResizable(True) does not always
        automatically re-flow when a child widget's visibility changes.
        """
        try:
            # Walk the current stack page's content widget and invalidate all layouts
            current_page = self.stack.currentWidget()
            if current_page:
                def _invalidate_recursive(widget):
                    if widget.layout():
                        widget.layout().invalidate()
                        widget.layout().activate()
                    for child in widget.findChildren(QWidget):
                        if child.layout():
                            child.layout().invalidate()
                            child.layout().activate()
                _invalidate_recursive(current_page)
                current_page.adjustSize()
                current_page.update()
        except RuntimeError:
            pass

    def _connect_visibility_trigger(self, key, widget):
        try:
            if not widget: return
            
            # Robust check for CheckableComboBox
            is_checkable = isinstance(widget, CheckableComboBox) or widget.__class__.__name__ == "CheckableComboBox"
            LoggerService().log_event(f"CONNECT DEBUG: Connecting visibility for '{key}'. IsCheckable={is_checkable}")
            
            if is_checkable:
                 if hasattr(widget, "selectionChanged"):
                     # Do NOT use disconnect() as it kills other signals like triggers_reload
                     widget.selectionChanged.connect(lambda *args, k=key: self._check_visibility(k))
            
            elif isinstance(widget, QComboBox):
                 widget.currentIndexChanged.connect(lambda *args, k=key: self._check_visibility(k))
            
            elif isinstance(widget, QLineEdit):
                 widget.textChanged.connect(lambda *args, k=key: self._check_visibility(k))
                
        except (TypeError, RuntimeError):
            pass

    def _check_visibility(self, source_key):
        LoggerService().log_event(f"EVENT: Checking visibility triggered by {source_key}")
        if source_key not in self.visibility_map: return
        
        # Verify inputs integrity
        if source_key not in self.inputs: return

        source_widget = self.inputs.get(source_key)
        if not source_widget: return
        
        try:
            # Get value
            val = None
            is_checkable = isinstance(source_widget, CheckableComboBox) or source_widget.__class__.__name__ == "CheckableComboBox"

            if is_checkable:
                 val = source_widget.currentData()
            elif isinstance(source_widget, QComboBox):
                 val = source_widget.currentData()
            elif isinstance(source_widget, QLineEdit):
                 val = source_widget.text()

            deps = self.visibility_map[source_key]
            for dep in deps:
                rule = dep["rule"]
                target_block = dep["target_block"]
                
                # Check target block existence
                if not target_block: continue

                # Check condition
                match = False
                req_val = rule.get("value")
                contains_val = rule.get("contains")
                
                if contains_val:
                    # Universal "contains" check
                    rule_text = str(contains_val).strip().lower()
                    
                    # 1. Check texts (display labels)
                    display_texts = []
                    if hasattr(source_widget, "get_selected_texts"):
                        display_texts = [t.strip().lower() for t in source_widget.get_selected_texts()]
                    elif hasattr(source_widget, "currentText"):
                        display_texts = [source_widget.currentText().strip().lower()]
                    
                    found_in_text = any(rule_text in t for t in display_texts)
                    LoggerService().log_event(f"VISIBILITY MATCH for '{source_key}': Rule '{rule_text}' vs '{display_texts}' -> {found_in_text}")
                    
                    # 2. Check value (IDs)
                    val_str = str(val).lower()
                    found_in_val = rule_text in val_str
                    
                    match = found_in_text or found_in_val
                    LoggerService().log_event(f"VISIBILITY DEBUG: Field '{source_key}' contains '{rule_text}'? Text:{display_texts} Val:{val} -> MATCH={match}")
                
                elif req_val is not None:
                    if isinstance(val, list): # Checkable returns list
                         if str(req_val) in [str(v) for v in val]: match = True
                    else:
                         if str(val) == str(req_val): match = True
                
                if target_block:
                    was_visible = target_block.isVisible()
                    target_block.setVisible(match)
                    if match != was_visible:
                        self._force_layout_update()
                    
                    # CASCADE: If visibility changed, anything depending on THIS field must be re-checked
                    # Find the key for the widget in this block
                    target_key = None
                    for k, b in self.blocks.items():
                        if b == target_block:
                            target_key = k
                            break
                    
                    if target_key and target_key in self.visibility_map:
                         LoggerService().log_event(f"CASCADE TRIGGER: Re-checking {target_key}")
                         self._check_visibility(target_key)
                
            # Retrigger validation because required fields might have appeared/disappeared
            self._validate_steps_progress()
            
        except RuntimeError:
            return  # Object deleted

    def _recheck_all_visibility(self):
        """
        Fire _check_visibility for every field that is registered as a visibility
        source. Called via QTimer.singleShot after nested combos are populated so
        that dependent fields (e.g., the free-text box for 'Otros datos personales')
        correctly reflect the current selection state.
        """
        for source_key in list(self.visibility_map.keys()):
            try:
                self._check_visibility(source_key)
            except RuntimeError:
                pass  # Widget was deleted

    def _create_input_widget(self, field):
        ftype = field.get("type", "text")
        
        if field.get("control") == "calendar":
             from PySide6.QtWidgets import QDateEdit
             from PySide6.QtCore import QDate
             
             inp = QDateEdit()
             inp.setCalendarPopup(True)
             inp.setDate(QDate.currentDate())
             inp.setDisplayFormat("dd-MM-yyyy") 
             return inp
        
        

        if ftype == "text":
            inp = QLineEdit()
            
            bg_color = "white"
            if field.get("readonly", False):
                inp.setReadOnly(True)
                bg_color = "#f1f5f9"
                
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {bg_color}; 
                    border: 1px solid #94a3b8; 
                    border-radius: 6px; 
                    padding: 4px 8px;
                    color: #0f172a;
                }}
                QLineEdit:focus {{
                    border: 2px solid #2563eb;
                }}
            """)
            return inp

        elif ftype == "textarea":
            inp = QPlainTextEdit()
            inp.setFixedHeight(100)
            inp.setStyleSheet("""
                QPlainTextEdit {
                    background-color: white; 
                    border: 1px solid #94a3b8; 
                    border-radius: 6px; 
                    padding: 8px;
                    color: #0f172a;
                    font-family: inherit;
                }
                QPlainTextEdit:focus {
                    border: 2px solid #2563eb;
                }
            """)
            return inp
            
        elif ftype == "combo" or ftype == "combo_static":
            is_multiple = field.get("multiple", False)
            
            if is_multiple:
                inp = CheckableComboBox()
            else:
                inp = QComboBox()
                inp.setPlaceholderText("Seleccione...")
                
            if ftype == "combo_static" and "options" in field:
                for opt in field["options"]:
                    inp.addItem(opt["nombre"], opt["id"])
                    
                if not is_multiple:
                     inp.setCurrentIndex(-1)

            inp.setProperty("field_config", field)
            return inp

        elif ftype == "radio_combo":
            inp = RadioComboBox()
            inp.setProperty("field_config", field)
            return inp
            
        elif ftype == "file":
             return FilePickerWidget()
             
        elif ftype == "file_textarea":
             return FileTextWidget()
         
        elif ftype == "risk_matrix":
            # For EIPD, the user specifically asked for this to be read-only summary
            is_read_only = field.get("read_only", False)
            # Default to True for EIPD if it's the matriz_riesgos key
            if field.get("key") == "matriz_riesgos":
                is_read_only = True
                
            w = RiskMatrixWidget(read_only=is_read_only)
            
            # Extract descriptions from Section 1 groups for pre-population
            descriptions = {}
            for section in self.config.get("sections", []):
                for f in section.get("fields", []):
                    if f.get("type") == "group" and f.get("label") and f.get("description"):
                        descriptions[f["label"]] = f["description"]
            
            w.preload_ambitos(EIPD_AMBITOS, descriptions=descriptions)
            
            # Initial sync from existing data in Section 1
            prefixes = ["licitud", "finalidad", "proporcionabilidad", "calidad", "responsabilidad", "seguridad", "transparencia", "confidencialidad", "coordinacion"]
            for p in prefixes:
                QTimer.singleShot(100, lambda p=p: self._sync_risk_matrix(p))
                
            return w
        elif ftype == "editable_table":
            return EditableTableWidget(field)
        elif ftype == "combo_text":
            return ComboTextWidget(field_config=field)
    
        return QLineEdit()

    def _validate_steps_progress(self):
        # Iterate all sections
        sections = self.config.get("sections", [])
        
        global_filled = 0
        global_total = 0
        
        for i, section in enumerate(sections):
            total_req = 0
            filled_req = 0
            
            # Identify the page widget for this section to check relative visibility
            page_widget = self.stack.widget(i)
            
            def process_fields(field_list):
                nonlocal total_req, filled_req
                for field in field_list:
                    if field.get("type") == "group":
                        process_fields(field.get("fields", []))
                        continue

                    if field.get("required", False):
                        key = field["key"]
                        widget = self.inputs.get(key)
                        
                        try:
                            # Check visibility relative to the page (handling hidden tabs)
                            not_visible = False
                            if not widget or not page_widget:
                                not_visible = True
                            elif not widget.isVisibleTo(page_widget):
                                not_visible = True
                                
                            if not_visible:
                                 continue
        
                            total_req += 1
                            if self._is_field_filled(widget, field):
                                filled_req += 1
                        except RuntimeError:
                            continue

            process_fields(section.get("fields", []))
            
            # Update Sidebar Step
            if i < len(self.sidebar.step_widgets):
                try:
                    self.sidebar.step_widgets[i].update_required_count(filled_req, total_req)
                except (RuntimeError, AttributeError):
                    pass
            
            global_filled += filled_req
            global_total += total_req

        # Update Global Header Progress
        percentage = 0
        if global_total > 0:
            percentage = int((global_filled / global_total) * 100)
        else:
            percentage = 100 

        # Update Bar
        if hasattr(self, "progress_bar"):
            try:
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: none;
                        background-color: #e2e8f0;
                        border-radius: 3px;
                    }
                    QProgressBar::chunk {
                        background-color: #0284c7; 
                        border-radius: 3px;
                    }
                """)
                self.progress_bar.setMaximum(global_total if global_total > 0 else 1)
                self.progress_bar.setValue(global_filled if global_total > 0 else 1)
            except RuntimeError:
                pass

        # Update Label
        if hasattr(self, "progress_label"):
            try:
                self.progress_label.setText(f"Progreso: {percentage}% ({global_filled}/{global_total} campos requeridos)")
            except RuntimeError:
                pass
        

    def _get_missing_required_fields(self):
        """Returns a list of (label, section_title) for missing required fields that are currently visible."""
        missing = []
        sections = self.config.get("sections", [])
        
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Sección {i+1}")
            page_widget = self.stack.widget(i)
            
            def check_fields(field_list):
                for field in field_list:
                    if field.get("type") == "group":
                        check_fields(field.get("fields", []))
                        continue

                    if field.get("required", False):
                        key = field["key"]
                        widget = self.inputs.get(key)
                        label = field.get("label", key)
                        
                        try:
                            # Only validate if the field is visible (logic-driven visibility)
                            if not widget or not page_widget:
                                continue
                            if not widget.isVisibleTo(page_widget):
                                continue
                                
                            if not self._is_field_filled(widget, field):
                                missing.append(f"- {label} ({section_title})")
                        except RuntimeError:
                            continue

            check_fields(section.get("fields", []))
        return missing

    def _is_field_filled(self, widget, field):
        if not widget: return False
        
        try:
            # Robust check for CheckableComboBox and RadioComboBox
            is_checkable = isinstance(widget, CheckableComboBox) or widget.__class__.__name__ == "CheckableComboBox"
            is_radio = isinstance(widget, RadioComboBox) or widget.__class__.__name__ == "RadioComboBox"
            
            if isinstance(widget, QLineEdit):
                return bool(widget.text().strip())
                
            elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
                return bool(widget.toPlainText().strip())
                 
            elif is_radio or is_checkable:
                # Check text presence as visual confirmation of selection
                return bool(widget.lineEdit().text().strip())
                
            elif isinstance(widget, QComboBox):
                if widget.currentIndex() == -1: return False
                return True
                
            elif isinstance(widget, FilePickerWidget):
                return bool(widget.text().strip())
                
            elif isinstance(widget, FileTextWidget):
                data = widget.get_data()
                file_ok = bool((data.get("file") or "").strip())
                text_ok = bool((data.get("text") or "").strip())
                return file_ok or text_ok
            elif isinstance(widget, EditableTableWidget):
                return widget.has_non_empty_rows()
            elif isinstance(widget, ComboTextWidget):
                return widget.is_filled()

            elif isinstance(widget, QDateEdit):
                d = widget.date()
                return d is not None and d.isValid()
        except RuntimeError:
            return False
            
        return False

    def _on_record_data(self, data):
        # Flattening/Unnesting Logic
        if self.config.get("endpoint") == "/rat" and "titulares" in data:
            # Flatten RAT sub-objects for easier mapping
            titulares = data.get("titulares", {})
            for k, v in titulares.items():
                if k not in data:
                    data[k] = v
        
        if self.config.get("endpoint") == "/eipd":
            data = self._flatten_eipd_data(data)

        # Store virgin copy for hierarchical mapping
        self._raw_asset_data = data.copy() if data else {}
        self.asset_data = data
        self._try_set_values()
        # Trigger validation after loading data
        self._validate_steps_progress() 
        self._check_finished()

    def _flatten_eipd_data(self, data):
        """
        Transforms the nested EIPD structure (ambitos[], riesgos[]) 
        back into the flat key-value structure required by the form widgets.
        """
        flat_data = data.copy()
        
        # 1. Map Ambitos (List -> Flat Fields)
        # We need to know the prefixes. We can use AMBITO_CODES reverse manually or helper.
        # Prefixes used in _build__eipd_payload were: licitud, finalidad, etc.
        
        prefix_map_reverse = {
            "LICITUD": "licitud",
            "FINALIDAD": "finalidad",
            "PROPORCIONABILIDAD": "proporcionabilidad",
            "CALIDAD": "calidad",
            "RESPONSABILIDAD": "responsabilidad",
            "SEGURIDAD": "seguridad",
            "TRANSPARENCIA": "transparencia",
            "CONFIDENCIALIDAD": "confidencialidad",
            "COORDINACION": "coordinacion"
        }
        
        ambitos = data.get("ambitos", [])
        for ambito in ambitos:
            code = ambito.get("ambito_codigo")
            if code: code = code.upper() # Ensure uppercase for lookup
            prefix = prefix_map_reverse.get(code)
            if not prefix: continue
            
            # Map fields
            flat_data[f"{prefix}_criterios"] = ambito.get("criterios_evaluacion")
            flat_data[f"{prefix}_resumen"] = ambito.get("resumen")
            
            # Combos (prob, imp) - stored as IDs usually. 
            # In the provided JSON, "probabilidad" is "maximo" (string ID).
            # "nivel" is "Medio".
            flat_data[f"{prefix}_probabilidad"] = ambito.get("probabilidad")
            flat_data[f"{prefix}_impacto"] = ambito.get("impacto")
            
            # Note: 'nivel' might be a calculated label in UI, usually not an input we set directly 
            # unless there is a read-only field for it.
            
        # 2. Map Riesgos (List -> Matrix Data)
        # RiskMatrixWidget expects a list of dicts with 'ambito' (display name)
        riesgos = data.get("riesgos", [])
        matrix_data = []
        
        # We need code -> Display Name
        code_to_name = {v: k for k, v in AMBITO_CODES.items()}
        
        for r in riesgos:
            code = r.get("ambito_codigo")
            if code: code = code.upper() # Ensure uppercase for lookup
            name = code_to_name.get(code)
            if not name: continue
            
            row = r.copy()
            row["ambito"] = name # Required by RiskMatrixWidget to find the row
            matrix_data.append(row)
            
        flat_data["matriz_riesgos"] = matrix_data
        
        # 3. Base Fields
        # flat_data["identificacion_rat_catalogo"] should be set to rat_id
        flat_data["identificacion_rat_catalogo"] = data.get("rat_id")
        
        return flat_data
    
    def _unflatten_hierarchical_categories(self):
        """
        General approach to unflatten hierarchical categories for both Activos and RAT.
        Detects keys dynamically from self.inputs and maps from self._raw_asset_data.
        """
        if not self._raw_asset_data: return

        # Mapping variations [Main Key, Sub Key, Text Key, API Main, API Sub, API Text]
        maps = [
            # Activos
            ["categoria_ids", "categoria_sensible_especifica", "categoria_sensible_especificar_otro", "categoria_ids", None, "categoria_otro"],
            # RAT Inst
            ["categorias_datos_inst", "categorias_datos_sensibles_inst", "categorias_datos_otro_inst", "categoria_datos", "categoria_datos_sensibles", "categoria_datos_otro"],
            # RAT Simp
            ["categorias_datos_personales", "categorias_datos_sensibles", "categorias_datos_otro", "categoria_datos", "categoria_datos_sensibles", "categoria_datos_otro"]
        ]

        found_map = None
        for m in maps:
            if m[0] in self.inputs:
                found_map = m
                break
        
        if not found_map: return
        
        main_key, sub_key, text_key, api_main, api_sub, api_text = found_map
        
        # Helper to parse list from raw data (can be list or JSON string)
        def get_list(key):
            val = self._raw_asset_data.get(key)
            if not val: return []
            if isinstance(val, list): return val
            if isinstance(val, str):
                try: 
                    p = json.loads(val)
                    return p if isinstance(p, list) else []
                except: return []
            return []

        api_main_ids = get_list(api_main)
        api_sub_ids = get_list(api_sub) if api_sub else []
        
        # Combined set of all selected IDs
        all_ids_set = set(map(str, api_main_ids + api_sub_ids))
        if not all_ids_set: return

        main_widget = self.inputs.get(main_key)
        catalog = main_widget.property("raw_data") if main_widget else None
        if not catalog: return

        final_main_ids = []
        final_sub_ids = []
        
        for parent in catalog:
            p_id = str(parent.get("id"))
            subcats = parent.get("subcategorias") or []
            
            # Parent was explicitly selected
            if p_id in all_ids_set and parent.get("id") not in final_main_ids:
                final_main_ids.append(parent.get("id"))
            
            # Check subcats
            for sub in subcats:
                s_id = str(sub.get("id"))
                if s_id in all_ids_set:
                    # Found a match
                    if sub.get("id") not in final_sub_ids:
                        final_sub_ids.append(sub.get("id"))
                    # Ensure parent is selected in main widget
                    if parent.get("id") not in final_main_ids:
                        final_main_ids.append(parent.get("id"))

        # Apply to working data
        self.asset_data[main_key] = final_main_ids
        if sub_key:
            sub_widget = self.inputs.get(sub_key)
            # Read field_config Qt property to get the "multiple" flag.
            # NOTE: property("multiple") would always return None because only
            # "field_config" is stored as a Qt property, not "multiple" directly.
            # That was the root cause of the textbox never appearing: sub IDs were
            # stored as a single UUID string → json.loads() failed → setCurrentData([])
            # → nothing checked → selectionChanged not triggered → textbox stayed hidden.
            field_cfg = sub_widget.property("field_config") if sub_widget else None
            is_multiple = field_cfg.get("multiple", False) if isinstance(field_cfg, dict) else False
            # Also treat any CheckableComboBox as multiple by definition
            if sub_widget and isinstance(sub_widget, CheckableComboBox) and not isinstance(sub_widget, RadioComboBox):
                is_multiple = True
            self.asset_data[sub_key] = final_sub_ids if is_multiple else (final_sub_ids[0] if final_sub_ids else None)
             
        if text_key and api_text in self._raw_asset_data:
            self.asset_data[text_key] = self._raw_asset_data.get(api_text)
            
        # Specific Activos mapping for linked processes
        if self.config.get("endpoint") == "/activos":
            linked_p = self._raw_asset_data.get("proceso_vinculado_ids") or self._raw_asset_data.get("rat_id")
            if linked_p: self.asset_data["procesos_vinculados"] = linked_p

    def _check_finished(self):
        if self.pending_loads > 0:
            self.pending_loads -= 1

        if self.pending_loads <= 0:
            self._allow_asset_reapply = False
            self.loading_overlay.hide_loading()
            # Initial validation for "New" mode (might be 0/X)
            self._validate_steps_progress()

    def _try_set_values(self):
        if not self.asset_data or self.is_setting_values:
            return
            
        self.is_setting_values = True
        try:
            # --- Hierarchical Categories Unflattening (Activos & RAT) ---
            self._unflatten_hierarchical_categories()

            # Special first pass: Trigger fields
            # If we have dependencies, we might need to load them first.
            # For simplicity in this generic version, we just try to set everything.
            # If a combo depends on another, setting the parent might trigger the load.
            
            # Use a snapshot to avoid "dictionary changed size during iteration"
            # when signal handlers trigger re-entrant updates.
            for key, widget in list(self.inputs.items()):
                value = self.asset_data.get(key)
                if value is None: continue
                
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QPlainTextEdit):
                    widget.setPlainText(str(value))
                elif isinstance(widget, QDateEdit):
                    # Assume value comes as "yyyy-MM-dd" string from API
                    if value:
                        d = QDate.fromString(str(value), "yyyy-MM-dd")
                        if d.isValid():
                            widget.setDate(d)
                elif isinstance(widget, FilePickerWidget):
                    widget.setText(str(value))
                elif isinstance(widget, FileTextWidget):
                    widget.set_data(value)
                elif isinstance(widget, EditableTableWidget):
                    widget.set_data(value)
                elif isinstance(widget, CheckableComboBox):
                    # RadioComboBox inherit from CheckableComboBox, so we handle it here
                    # value puede venir como JSON string o list (Checkable) o single ID (Radio)
                    
                    is_radio = isinstance(widget, RadioComboBox) or widget.__class__.__name__ == "RadioComboBox"
                    
                    if is_radio:
                        # Radio stores a single ID but setCurrentData expects a list
                        if not isinstance(value, list):
                            value = [value]
                    else:
                        # Standard Checkable (Multi)
                        if isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except Exception:
                                value = []
    
                        if not isinstance(value, list):
                            value = []
    
                    widget.setCurrentData(value)
                    
                    # Check if this key triggers others (e.g. nested subcategory combo)
                    if key in self.dependencies:
                        # For nested dependencies, only call _on_trigger_changed if the
                        # dependent combo is EMPTY. If it already has items it was already
                        # populated by _on_combo_data and calling _on_trigger_changed again
                        # would clear it, remove the selection, and hide the dependent textbox.
                        skip_trigger = False
                        for dep_key in self.dependencies[key]:
                            dep_cfg = self.dependency_configs.get(dep_key, {})
                            dep_w = self.inputs.get(dep_key)
                            if dep_cfg.get("depends_type") == "nested" and dep_w and dep_w.model().rowCount() > 0:
                                skip_trigger = True
                                break
                        if not skip_trigger:
                            self._on_trigger_changed(key)
    
                elif isinstance(widget, RiskMatrixWidget):
                    widget.set_data(value)
    
                elif isinstance(widget, ComboTextWidget):
                    widget.set_data(value)
    
                elif isinstance(widget, QComboBox):
                    self._set_combo_value(widget, value)
                    
                    # Check if this key triggers others
                    # Force trigger update if needed
                    if key in self.dependencies:
                         self._on_trigger_changed(key, widget.currentIndex())
        finally:
            self.is_setting_values = False
            # After all values are set, fire direct visibility handlers so conditional
            # blocks (like the free-text for "Otros datos personales") reflect the
            # current selections. Use QTimer to run after all pending signals settle.
            QTimer.singleShot(20, self._apply_all_direct_visibility)
            QTimer.singleShot(30, self._recheck_all_visibility)

    def _set_combo_value(self, combo, value):
        index = combo.findData(value)
        if index != -1:
            combo.setCurrentIndex(index)
        else:
             # Fallback string match
             val_str = str(value)
             for i in range(combo.count()):
                 if str(combo.itemData(i)) == val_str:
                     combo.setCurrentIndex(i)
                     return



    def _on_load_error(self, error):
        print(f"Generic Load Error: {error}")
        self._check_finished()

    def _on_step_changed(self, index):
        self.stack.setCurrentIndex(index)

    # ===============================
    # Data Loading
    # ===============================

    def _init_async_load(self):
        # Force initial validation to update counters (e.g. 0/X)
        self._validate_steps_progress()
        
        self.loading_overlay.show_loading()
        
        # Identify combos to load from config
        combos_to_load = []
        for section in self.config.get("sections", []):
            for field in self._iter_fields(section.get("fields", [])):
                ftype = field.get("type", "")
                if ftype == "combo_text" and field.get("source") and not field.get("depends_on"):
                    key = field["key"]
                    ct_widget = self.inputs.get(key)
                    if isinstance(ct_widget, ComboTextWidget):
                        endpoint = field["source"]
                        cache_key = field.get("cache_key", f"cache_{key}")
                        combos_to_load.append((ct_widget.combo, endpoint, cache_key))
                elif ftype in ["combo", "radio_combo"] and (field.get("source") or field.get("cache_key")) and not field.get("depends_on"):
                    key = field["key"]
                    widget = self.inputs.get(key)
                    endpoint = field.get("source", "")
                    cache_key = field.get("cache_key", f"cache_{key}")
                    combos_to_load.append((widget, endpoint, cache_key))

        self.pending_loads = len(combos_to_load)
        if self.is_edit:
            self.pending_loads += 1
            
        # Launch Combo Loaders
        for combo, endpoint, cache_key in combos_to_load:
            self._start_combo_loader(combo, endpoint, cache_key)
            
        # Launch Record Loader
        if self.is_edit:
            self._start_record_loader()
            
        if self.pending_loads == 0:
             self.loading_overlay.hide_loading()

    def _start_combo_loader(self, combo, endpoint, cache_key, track_pending=True):
        worker = ComboLoaderRunnable(self.catalogo_service.get_catalogo, endpoint, cache_key)
        self._active_runnables.append(worker)
        
        worker.signals.result.connect(partial(self._on_combo_data, combo))
        worker.signals.error.connect(self._on_load_error)
        if track_pending:
            worker.signals.finished.connect(self._check_finished)
        
        self.thread_pool.start(worker)

    def _start_record_loader(self):
        endpoint_base = self.config.get("endpoint")
        # 🔑 Soporte opcional para endpoint /full en edición
        if self.is_edit and self.config.get("endpoint_edit_full"):
            url = f"{endpoint_base}/{self.record_id}/full"
        else:
            url = f"{endpoint_base}/{self.record_id}"
        
        worker = ApiWorker(lambda: self.api.get(url), parent=self)
        worker.finished.connect(self._on_record_data)
        worker.error.connect(self._on_load_error)
        worker.start()

    def _on_combo_data(self, combo, data):
        # Handle paginated response if data is a dict
        items = []
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
            
        # Store processed items for potential nested dependencies
        combo.setProperty("raw_data", items)
        combo.clear()
        
        count = len(items)
        print(f"[UI DEBUG] Populating combo. Items received: {count}")

        if items:
            is_radio = isinstance(combo, RadioComboBox) or combo.__class__.__name__ == "RadioComboBox"
            for item in items:
                if not isinstance(item, dict): continue
                
                if is_radio:
                    # Specific RadioComboBox logic for tooltips and codes
                    full_desc = item.get("descripcion") or item.get("nombre") or ""
                    tooltip_text = ""
                    primary_text = full_desc
                    if "." in full_desc:
                        try:
                            primary_text, tooltip_text = full_desc.split(".", 1)
                            primary_text = primary_text.strip()
                            tooltip_text = tooltip_text.strip()
                        except: pass
                    
                    code = item.get("codigo_proceso")
                    label = f"{code}. {primary_text}" if code else primary_text
                    combo.addItem(label, item.get("id"), tooltip=tooltip_text)
                else:
                    # Standard label logic
                    label = item.get("nombre") or item.get("descripcion") or item.get("label") or str(item.get("id"))
                    combo.addItem(label, item.get("id"))
        
        # Support for extra_options (like "Otro") from JSON config
        field_cfg = combo.property("field_config")
        if field_cfg and "extra_options" in field_cfg:
            for ext in field_cfg["extra_options"]:
                label = ext.get("nombre", "Otro")
                value = ext.get("id", "Otro")
                found = False
                for i in range(combo.count()):
                    if str(combo.itemData(i)) == str(value) or combo.itemText(i) == label:
                        found = True
                        break
                if not found:
                    combo.addItem(label, value)
                 
        # Ensure no default selection
        combo.setCurrentIndex(-1)
        if hasattr(combo, 'lineEdit') and combo.lineEdit():
             combo.lineEdit().clear()
        
        if hasattr(combo, 'updateText'):
             combo.updateText()

        # Re-try applying value to THIS combo if we already have asset_data (Edit mode).
        if self.asset_data and not self.is_setting_values:
            for k, w in list(self.inputs.items()):
                if w is combo:
                    pending_val = self.asset_data.get(k)
                    if pending_val is not None:
                        if hasattr(combo, 'setCurrentData'):
                            if isinstance(pending_val, str):
                                try:
                                    pending_val = json.loads(pending_val)
                                except Exception:
                                    pending_val = [pending_val]
                            if not isinstance(pending_val, list):
                                pending_val = [pending_val]
                            combo.setCurrentData(pending_val)
                        else:
                            self._set_combo_value(combo, pending_val)
                            
                            # If this combo triggers others (like origen_datos triggers activos), run logic
                            if k in self.dependencies:
                                self._on_trigger_changed(k, combo.currentIndex())
                    break
                    
        # Always recheck visibility after populating a combo — covers manual and edit mode
        QTimer.singleShot(10, self._recheck_all_visibility)
        QTimer.singleShot(15, self._apply_all_direct_visibility)


    # ===============================
    # Dependency Logic
    # ===============================
    def _on_trigger_changed(self, trigger_key, index=None):
        # Trigger key changed. Find dependents.
        dependents = self.dependencies.get(trigger_key, [])
        trigger_widget = self.inputs.get(trigger_key)
        if not trigger_widget: return
        
        trigger_val = trigger_widget.currentData()
        
        for dep_key in dependents:
            dep_config = self.dependency_configs.get(dep_key)
            if not dep_config: continue
            
            dep_widget = self.inputs.get(dep_key)
            if not dep_widget: continue

            # If trigger is empty, clear dependent and skip load
            if not trigger_val:
                dep_widget.clear()
                if isinstance(dep_widget, QComboBox) and not dep_widget.isEditable():
                     dep_widget.setCurrentIndex(-1)
                continue
            
            # Load dependency
            # Template: /setup/divisiones?subsecretaria_id={value}
            template = dep_config.get("dependency_endpoint_template")
            if template:
                url = template.replace("{value}", str(trigger_val))
                cache_key = dep_config.get("cache_key")
                
                # If we have a cache key, make it specific to this parameter value
                if cache_key:
                    cache_key = f"{cache_key}_{str(trigger_val)}"
                
                self._load_dependent_combo(dep_widget, url, cache_key)
            
            # --- NEW: Nested Dependency Logic ---
            elif dep_config.get("depends_type") == "nested":
                nested_key = dep_config.get("nested_key", "subcategorias")
                raw_data = trigger_widget.property("raw_data")
                
                if not raw_data:
                    dep_widget.clear()
                    continue
                
                # Convert selection to set of strings for robust comparison
                selected_ids = set()
                if isinstance(trigger_val, list):
                    selected_ids = {str(v) for v in trigger_val}
                elif trigger_val:
                    selected_ids = {str(trigger_val)}
                
                print(f"[RELOAD DEBUG] Trigger '{trigger_key}' selected IDs: {selected_ids}")
                
                sub_items = []
                for item in raw_data:
                    item_id = str(item.get("id"))
                    if item_id in selected_ids:
                        sub_items.extend(item.get(nested_key, []))
                
                # Deduplicate subitems if necessary (by ID)
                final_sub_items = []
                seen_ids = set()
                for si in sub_items:
                    si_id = si.get("id")
                    if si_id not in seen_ids:
                        final_sub_items.append(si)
                        seen_ids.add(si_id)
                
                # Populate dependent combo
                self._on_combo_data(dep_widget, final_sub_items)
                
                # --- CRITICAL FIX ---
                # After populating the nested combo, apply any pending value from asset_data.
                # We CANNOT rely on _on_combo_data's pending-value block (it checks
                # `not self.is_setting_values` which is True here). We must apply directly.
                if self.asset_data and hasattr(dep_widget, 'setCurrentData'):
                    pending_val = self.asset_data.get(dep_key)
                    if pending_val is not None:
                        if isinstance(pending_val, str):
                            try:
                                import json
                                pending_val = json.loads(pending_val)
                            except Exception:
                                pending_val = [pending_val]
                        if not isinstance(pending_val, list):
                            pending_val = [pending_val]
                        LoggerService().log_event(
                            f"[NESTED FIX] Applying pending val {pending_val} to '{dep_key}'"
                        )
                        dep_widget.setCurrentData(pending_val)
                
                # Force visibility check AFTER value is applied (not before)
                self._check_visibility(trigger_key)
                # Also recheck source-of-visibility for the nested combo
                if dep_key in self.visibility_map:
                    self._check_visibility(dep_key)

    def _load_dependent_combo(self, combo, url, cache_key=None):
        # Create a worker just for this
        combo.clear()
        
        # Use CatalogoService to leverage cache if available
        worker = ComboLoaderRunnable(self.catalogo_service.get_catalogo, url, cache_key)
        self._active_runnables.append(worker)
        
        worker.signals.result.connect(partial(self._on_dependent_data, combo))
        worker.signals.error.connect(self._on_load_error)
        # We don't increment pending_loads for dynamic reloads to avoid showing the overlay
        # but we do want to cleanup
        self.thread_pool.start(worker)

    def _on_dependent_data(self, combo, data):
        combo.clear()
        if data:
            for item in data:
                 combo.addItem(item["nombre"], item["id"])
                 
        # If we have asset data pending for this combo (e.g. during initial load), set it now
        # We need to know which key this combo belongs to...
        # Reverse lookup or closure?
        # A bit complex. For now, rely on user re-selecting or simple flow.
        # Ideally, we should check self.asset_data again for this specific combo.
        
        # Hacky reverse lookup
        found_key = None
        for k, v in self.inputs.items():
            if v == combo:
                found_key = k
                break
        
        if found_key and self.asset_data:
             val = self.asset_data.get(found_key)
             if val:
                 self._set_combo_value(combo, val)
                 
    
    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _rebuild_footer(self, index, is_last):
        layout = self.footer_layouts.get(index)
        if not layout:
            return

        self._clear_layout(layout)

        # Standard buttons
        if index > 0:
            prev_btn = QPushButton("Anterior")
            prev_btn.setObjectName("secondaryButton")
            prev_btn.clicked.connect(self.sidebar.prev_step)
            layout.addWidget(prev_btn)
        
        layout.addStretch()

        if not is_last:
            next_btn = QPushButton("Siguiente")
            next_btn.setObjectName("primaryButton")
            next_btn.clicked.connect(self.sidebar.next_step)
            layout.addWidget(next_btn)
        else:
            # The Save button is only in the footer
            save_btn = QPushButton("Guardar")
            save_btn.setObjectName("primaryButton")
            save_btn.clicked.connect(self._submit)
            layout.addWidget(save_btn)

    def _wrap_step_content(self, content_widget, title_text, desc_text, index, total):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QVBoxLayout()
        t = QLabel(title_text)
        t.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")
        d = QLabel(desc_text)
        d.setStyleSheet("font-size: 14px; color: #64748b;")
        d.setWordWrap(True)
        header.addWidget(t)
        header.addWidget(d)
        layout.addLayout(header)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e2e8f0;")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1) 
        
        # Footer
        footer_container = QWidget()
        footer_container.setObjectName(f"footerContainer_{index}")
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.footer_layouts[index] = footer_layout
        
        # Build initial footer
        self._rebuild_footer(index, index == total - 1)
            
        layout.addWidget(footer_container)
        return container

    # ===============================
    # Submit
    # ===============================
    def _submit(self):
        # Determine payload based on form type
        if self.config.get("endpoint") == "/eipd":
             payload = self._build_eipd_payload()
        else:
             payload = self._build_generic_payload()
        
        endpoint = self.config.get("endpoint")

        # 🛡️ Validación estricta y obligatoria de campos y formato
        if endpoint in ["/activos", "/users/complete-registration"]:
            missing = self._get_missing_required_fields()
            
            errors = []
            if missing:
                errors.append("Por favor complete los siguientes campos requeridos antes de guardar:\n\n" + "\n".join(missing))
                
            if endpoint == "/users/complete-registration":
                import re
                nombre_val = payload.get("nombre", "")
                email_val = payload.get("email", "")
                
                if nombre_val and len(nombre_val) < 3:
                    errors.append("\n- El campo 'Nombre' debe tener al menos 3 caracteres.")
                    
                if email_val and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_val):
                    errors.append("\n- El campo 'EMAIL' debe tener un formato válido (ejemplo@dominio.cl).")
                    
            if errors:
                LoggerService().log_error("Validación fallida: campos obligatorios o formato incorrecto", None)
                title = "Campos Obligatorios" if missing and len(errors) == 1 else "Validación de Formulario"
                AlertDialog(
                    title=title,
                    message="\n".join(errors),
                    icon_path="src/resources/icons/alert_error.svg",
                    confirm_text="Entendido",
                    parent=self
                ).exec()
                return # Abort submission

        if not self.is_edit:
            if endpoint == "/activos":
                payload = self._apply_activo_create_defaults(payload)
            elif endpoint == "/eipd":
                payload = self._apply_eipd_create_defaults(payload)
            elif endpoint == "/users/complete-registration":
                # Construcción del payload específico según requerimiento exacto de API
                payload = {
                    "nombre_completo": payload.get("nombre", ""),
                    "email": payload.get("email", ""),
                    "division_id": "2cbf9f16-5953-4b36-9cb8-a8e9ffb62800"
                }
            else:
                payload = self._apply_generic_required_defaults(payload)
        
        try:
            if endpoint == "/users/complete-registration":
                user_id = self.asset_data.get("backend_id")
                final_endpoint = f"/users/{user_id}/complete-registration"
                self.api.put(final_endpoint, payload)
                msg = "Registro completado con éxito."
            elif self.is_edit:
                if endpoint == "/activos":
                    self.api.patch(f"{endpoint}/{self.record_id}", payload)
                else:
                    self.api.put(f"{endpoint}/{self.record_id}", payload)
                msg = f"{self.config.get('title_edit', 'Registro')} actualizado correctamente."
                # 🔄 Actualizar cache de inventario
                if endpoint == "/activos":
                    InventoryCacheService().refresh_inventory_cache()
            else:
                res = self.api.post(endpoint, payload)
                # Capture ID from response if possible
                if isinstance(res, dict):
                    self.record_id = res.get("id") or res.get("backend_id") or res.get("eipd_id")
                
                msg = f"{self.config.get('title_new', 'Registro')} creado correctamente."
                # 🔄 Actualizar cache de inventario
                if endpoint == "/activos":
                    InventoryCacheService().refresh_inventory_cache()

            LoggerService().log_event(msg)
            
            AlertDialog(
                title="Éxito",
                message=msg,
                icon_path="src/resources/icons/alert_success.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()
            
            self.accept()
            
        except Exception as e:
            LoggerService().log_error("Error guardar form", e)
            AlertDialog(
                title="Error",
                message=str(e),
                icon_path="src/resources/icons/alert_error.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()

    def _first_combo_id(self, key):
        widget = self.inputs.get(key)
        if isinstance(widget, QComboBox) and widget.count() > 0:
            return widget.itemData(0)
        return None

    def _first_id_from_endpoint(self, endpoint):
        try:
            items = self.api.get(endpoint)
            if isinstance(items, list) and items:
                first = items[0]
                if isinstance(first, dict):
                    return first.get("id")
        except Exception:
            return None
        return None

    def _apply_activo_create_defaults(self, payload):
        # Solo campos de texto básicos si vienen vacíos para evitar errores de esquema, 
        # pero para combos catalógicos (FK) se debe respetar la selección del usuario.
        payload["nombre_activo"] = payload.get("nombre_activo") or "Activo sin nombre"
        payload["responsable"] = payload.get("responsable") or "Sin responsable"
        return payload

    def _apply_eipd_create_defaults(self, payload):
        if not payload.get("rat_id"):
            payload["rat_id"] = (
                self._first_combo_id("identificacion_rat_catalogo")
                or self._first_id_from_endpoint("/rat/catalogo")
            )
        return payload

    def _is_missing_value(self, value):
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, list):
            return len(value) == 0
        return False

    def _iter_fields(self, fields):
        for field in fields or []:
            if field.get("type") == "group":
                yield from self._iter_fields(field.get("fields", []))
            else:
                yield field

    def _apply_generic_required_defaults(self, payload):
        sections = self.config.get("sections", [])
        for section in sections:
            for field in self._iter_fields(section.get("fields", [])):
                if not field.get("required", False):
                    continue

                key = field.get("key")
                if not key:
                    continue

                current = payload.get(key)
                if not self._is_missing_value(current):
                    continue

                ftype = field.get("type", "text")
                default_value = None

                if ftype in ["combo", "combo_static", "radio_combo"]:
                    # No asignar el primer ID por defecto. El usuario debe seleccionar uno.
                    default_value = None
                elif ftype in ["text", "textarea"]:
                    default_value = "Pendiente"
                elif ftype == "file":
                    default_value = "pendiente"
                elif ftype == "file_textarea":
                    default_value = {"file": "pendiente", "text": "pendiente"}

                payload[key] = default_value

        return payload

    def _build_generic_payload(self):
        payload = {}
        for key, widget in self.inputs.items():
            # Saltar campos que no están visibles (basado en lógica condicional)
            # Esto cumple con el Flujo 3: no enviar campos ocultos
            block = self.blocks.get(key)
            if block and block.isHidden():
                continue

            val = None
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                val = text if text else None
            elif isinstance(widget, QDateEdit):
                 val = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
                 text = widget.toPlainText().strip()
                 val = text if text else None
            elif isinstance(widget, FilePickerWidget):
                 text = widget.text().strip()
                 val = text if text else None
            elif isinstance(widget, FileTextWidget):
                 val = widget.get_data()
            elif isinstance(widget, RiskMatrixWidget):
                val = widget.get_data()
            elif isinstance(widget, EditableTableWidget):
                val = widget.get_data()
            elif isinstance(widget, ComboTextWidget):
                val = widget.get_data()
            elif isinstance(widget, QComboBox):
                if isinstance(widget, RadioComboBox) or widget.__class__.__name__ == "RadioComboBox":
                    # RadioComboBox returns a list from currentData but we want a single ID
                    data_list = widget.currentData()
                    val = data_list[0] if data_list else None
                else:
                    val = widget.currentData()
            
            payload[key] = val
            
        # Activos Mapping: Form keys -> Backend fields (Linked Processes)
        if self.config.get("endpoint") == "/activos":
            # The backend expects 'proceso_vinculado_ids' as an array of UUIDs
            if "procesos_vinculados" in payload:
                val = payload.pop("procesos_vinculados")
                if val:
                    # RadioComboBox.currentData() returns a list, ensure it's correct
                    payload["proceso_vinculado_ids"] = val if isinstance(val, list) else [val]
                else:
                    payload["proceso_vinculado_ids"] = []
            
            # Remove fields not present in Swagger schema to avoid 422 (strict validation)
            if "rat_id" in payload:
                payload.pop("rat_id")

            # --- NEW: Activos Categorias Mapping (M2M flattening) ---
            cat_ids = payload.get("categoria_ids", [])
            if not isinstance(cat_ids, list):
                cat_ids = [cat_ids] if cat_ids else []
            
            # Sub-category ID from hierarchical helper
            spec_id = payload.pop("categoria_sensible_especifica", None)
            if spec_id:
                if spec_id not in cat_ids:
                    cat_ids.append(spec_id)
            
            payload["categoria_ids"] = cat_ids
            
            # Map free text 'Otro' to backend key
            if "categoria_sensible_especificar_otro" in payload:
                payload["categoria_otro"] = payload.pop("categoria_sensible_especificar_otro")
                LoggerService().log_event(f"Sent categoria_otro: {payload['categoria_otro']}")
            elif "categoria_otro" not in payload:
                 payload["categoria_otro"] = None
             
        # RAT Mapping: Form keys -> Backend fields (Hierarchy)
        if self.config.get("endpoint") == "/rat":
            # Determine mapping based on available inputs
            mapping_found = False
            # [Main Key, Sub Key, Text Key, API Main, API Sub, API Text]
            rat_maps = [
                ["categorias_datos_inst", "categorias_datos_sensibles_inst", "categorias_datos_otro_inst", "categoria_datos", "categoria_datos_sensibles", "categoria_datos_otro"],
                ["categorias_datos_personales", "categorias_datos_sensibles", "categorias_datos_otro", "categoria_datos", "categoria_datos_sensibles", "categoria_datos_otro"]
            ]
            
            for rm in rat_maps:
                m_key, s_key, t_key, a_main, a_sub, a_text = rm
                if m_key in payload:
                    mapping_found = True
                    # 1. Main Categories (List -> JSON String)
                    main_ids = payload.pop(m_key, []) or []
                    payload[a_main] = json.dumps(main_ids if isinstance(main_ids, list) else ([main_ids] if main_ids else []))
                    
                    # 2. Sub Categories (List -> JSON String)
                    sub_ids = payload.pop(s_key, []) or []
                    payload[a_sub] = json.dumps(sub_ids if isinstance(sub_ids, list) else ([sub_ids] if sub_ids else [])) if sub_ids else None
                    
                    # 3. Free Text
                    payload[a_text] = payload.pop(t_key, None)
                    break
        
        # Common fields (Only for New records, Update doesn't allow changing creator)
        if not self.is_edit:
            payload["creado_por_usuario_id"] = "e13f156d-4bde-41fe-9dfa-9b5a5478d257"
        return payload

    def _build_eipd_payload(self):
        # 1. Build base payload with all fields (including Section 0)
        # generic_payload handles all input types (text, files, combos, etc.)
        payload = self._build_generic_payload()
        
        # 2. Restructure Ambitos (Section 1)
        # These are individual fields in the form but nested in the API
        ambitos_list = []
        prefix_map = {
            "LICITUD": "licitud",
            "FINALIDAD": "finalidad",
            "PROPORCIONABILIDAD": "proporcionabilidad",
            "CALIDAD": "calidad",
            "RESPONSABILIDAD": "responsabilidad",
            "SEGURIDAD": "seguridad",
            "TRANSPARENCIA": "transparencia",
            "CONFIDENCIALIDAD": "confidencialidad",
            "COORDINACION": "coordinacion"
        }
        
        for name, code in AMBITO_CODES.items():
            p = prefix_map.get(code)
            if not p: continue
            
            # Pop keys from payload root so they are not sent twice
            criterios = payload.pop(f"{p}_criterios", "")
            resumen = payload.pop(f"{p}_resumen", "")
            prob = payload.pop(f"{p}_probabilidad", None)
            imp = payload.pop(f"{p}_impacto", None)
            
            ambitos_list.append({
                "ambito_codigo": code.lower(),
                "criterios_evaluacion": criterios or "",
                "resumen": resumen or "",
                "probabilidad": prob,
                "impacto": imp,
                "nivel": self._calculate_risk_level(prob, imp)
            })
        
        payload["ambitos"] = ambitos_list

        # 3. Restructure Riesgos (Section 2 - Matrix)
        raw_risks = payload.pop("matriz_riesgos", [])
        formatted_risks = []
        if isinstance(raw_risks, list):
            for row in raw_risks:
                name = row.get("ambito")
                code = AMBITO_CODES.get(name)
                if not code: continue 
                
                formatted_risks.append({
                    "ambito_codigo": code.lower(),
                    "descripcion": row.get("descripcion") or "",
                    "nivel_desarrollo": row.get("nivel_desarrollo") or "",
                    "riesgo_transversal": row.get("riesgo_transversal") or "",
                    "probabilidad": row.get("probabilidad") or "",
                    "impacto": row.get("impacto") or "",
                    "nivel_riesgo": row.get("nivel_riesgo") or ""
                })
        payload["riesgos"] = formatted_risks
        
        # 4. Handle rat_id consistency
        # In eipd.json Section 0, the key is 'identificacion_rat_catalogo'
        rat_id = payload.pop("identificacion_rat_catalogo", None)
        if not rat_id and self.asset_data:
             rat_id = self.asset_data.get("rat_id")
        
        payload["rat_id"] = rat_id
        
        # The EIPD API expects 'creado_por' instead of 'creado_por_usuario_id'
        payload["creado_por"] = payload.get("creado_por_usuario_id")
        
        return payload

    def _sync_risk_matrix(self, prefix):
        """Synchronizes a row in the Risk Matrix with data from the Ámbitos section."""
        w_matrix = self.inputs.get("matriz_riesgos")
        if not w_matrix or not hasattr(w_matrix, "update_row"):
            return

        prefix_to_full = {
            "licitud": "Lícitud y Lealtad",
            "finalidad": "Finalidad",
            "proporcionabilidad": "Proporcionabilidad",
            "calidad": "Calidad",
            "responsabilidad": "Responsabilidad",
            "seguridad": "Seguridad",
            "transparencia": "Transparencia e Información",
            "confidencialidad": "Confidencialidad",
            "coordinacion": "Coordinación"
        }
        
        full_name = prefix_to_full.get(prefix)
        if not full_name: return
        
        try:
            row_index = EIPD_AMBITOS.index(full_name)
        except ValueError:
            return

        # Get Widgets
        w_resumen = self.inputs.get(f"{prefix}_resumen")
        w_prob = self.inputs.get(f"{prefix}_probabilidad")
        w_imp = self.inputs.get(f"{prefix}_impacto")

        # Extract values for the table (text) and calculation (data/ID)
        data = {
            "resumen": w_resumen.toPlainText().strip() if hasattr(w_resumen, "toPlainText") else "",
            "probabilidad": w_prob.currentText() if isinstance(w_prob, QComboBox) else "",
            "impacto": w_imp.currentText() if isinstance(w_imp, QComboBox) else "",
        }
        
        prob_id = w_prob.currentData() if isinstance(w_prob, QComboBox) else None
        imp_id = w_imp.currentData() if isinstance(w_imp, QComboBox) else None
        
        data["nivel_riesgo"] = self._calculate_risk_level(prob_id, imp_id)
        
        # Update Row
        w_matrix.update_row(row_index, data)

    def _get_input_value(self, key):
        widget = self.inputs.get(key)
        if not widget: return None
        
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
             return widget.toPlainText().strip()
        elif isinstance(widget, QComboBox):
             return widget.currentData() # ID
        return None

    def _calculate_risk_level(self, prob, imp):
        """Calculates risk level (Bajo, Medio, Alto, Muy Alto) based on probability and impact."""
        if not prob or not imp: return "Bajo"
        
        score_map = {
            "despreciable": 1,
            "limitado": 2,
            "significativo": 3,
            "maximo": 4
        }
        
        p_val = score_map.get(str(prob).lower(), 0)
        i_val = score_map.get(str(imp).lower(), 0)
        
        score = p_val * i_val
        if score <= 1: return "Bajo"
        if score <= 4: return "Medio"
        if score <= 9: return "Alto"
        return "Muy Alto"

    
    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    # ======================================================
    # Close Prevention
    # ======================================================

    def reject(self):
        """Override Esc key and reject() behavior to ask for confirmation."""
        self._confirm_close_dialog()

    def closeEvent(self, event):
        """Override window X button to ask for confirmation."""
        # result = self._confirm_close_dialog()
        # if result:
        #     event.accept()
        # else:
        #     event.ignore()
        # Wait, since reject() is called by QDialog when closing via X in some cases, 
        # but better handle closeEvent explicitly.
        
        # We need to block close if the user cancels the confirmation
        if self._confirm_close_dialog_bool():
            event.accept()
        else:
            event.ignore()

    def _confirm_close_dialog_bool(self) -> bool:
        """Shows the confirmation dialog and returns True if user wants to close."""
        dialog = AlertDialog(
            title="Confirmar Cierre",
            message="¿Está seguro que desea cerrar la ventana? Se perderán los cambios no guardados.",
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Cerrar ventana",
            cancel_text="Cancelar",
            parent=self
        )
        return bool(dialog.exec())

    def _confirm_close_dialog(self):
        """Shows the confirmation dialog and rejects if user confirms."""
        if self._confirm_close_dialog_bool():
            super().reject()
