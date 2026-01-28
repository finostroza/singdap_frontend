import json
import os
from functools import partial

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, 
    QComboBox, QFormLayout, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QThreadPool

from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.components.wizard_sidebar import WizardSidebar
from src.components.loading_overlay import LoadingOverlay
from src.services.catalogo_service import CatalogoService
from src.workers.combo_loader import ComboLoaderRunnable
from src.workers.api_worker import ApiWorker
from src.services.logger_service import LoggerService
from src.components.custom_inputs import CheckableComboBox

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
        self.setModal(True)
        
        width = self.config.get("width", 1100)
        height = self.config.get("height", 800)
        self.resize(width, height)
        # Main Dialog Background - Light Gray
        self.setStyleSheet("#genericFormDialog { background-color: #f1f5f9; }")
        
        # Inputs Registry: key -> widget
        self.inputs = {}
        # Dependency Map: trigger_key -> [dependent_keys]
        self.dependencies = {}
        # Dependency Config: key -> config
        self.dependency_configs = {}

        self._init_ui()
        
        # Async Load
        self.loading_overlay = LoadingOverlay(self)
        QTimer.singleShot(0, self._init_async_load)
        LoggerService().log_event(f"Abriendo formulario genérico: {title}")

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
        # Prepend Context if available (e.g. SINGDAP / SIGDAP) - Hardcoded for visual match or generic
        # Utilizing config title as main header
        
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
        # Main layout for the form section - Vertical
        layout = QVBoxLayout(w)
        layout.setSpacing(24) # Spacing between field blocks
        layout.setContentsMargins(16, 16, 16, 16)
        
        for field in section_config.get("fields", []):
            # Block for each field
            field_block = QWidget()
            block_layout = QVBoxLayout(field_block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(6) # Spacing between Label-Desc-Input
            
            # 1. Label Row (Title + "Obligatorio" badge)
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
            
            # 2. Field Description (Red box equivalent) - NEW
            # Fallback to test text if not in config, as requested
            desc_text = field.get("description", "Descripción del Campo - Prueba")
            if desc_text:
                desc_lbl = QLabel(desc_text)
                desc_lbl.setStyleSheet("font-size: 12px; color: #64748b; margin-bottom: 2px;")
                desc_lbl.setWordWrap(True)
                block_layout.addWidget(desc_lbl)
            
            # 3. Widget (Purple box equivalent)
            widget = self._create_input_widget(field)
            
            # Register input
            key = field["key"]
            self.inputs[key] = widget
            
            # Store dependency info if exists
            if "triggers_reload" in field:
                 self.dependencies[key] = field["triggers_reload"]
                 # Connect signal
                 if isinstance(widget, QComboBox):
                     widget.currentIndexChanged.connect(partial(self._on_trigger_changed, key))
                     
            if "depends_on" in field:
                 self.dependency_configs[key] = field
            
            # Connect Validation Signal for Real-time counter
            if isinstance(widget, QLineEdit):
                # Use default arg to avoid closure issue if needed, but self is fine
                widget.textChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, CheckableComboBox):
                widget.selectionChanged.connect(self._validate_steps_progress)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._validate_steps_progress)

            block_layout.addWidget(widget)
            
            layout.addWidget(field_block)
            
        layout.addStretch() # Push everything up
        return w



    def _create_input_widget(self, field):
        ftype = field.get("type", "text")
        
        if ftype == "text":
            inp = QLineEdit()
            return inp
            
        elif ftype == "textarea":
            inp = QLineEdit()
            height = field.get("height", 120)
            inp.setFixedHeight(height)
            inp.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            inp.setObjectName("formLargeInput")
            return inp
            
        elif ftype == "combo" or ftype == "combo_static":
            is_multiple = field.get("multiple", False)
            
            if is_multiple:
                inp = CheckableComboBox()
            else:
                inp = QComboBox()
                inp.setPlaceholderText("Seleccione...")
                
            # If static options
            if ftype == "combo_static" and "options" in field:
                for opt in field["options"]:
                    inp.addItem(opt["nombre"], opt["id"])
                    
                # Fix for New Mode: Start empty
                if not self.is_edit and not is_multiple:
                     inp.setCurrentIndex(-1)

            return inp
            
        return QLineEdit() # Fallback

    # ... in _on_combo_data ...
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
            
    # ... in _try_set_values ...
    def _try_set_values(self):
        if not self.asset_data: return
        
        for key, widget in self.inputs.items():
            value = self.asset_data.get(key)
            if value is None: continue
            
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, CheckableComboBox):
                 # Expecting list of IDs or single ID
                 if isinstance(value, list):
                     widget.setCurrentData(value)
                 else:
                     widget.setCurrentData([value])
            elif isinstance(widget, QComboBox):
                self._set_combo_value(widget, value)
                
                # Check triggers
                if key in self.dependencies:
                     self._on_trigger_changed(key, widget.currentIndex())

    # ... in _submit ...
    def _submit(self):
        payload = {}
        for key, widget in self.inputs.items():
            val = None
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                val = text if text else None
            elif isinstance(widget, CheckableComboBox):
                # Returns list of IDs
                val = widget.currentData()
                # Use empty list or None if empty? usually API expects list
                if not val: val = []
            elif isinstance(widget, QComboBox):
                val = widget.currentData()
            
            payload[key] = val
        
        # ... rest of submit ...

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
                
        if self.asset_data:
            # Re-try setting value if data is already here
            self._try_set_values()



    def _validate_steps_progress(self):
        # Iterate all sections
        sections = self.config.get("sections", [])
        
        global_filled = 0
        global_total = 0
        
        for i, section in enumerate(sections):
            total_req = 0
            filled_req = 0
            
            for field in section.get("fields", []):
                if field.get("required", False):
                    total_req += 1
                    key = field["key"]
                    widget = self.inputs.get(key)
                    if self._is_field_filled(widget, field):
                        filled_req += 1
            
            # Update Sidebar Step
            step_widget = self.sidebar.step_widgets[i]
            if hasattr(step_widget, "update_required_count"):
                step_widget.update_required_count(filled_req, total_req)
                
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

        # Update Label
        if hasattr(self, "progress_label"):
            self.progress_label.setText(f"Progreso: {percentage}% ({global_filled}/{global_total} campos requeridos)")

    def _is_field_filled(self, widget, field):
        if not widget: return False
        
        # Robust check for CheckableComboBox (handling potential import/reload mismatches)
        is_checkable = isinstance(widget, CheckableComboBox) or widget.__class__.__name__ == "CheckableComboBox"
        
        if isinstance(widget, QLineEdit):
             # Ensure we don't treat CheckableComboBox (which inherits QComboBox -> QWidget) as QLineEdit 
             # (it keeps an internal lineedit but widget itself is ComboBox)
             return bool(widget.text().strip())
             
        elif is_checkable:
            # Check text presence as visual confirmation of selection
            return bool(widget.lineEdit().text().strip())
            
        elif isinstance(widget, QComboBox):
            # Standard ComboBox
            if widget.currentIndex() == -1: return False
            return True
            
        return False

    def _on_record_data(self, data):
        self.asset_data = data
        self._try_set_values()
        # Trigger validation after loading data
        self._validate_steps_progress() 
        self._check_finished()

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
                 
    # ===============================
    # Submit
    # ===============================
    def _submit(self):
        payload = {}
        for key, widget in self.inputs.items():
            val = None
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                val = text if text else None
            elif isinstance(widget, QComboBox):
                val = widget.currentData()
            
            payload[key] = val
        
        # Inject user id (hardcoded for now as in original)
        payload["creado_por_usuario_id"] = "e13f156d-4bde-41fe-9dfa-9b5a5478d257"
        
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
    
    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)
