import json
import os
from functools import partial

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QStackedWidget,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, 
    QComboBox, QFormLayout
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
        height = self.config.get("height", 750)
        self.resize(width, height)
        self.setStyleSheet("#genericFormDialog { background-color: white; }")
        
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
        # Layout principal (Horizontal: Sidebar | Content)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Prepare Sections Data for Sidebar
        # We need simply [{title, ...}]
        # But we also need to build the widgets.
        
        sections_config = self.config.get("sections", [])
        
        # 2. Sidebar
        self.sidebar = WizardSidebar(sections_config)
        self.sidebar.step_changed.connect(self._on_step_changed)
        main_layout.addWidget(self.sidebar)
        
        # 3. Content Area (Stack)
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
            
        main_layout.addWidget(self.stack)

    def _build_section_form(self, section_config):
        w = QWidget()
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(16)
        
        for field in section_config.get("fields", []):
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

            form.addRow(field["label"], widget)
            
        w.setLayout(form)
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
            inp = QComboBox()
            # If static options
            if ftype == "combo_static" and "options" in field:
                for opt in field["options"]:
                    inp.addItem(opt["nombre"], opt["id"])
            return inp
            
        return QLineEdit() # Fallback

    def _wrap_step_content(self, content_widget, title_text, desc_text, index, total):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QVBoxLayout()
        t = QLabel(f"{index + 1}. {title_text}")
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

    def _on_record_data(self, data):
        self.asset_data = data
        self._try_set_values()
        
        # Manually verify if we need to trigger any dependency chain
        # For now _try_set_values just sets data. 
        # But if we set a trigger field, it should fire indexChanged? 
        # Programmatic setText/setCurrentIndex DOES NOT fire signals usually in Qt unless explicit.
        # But setCurrentIndex DOES fire if it changes.
        
        # We need to manually handle dependency loading for existing values (e.g. Subs -> Div)
        # This is tricky because we need the Div combo to load BEFORE we can set its value.
        # So we iterate dependencies.
        
        self._check_finished() # Decrement pending

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

    def _check_finished(self):
        self.pending_loads -= 1
        if self.pending_loads <= 0:
            self.loading_overlay.hide_loading()

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
