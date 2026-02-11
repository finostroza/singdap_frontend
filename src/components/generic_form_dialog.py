import json
import os
from functools import partial

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, 
    QComboBox, QFormLayout, QProgressBar, QDateEdit, QFileDialog, 
    QTextEdit, QPlainTextEdit, QApplication
)
from PySide6.QtCore import Qt, QTimer, QThreadPool, QDate

from src.components.risk_matrix_widget import RiskMatrixWidget
from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.components.wizard_sidebar import WizardSidebar
from src.components.loading_overlay import LoadingOverlay
from src.services.catalogo_service import CatalogoService
from src.workers.combo_loader import ComboLoaderRunnable
from src.workers.api_worker import ApiWorker
from src.services.logger_service import LoggerService
from src.components.custom_inputs import CheckableComboBox

EIPD_AMBITOS = [
    "Licitud y Lealtad",
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
    "Licitud y Lealtad": "LICITUD",
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
        self.dependency_configs = {} # Was missing too if I removed it? Let's check previously. Yes I removed it.

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

                header_layout = QHBoxLayout()
                header_layout.setContentsMargins(0, 0, 0, 0) # No extra margin for header either

                title = QLabel(field.get("label", ""))
                title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")

                header_layout.addWidget(title)
                header_layout.addStretch()
                v.addLayout(header_layout)

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
                    widget.currentIndexChanged.connect(
                        partial(self._on_trigger_changed, key)
                    )

            if "depends_on" in field:
                self.dependency_configs[key] = field

            # Validation
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, CheckableComboBox):
                widget.selectionChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._validate_steps_progress)

            block_layout.addWidget(widget)
            layout.addWidget(field_block)

        layout.addStretch()

        # Visibility triggers
        for source_key in self.visibility_map.keys():
            if source_key in self.inputs:
                self._connect_visibility_trigger(source_key, self.inputs[source_key])
                self._check_visibility(source_key)

        return w
    

    def _connect_visibility_trigger(self, key, widget):
        # We need to accept whatever arguments the signal emits (e.g. index for combo) and ignore them
        try:
            # Safety check for deleted objects
            if not widget: return
            
            # Robust check for CheckableComboBox
            is_checkable = isinstance(widget, CheckableComboBox) or widget.__class__.__name__ == "CheckableComboBox"
            
            if is_checkable:
                 if hasattr(widget, "selectionChanged"):
                     widget.selectionChanged.connect(lambda *args: self._check_visibility(key), Qt.UniqueConnection)
            
            elif isinstance(widget, QComboBox):
                 widget.currentIndexChanged.connect(lambda *args: self._check_visibility(key), Qt.UniqueConnection)
            
            elif isinstance(widget, QLineEdit):
                 widget.textChanged.connect(lambda *args: self._check_visibility(key), Qt.UniqueConnection)
                
        except (TypeError, RuntimeError):
            pass # Already connected, connection failed, or object deleted

    def _check_visibility(self, source_key):
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
                
                if isinstance(val, list): # Checkable returns list
                     if req_val in val: match = True
                else:
                     if str(val) == str(req_val): match = True
                
                target_block.setVisible(match)
                
            # Retrigger validation because required fields might have appeared/disappeared
            self._validate_steps_progress()
            
        except RuntimeError:
            return  # Object deleted

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
            inp.setStyleSheet("""
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
                    
                if not self.is_edit and not is_multiple:
                     inp.setCurrentIndex(-1)

            return inp
            
        elif ftype == "file":
             return FilePickerWidget()
             
        elif ftype == "file_textarea":
             return FileTextWidget()
         
        elif ftype == "risk_matrix":
            w = RiskMatrixWidget()
            w.preload_ambitos(EIPD_AMBITOS)
            return w
    
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
            
            for field in section.get("fields", []):
                if field.get("required", False):
                    key = field["key"]
                    widget = self.inputs.get(key)
                    
                    try:
                        # Check visibility relative to the page (handling hidden tabs)
                        # If the field block was hidden by logic, isVisibleTo(page) will be False
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
                        continue # Object deleted during iteration
            
            # Update Sidebar Step
            if i < len(self.sidebar.step_widgets):
                step_widget = self.sidebar.step_widgets[i]
                if hasattr(step_widget, "update_required_count"):
                    try:
                        step_widget.update_required_count(filled_req, total_req)
                    except RuntimeError:
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

    def _is_field_filled(self, widget, field):
        if not widget: return False
        
        try:
            # Robust check for CheckableComboBox
            is_checkable = isinstance(widget, CheckableComboBox) or widget.__class__.__name__ == "CheckableComboBox"
            
            if isinstance(widget, QLineEdit):
                return bool(widget.text().strip())
                
            elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
                return bool(widget.toPlainText().strip())
                 
            elif is_checkable:
                # Check text presence as visual confirmation of selection
                return bool(widget.lineEdit().text().strip())
                
            elif isinstance(widget, QComboBox):
                if widget.currentIndex() == -1: return False
                return True
                
            elif isinstance(widget, FilePickerWidget):
                return bool(widget.text().strip())
                
            elif isinstance(widget, FileTextWidget):
                data = widget.get_data()
                return bool(data["file"].strip())
        except RuntimeError:
            return False
            
        return False

    def _on_record_data(self, data):
        # EIPD Flattening Logic
        if self.config.get("endpoint") == "/eipd":
            data = self._flatten_eipd_data(data)

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

    def _check_finished(self):
        self.pending_loads -= 1
        if self.pending_loads <= 0:
            self.loading_overlay.hide_loading()
            # Initial validation for "New" mode (might be 0/X)
            self._validate_steps_progress()

    def _try_set_values(self):
        if not self.asset_data: return
        
        # Special first pass: Trigger fields
        # If we have dependencies, we might need to load them first.
        # For simplicity in this generic version, we just try to set everything.
        # If a combo depends on another, setting the parent might trigger the load.
        
        for key, widget in self.inputs.items():
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
            elif isinstance(widget, CheckableComboBox):
                # value puede venir como JSON string o list
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except Exception:
                        value = []

                if not isinstance(value, list):
                    value = []

                # Marcar checks según itemData
                for i in range(widget.count()):
                    item_data = widget.itemData(i)
                    item = widget.model().item(i, 0)

                    if item_data in value:
                        item.setCheckState(Qt.Checked)
                    else:
                        item.setCheckState(Qt.Unchecked)

                widget.updateText()

            elif isinstance(widget, RiskMatrixWidget):
                widget.set_data(value)

            elif isinstance(widget, QComboBox):
                self._set_combo_value(widget, value)
                
                # Check if this key triggers others
                # Force trigger update if needed
                if key in self.dependencies:
                     self._on_trigger_changed(key, widget.currentIndex())

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
            for field in section.get("fields", []):
                if field.get("type") == "combo" and field.get("source") and not field.get("depends_on"):
                    key = field["key"]
                    widget = self.inputs.get(key)
                    endpoint = field["source"]
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

    def _start_combo_loader(self, combo, endpoint, cache_key):
        worker = ComboLoaderRunnable(self.catalogo_service.get_catalogo, endpoint, cache_key)
        self._active_runnables.append(worker)
        
        worker.signals.result.connect(partial(self._on_combo_data, combo))
        worker.signals.error.connect(self._on_load_error)
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
        combo.clear()
        if data:
            for item in data:
                combo.addItem(item["nombre"], item["id"])
                
        # Logic for selection state
        if isinstance(combo, CheckableComboBox):
             combo.updateText() # Clear
        else:
             # Standard ComboBox
             # If "New" mode, ensure no selection by default
             if not self.is_edit:
                 combo.setCurrentIndex(-1)
                 
        if self.asset_data:
            # Re-try setting value if data is already here (Edit mode)
            self._try_set_values()

    # ===============================
    # Dependency Logic
    # ===============================
    def _on_trigger_changed(self, trigger_key, index):
        # Trigger key changed. Find dependents.
        dependents = self.dependencies.get(trigger_key, [])
        trigger_widget = self.inputs[trigger_key]
        trigger_val = trigger_widget.currentData()
        
        for dep_key in dependents:
            dep_config = self.dependency_configs.get(dep_key)
            if not dep_config: continue
            
            dep_widget = self.inputs.get(dep_key)
            
            # Load dependency
            # Template: /setup/divisiones?subsecretaria_id={value}
            template = dep_config.get("dependency_endpoint_template")
            if template:
                url = template.replace("{value}", str(trigger_val) if trigger_val else "")
                
                # We need to run this async too preferably, but let's do simple worker
                self._load_dependent_combo(dep_widget, url)

    def _load_dependent_combo(self, combo, url):
        # Create a worker just for this
        # We don't block UI with overlay for this small interaction usually, 
        # or maybe we should? For now, let's just load.
        
        combo.clear()
        
        def fetch():
            return self.api.get(url)
            
        worker = ApiWorker(fetch, parent=self)
        worker.finished.connect(lambda data: self._on_dependent_data(combo, data))
        worker.start()

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
        footer = QHBoxLayout()
        if index > 0:
            prev_btn = QPushButton("Anterior")
            prev_btn.setObjectName("secondaryButton")
            prev_btn.clicked.connect(self.sidebar.prev_step)
            footer.addWidget(prev_btn)
        
        footer.addStretch()
        
        if index < total - 1:
            next_btn = QPushButton("Siguiente")
            next_btn.setObjectName("primaryButton")
            next_btn.clicked.connect(self.sidebar.next_step)
            footer.addWidget(next_btn)
        else:
            save_btn = QPushButton("Guardar")
            save_btn.setObjectName("primaryButton")
            save_btn.clicked.connect(self._submit)
            footer.addWidget(save_btn)
            
        layout.addLayout(footer)
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
        
        try:
            if self.is_edit:
                self.api.put(f"{endpoint}/{self.record_id}", payload)
                msg = f"{self.config.get('title_edit', 'Registro')} actualizado correctamente."
            else:
                self.api.post(endpoint, payload)
                msg = f"{self.config.get('title_new', 'Registro')} creado correctamente."

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

    def _build_generic_payload(self):
        payload = {}
        for key, widget in self.inputs.items():
            val = None
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                val = text if text else None
            elif isinstance(widget, QDateEdit):
                 val = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, FilePickerWidget):
                 text = widget.text().strip()
                 val = text if text else None
            elif isinstance(widget, FileTextWidget):
                 val = widget.get_data()
            elif isinstance(widget, RiskMatrixWidget):
                 val = widget.get_data()
            elif isinstance(widget, QComboBox):
                val = widget.currentData()
            
            payload[key] = val
            
        # Common fields
        payload["creado_por_usuario_id"] = "e13f156d-4bde-41fe-9dfa-9b5a5478d257"
        return payload

    def _build_eipd_payload(self):
        # 1. Base fields
        rat_id = None
        w_rat = self.inputs.get("identificacion_rat_catalogo")
        if w_rat and isinstance(w_rat, QComboBox):
            rat_id = w_rat.currentData()

        if not rat_id and self.asset_data:
             rat_id = self.asset_data.get("rat_id")

        payload = {
            "rat_id": rat_id,
            "creado_por": "e13f156d-4bde-41fe-9dfa-9b5a5478d257", # Hardcoded per original
            "ambitos": [],
            "riesgos": []
        }

        # 2. Ambitos (Flattened fields -> List)
        # We process each known code
        for ambito_name, ambito_code in AMBITO_CODES.items():
            # Construct keys expected in the form
            # e.g. licitud_group -> fields -> licitud_criterios
            # We know the keys from the JSON config. 
            # Pattern seems to be: {prefix}_criterios, {prefix}_resumen, etc.
            
            prefix = ambito_code.lower()
            if prefix == "licitud": pass # Matches
            elif prefix == "transparencia": pass # Matches
            
            # Correction: Config keys are slightly different from simple lower case code
            # Let's map code to prefix manually to be safe, or direct lookup
            
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
            
            p = prefix_map.get(ambito_code)
            if not p: continue

            # Extract specific fields for this ambito
            # We use _get_input_value helper
            
            ambito_obj = {
                "ambito_codigo": ambito_code.lower(),
                "criterios_evaluacion": self._get_input_value(f"{p}_criterios") or "",
                "resumen": self._get_input_value(f"{p}_resumen") or "",
                "probabilidad": self._get_input_value(f"{p}_probabilidad"), # combo ID?
                "impacto": self._get_input_value(f"{p}_impacto"),
                "nivel": "Bajo" # Calculated or just default? Backend requires string. 
                # Note: 'nivel' is not clearly in the form inputs for ambitos, maybe calculate from prob/imp?
                # For now let's send "Desconocido" or calc if needed. 
                # Looking at Schema: nivel: str. 
            }
            
            # Simple calc logic or just send what we have? 
            # The form has prob/impact combos.
            # Let's assume we send the ID from the combo which are strings like "limitado", "maximo".
            
            # TODO: Should we calculate 'nivel'? Schema implies it's required.
            # Let's simple-calc valid for now.
            ambito_obj["nivel"] = self._calculate_risk_level(ambito_obj["probabilidad"], ambito_obj["impacto"])
            
            payload["ambitos"].append(ambito_obj)

        # 3. Riesgos (Risk Matrix)
        w_matrix = self.inputs.get("matriz_riesgos")
        if w_matrix and isinstance(w_matrix, RiskMatrixWidget):
            matrix_data = w_matrix.get_data()
            for row in matrix_data:
                # row has: ambito (name), descripcion, ...
                name = row.get("ambito")
                code = AMBITO_CODES.get(name)
                if not code: continue 
                
                riesgo_obj = {
                    "ambito_codigo": code.lower(),
                    "descripcion": row.get("descripcion") or "",
                    "nivel_desarrollo": row.get("nivel_desarrollo") or "",
                    "riesgo_transversal": row.get("riesgo_transversal") or "",
                    "probabilidad": row.get("probabilidad") or "",
                    "impacto": row.get("impacto") or "",
                    "nivel_riesgo": row.get("nivel_riesgo") or ""
                }
                payload["riesgos"].append(riesgo_obj)

        return payload

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
        # Placeholder logic
        if not prob or not imp: return "Bajo"
        return "Medio" # TODO: Real calculation logic if needed by business rule

    
    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)
