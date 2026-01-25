from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt

from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.workers.api_worker import ApiWorker
from src.components.loading_overlay import LoadingOverlay
from PySide6.QtCore import QTimer


from src.workers.combo_loader import ComboLoaderRunnable
from src.services.catalogo_service import CatalogoService
from src.services.logger_service import LoggerService
from PySide6.QtCore import QThreadPool, QTimer
from functools import partial


class ActivoDialog(QDialog):
    def __init__(self, parent=None, activo_id=None):
        super().__init__(parent)

        self.api = ApiClient()
        self.catalogo_service = CatalogoService()
        self.thread_pool = QThreadPool.globalInstance()
        self.pending_loads = 0
        self.asset_data = None # Store asset data for edit mode sync
        self._active_runnables = [] # Keep refs to prevent GC crash
        
        self.activo_id = activo_id
        self.is_edit = activo_id is not None

        self.setObjectName("activoDialog")
        self.setWindowTitle("Editar Activo" if self.is_edit else "Nuevo Activo")
        self.setModal(True)
        self.resize(1100, 750)

        # ===============================
        # Layout principal (Horizontal: Sidebar | Content)
        # ===============================
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Prepare Steps Data
        self.steps_config = [
            {"title": "Identificación general", "desc": "Antecedentes principales para individualizar el activo.", "func": self._tab_identificacion},
            {"title": "Contexto institucional", "desc": "Unidad y marco que da origen al activo.", "func": self._tab_contexto},
            {"title": "Responsables", "desc": "Personas y roles encargados del activo.", "func": self._tab_responsables},
            {"title": "Seguridad y privacidad", "desc": "Detalle de clasificación y medidas de seguridad.", "func": self._tab_clasificacion},
        ]
        
        # 2. Sidebar
        from src.components.wizard_sidebar import WizardSidebar
        self.sidebar = WizardSidebar(self.steps_config)
        self.sidebar.step_changed.connect(self._on_step_changed)
        
        main_layout.addWidget(self.sidebar)

        # 3. Content Area (Stack)
        from PySide6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()
        
        # Build pages
        for i, step in enumerate(self.steps_config):
            # Create content widget from existing function
            content_widget = step["func"]()
            
            # Wrap in wizard page structure
            page = self._wrap_step_content(
                content_widget, 
                step["title"], 
                step["desc"], 
                i, 
                len(self.steps_config)
            )
            self.stack.addWidget(page)

        main_layout.addWidget(self.stack)

        # ===============================
        # Overlay & Initial Load
        # ===============================
        self.loading_overlay = LoadingOverlay(self)

        # Trigger async load
        QTimer.singleShot(0, self._init_async_load)
        LoggerService().log_event(f"Abriendo formulario activo. Modo: {'Editar' if self.is_edit else 'Nuevo'}")
        
    def _on_step_changed(self, index):
        self.stack.setCurrentIndex(index)

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
        
        # Content (Scrollable if needed, but inner forms usually fit or have their own logic)
        # Using scroll wrapper here as well
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1) # Stretch
        
        # Footer (Nav Buttons)
        footer = QHBoxLayout()
        
        # Prev Button
        if index > 0:
            prev_btn = QPushButton("Anterior")
            prev_btn.setObjectName("secondaryButton")
            prev_btn.clicked.connect(self.sidebar.prev_step)
            footer.addWidget(prev_btn)
        
        footer.addStretch()
        
        # Next / Save Button
        if index < total - 1:
            next_btn = QPushButton("Siguiente")
            next_btn.setObjectName("primaryButton")
            next_btn.clicked.connect(self.sidebar.next_step)
            footer.addWidget(next_btn)
        else:
            # Last step -> Save
            save_btn = QPushButton("Guardar")
            save_btn.setObjectName("primaryButton")
            save_btn.clicked.connect(self._submit)
            footer.addWidget(save_btn)
            
        layout.addLayout(footer)
        return container

    def _init_async_load(self):
        self.loading_overlay.show_loading()
        
        # Parallel Load Configuration
        combos_to_load = [
            (self.tipo_activo_combo, "/catalogos/tipo-activo", "catalogo_tipos"),
            (self.estado_activo_combo, "/catalogos/estado-activo", "catalogo_estados"),
            (self.categoria_combo, "/catalogos/categoria-activo", "catalogo_categorias"),
            (self.importancia_combo, "/catalogos/importancia", "catalogo_importancia"),
            (self.subsecretaria_combo, "/setup/subsecretarias", "catalogo_subsecretarias"),
            (self.marco_combo, "/catalogos/marco-habilitante", "catalogo_marco"),
            (self.criticidad_combo, "/catalogos/criticidad", "catalogo_criticidad"),
            (self.confidencialidad_combo, "/catalogos/nivel-confidencialidad", "catalogo_confidencialidad"),
            (self.controles_combo, "/catalogos/controles-acceso", "catalogo_controles"),
            (self.medidas_combo, "/catalogos/medidas-seguridad", "catalogo_medidas_seguridad"),
        ]

        self.pending_loads = len(combos_to_load)
        if self.is_edit:
            self.pending_loads += 1 # Asset load

        # Launch Combo Loaders
        for combo, endpoint, cache_key in combos_to_load:
            self._start_combo_loader(combo, endpoint, cache_key)

        # Launch Asset Loader (if edit)
        if self.is_edit:
            self._start_asset_loader()

    def _start_combo_loader(self, combo, endpoint, cache_key):
        worker = ComboLoaderRunnable(self.catalogo_service.get_catalogo, endpoint, cache_key)
        
        # Prevent GC crash by storing reference
        self._active_runnables.append(worker)

        # Use partial to pass arguments safely and correctly
        worker.signals.result.connect(partial(self._on_combo_data, combo))
        worker.signals.error.connect(self._on_load_error_combo)
        worker.signals.finished.connect(self._check_finished)
        
        self.thread_pool.start(worker)

    def _on_load_error_combo(self, error):
        print(f"Combo load error: {error}")
        # Still need to decrement pending
        # self._check_finished() is connected to finished, which always runs, so no need to call it here manually
        pass

    def _start_asset_loader(self):
        def fetch_asset():
            asset = self.api.get(f"/activos/{self.activo_id}")
            # If subsecretaria exists, we might need to load divisiones too, OR load them when sub change triggers.
            # However, to be instant, better to fetch if needed.
            # But the existing logic for subsecretaria change handles fetch.
            # Let's rely on standard flow or optimizing later if needed. 
            # Actually, to prevent empty division combo, we should fetch divisions if asset has sub_id
            if asset.get("subsecretaria_id"):
                 asset["_divisiones_preloaded"] = self.api.get(f"/setup/divisiones?subsecretaria_id={asset['subsecretaria_id']}")
            return asset

        worker = ApiWorker(fetch_asset, parent=self)
        worker.finished.connect(self._on_asset_data)
        worker.error.connect(self._on_load_error)
        worker.start()

    def _on_combo_data(self, combo, data):
        combo.clear()
        if data:
            for item in data:
                combo.addItem(item["nombre"], item["id"])
        
        # If we have asset data waiting, try to set value now
        if self.asset_data:
            self._try_set_combo_from_asset(combo)

    def _on_asset_data(self, data):
        self.asset_data = data
        
        # Text fields
        self.nombre_input.setText(data["nombre_activo"])
        self.descripcion_input.setText(data.get("descripcion") or "")
        self.responsable_input.setText(data.get("responsable") or "")
        self.roles_input.setText(data.get("rol") or "")
        self.url_input.setText(data.get("url_direccion") or "")
        self.procesos_input.setText(data.get("procesos_vinculados") or "")
        self.infra_input.setText(data.get("infraestructura_ti") or "")
        self.convenio_input.setText(data.get("convenio_vinculado") or "")
        self.tipo_sensible_input.setText(data.get("tipo_sensible") or "")
        self.datos_sensibles_combo.setCurrentIndex(1 if data.get("datos_sensibles") else 0)

        # Preloaded divisions special handling
        if "_divisiones_preloaded" in data:
            self.division_combo.clear()
            for div in data["_divisiones_preloaded"]:
                 self.division_combo.addItem(div["nombre"], div["id"])

        # Try to set all combos (some might be ready, some not)
        self._try_set_all_combos()
        
        # Manually trigger finish check for asset worker
        self._check_finished()

    def _try_set_all_combos(self):
        if not self.asset_data: return
        
        data = self.asset_data
        self._set_combo_by_data(self.tipo_activo_combo, data.get("tipo_activo_id"))
        self._set_combo_by_data(self.estado_activo_combo, data.get("estado_activo_id"))
        self._set_combo_by_data(self.categoria_combo, data.get("categoria_id"))
        self._set_combo_by_data(self.importancia_combo, data.get("importancia_id"))
        self._set_combo_by_data(self.subsecretaria_combo, data.get("subsecretaria_id"))
        self._set_combo_by_data(self.division_combo, data.get("division_id"))
        self._set_combo_by_data(self.marco_combo, data.get("marco_habilitante_id"))
        self._set_combo_by_data(self.criticidad_combo, data.get("criticidad_id"))
        self._set_combo_by_data(self.confidencialidad_combo, data.get("nivel_confidencialidad_id"))
        self._set_combo_by_data(self.controles_combo, data.get("controles_acceso_id"))
        self._set_combo_by_data(self.medidas_combo, data.get("medidas_seguridad_id"))

    def _try_set_combo_from_asset(self, combo):
        # We need to know which key maps to which combo. 
        # A simple map dict approach or just re-run _try_set_all_combos (fast enough)
        self._try_set_all_combos()

    def _check_finished(self):
        self.pending_loads -= 1
        if self.pending_loads <= 0:
            self.loading_overlay.hide_loading()

    def _on_load_error(self, error):
        print(f"Error loading: {error}")
        # Even on error we should decrement pending to avoid stuck spinner
        self._check_finished()

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    # ======================================================
    # Helpers
    # ======================================================

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def _form(self):
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(16)
        return form

    def _large_input(self, height=120):
        inp = QLineEdit()
        inp.setFixedHeight(height)
        inp.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        inp.setObjectName("formLargeInput")
        return inp

    def _set_combo_by_data(self, combo: QComboBox, value):
        if value is None:
            return
        
        # Try finding exact match first
        index = combo.findData(value)
        if index != -1:
            combo.setCurrentIndex(index)
            return

        # Fallback: Compare as strings (handle int vs str mismatch)
        value_str = str(value)
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data is not None and str(data) == value_str:
                combo.setCurrentIndex(i)
                return

    # ======================================================
    # Tabs
    # ======================================================

    def _tab_identificacion(self):
        w = QWidget()
        f = self._form()

        self.nombre_input = QLineEdit()
        self.descripcion_input = self._large_input()

        self.tipo_activo_combo = QComboBox()
        self.estado_activo_combo = QComboBox()
        self.categoria_combo = QComboBox()
        self.importancia_combo = QComboBox()

        self.url_input = QLineEdit()
        self.procesos_input = QLineEdit()
        self.infra_input = QLineEdit()
        self.convenio_input = QLineEdit()

        self.deprecado_combo = QComboBox()
        self.deprecado_combo.addItem("No", False)
        self.deprecado_combo.addItem("Sí", True)

        f.addRow("Nombre", self.nombre_input)
        f.addRow("Descripción", self.descripcion_input)
        f.addRow("Tipo de activo", self.tipo_activo_combo)
        f.addRow("Estado", self.estado_activo_combo)
        f.addRow("URL / Dirección", self.url_input)
        f.addRow("Procesos vinculados", self.procesos_input)
        f.addRow("Infraestructura TI", self.infra_input)
        f.addRow("Convenio vinculado", self.convenio_input)
        f.addRow("Categoría", self.categoria_combo)
        f.addRow("Importancia", self.importancia_combo)
        f.addRow("Deprecado", self.deprecado_combo)

        w.setLayout(f)
        return w

    def _tab_contexto(self):
        w = QWidget()
        f = self._form()

        self.subsecretaria_combo = QComboBox()
        self.division_combo = QComboBox()
        self.marco_combo = QComboBox()

        f.addRow("Subsecretaría", self.subsecretaria_combo)
        f.addRow("División / Depto", self.division_combo)
        f.addRow("Marco habilitante", self.marco_combo)

        w.setLayout(f)
        return w

    def _tab_responsables(self):
        w = QWidget()
        f = self._form()

        self.responsable_input = QLineEdit()
        self.roles_input = QLineEdit()

        f.addRow("Responsable tratamiento", self.responsable_input)
        f.addRow("Rol", self.roles_input)

        w.setLayout(f)
        return w

    def _tab_clasificacion(self):
        w = QWidget()
        f = self._form()

        self.datos_sensibles_combo = QComboBox()
        self.datos_sensibles_combo.addItem("No", False)
        self.datos_sensibles_combo.addItem("Sí", True)

        self.tipo_sensible_input = QLineEdit()

        self.criticidad_combo = QComboBox()
        self.confidencialidad_combo = QComboBox()
        self.controles_combo = QComboBox()
        self.medidas_combo = QComboBox()

        f.addRow("¿Datos sensibles?", self.datos_sensibles_combo)
        f.addRow("Tipo sensible", self.tipo_sensible_input)
        f.addRow("Criticidad", self.criticidad_combo)
        f.addRow("Confidencialidad", self.confidencialidad_combo)
        f.addRow("Controles de acceso", self.controles_combo)
        f.addRow("Medidas de seguridad", self.medidas_combo)

        w.setLayout(f)
        return w

    # ======================================================
    # Load data
    # ======================================================

    def _load_combo(self, combo, endpoint):
        combo.clear()
        for item in self.api.get(endpoint):
            combo.addItem(item["nombre"], item["id"])

    # _load_combos (removed, replaced by async)
    # _load_activo (removed, replaced by async)

    def _on_subsecretaria_changed(self):
        subsecretaria_id = self.subsecretaria_combo.currentData()
        self.division_combo.clear()

        if not subsecretaria_id:
            return

        divisions = self.api.get(
                    f"/setup/divisiones?subsecretaria_id={subsecretaria_id}".replace("/?", "?")
                    )

        for div in divisions:
            self.division_combo.addItem(div["nombre"], div["id"])



    # ======================================================
    # Submit
    # ======================================================

    def _submit(self):
        payload = {
            "nombre_activo": self.nombre_input.text().strip(),
            "descripcion": self.descripcion_input.text().strip() or None,
            "responsable": self.responsable_input.text().strip(),
            "rol": self.roles_input.text().strip(),
            "tipo_activo_id": self.tipo_activo_combo.currentData(),
            "estado_activo_id": self.estado_activo_combo.currentData(),
            "importancia_id": self.importancia_combo.currentData(),
            "nivel_confidencialidad_id": self.confidencialidad_combo.currentData(),
            "categoria_id": self.categoria_combo.currentData(),
            "datos_sensibles": self.datos_sensibles_combo.currentData(),
            "tipo_sensible": self.tipo_sensible_input.text().strip() or None,
            "url_direccion": self.url_input.text().strip() or None,
            "procesos_vinculados": self.procesos_input.text().strip() or None,
            "infraestructura_ti": self.infra_input.text().strip() or None,
            "convenio_vinculado": self.convenio_input.text().strip() or None,
            "subsecretaria_id": self.subsecretaria_combo.currentData(),
            "division_id": self.division_combo.currentData(),
            "marco_habilitante_id": self.marco_combo.currentData(),
            "medidas_seguridad_id": self.medidas_combo.currentData(),
            "controles_acceso_id": self.controles_combo.currentData(),
            "criticidad_id": self.criticidad_combo.currentData(),
            "creado_por_usuario_id": self._get_user_id(),
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            if self.is_edit:
                self.api.put(f"/activos/{self.activo_id}", payload)
                msg = "Activo actualizado correctamente."
            else:
                self.api.post("/activos", payload)
                msg = "Activo creado correctamente."

            LoggerService().log_event(f"Activo {'actualizado' if self.is_edit else 'creado'} correctamente.")

            AlertDialog(
                title="Éxito",
                message=msg,
                icon_path="src/resources/icons/alert_success.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()

            self.accept()

        except Exception as e:
            LoggerService().log_error("Error al guardar activo", e)
            AlertDialog(
                title="Error",
                message=str(e),
                icon_path="src/resources/icons/alert_error.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()

    def _get_user_id(self):
        return "e13f156d-4bde-41fe-9dfa-9b5a5478d257"
