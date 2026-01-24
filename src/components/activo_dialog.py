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
)
from PySide6.QtCore import Qt

from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.workers.api_worker import ApiWorker
from src.components.loading_overlay import LoadingOverlay
from PySide6.QtCore import QTimer


class ActivoDialog(QDialog):
    def __init__(self, parent=None, activo_id=None):
        super().__init__(parent)

        self.api = ApiClient()
        self.activo_id = activo_id
        self.is_edit = activo_id is not None

        self.setObjectName("activoDialog")
        self.setWindowTitle("Editar Activo" if self.is_edit else "Nuevo Activo")
        self.setModal(True)
        self.resize(920, 620)

        # ===============================
        # Layout principal
        # ===============================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===============================
        # HEADER
        # ===============================
        header = QWidget()
        header.setObjectName("dialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Editar Activo" if self.is_edit else "Nuevo Activo")
        title.setObjectName("dialogTitle")
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # ===============================
        # Contenido
        # ===============================
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 16)
        content_layout.setSpacing(16)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("dialogTabs")

        self.tabs.addTab(self._wrap_scroll(self._tab_identificacion()), "Identificación")
        self.tabs.addTab(self._wrap_scroll(self._tab_contexto()), "Contexto institucional")
        self.tabs.addTab(self._wrap_scroll(self._tab_responsables()), "Responsables")
        self.tabs.addTab(self._wrap_scroll(self._tab_clasificacion()), "Seguridad y privacidad")

        content_layout.addWidget(self.tabs)

        # ===============================
        # Footer
        # ===============================
        footer = QHBoxLayout()
        footer.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._submit)

        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)

        content_layout.addLayout(footer)
        main_layout.addWidget(content)

        # ===============================
        # Load combos + signals
        # ===============================
        # ===============================
        # Overlay
        # ===============================
        self.loading_overlay = LoadingOverlay(self)

        # Trigger async load
        QTimer.singleShot(0, self._init_async_load)

    def _init_async_load(self):
        self.loading_overlay.show_loading()

        def fetch_data():
            # Determine calls
            endpoints = {
                "tipo_activo": "/catalogos/tipo-activo",
                "estado_activo": "/catalogos/estado-activo",
                "categoria_activo": "/catalogos/categoria-activo",
                "importancia": "/catalogos/importancia",
                "subsecretarias": "/setup/subsecretarias",
                "marco_habilitante": "/catalogos/marco-habilitante",
                "criticidad": "/catalogos/criticidad",
                "nivel_confidencialidad": "/catalogos/nivel-confidencialidad",
                "controles_acceso": "/catalogos/controles-acceso",
                "medidas_seguridad": "/catalogos/medidas-seguridad"
            }
            results = {}
            # 1. Load catalogs
            for key, url in endpoints.items():
                results[key] = self.api.get(url)

            # 2. If Edit, load asset + specific divisions
            if self.is_edit:
                asset = self.api.get(f"/activos/{self.activo_id}")
                results["asset"] = asset
                
                # Load divisions for the asset's subsecretaria
                sub_id = asset.get("subsecretaria_id")
                if sub_id:
                    results["divisiones"] = self.api.get(f"/setup/divisiones?subsecretaria_id={sub_id}")
            
            return results

        self.worker = ApiWorker(fetch_data, parent=self)
        self.worker.finished.connect(self._on_data_ready)
        self.worker.error.connect(self._on_load_error)
        self.worker.start()

    def _on_load_error(self, error):
        self.loading_overlay.hide_loading()
        print(f"Error loading dialog data: {error}")
        self.reject()

    def _on_data_ready(self, data):
        # Populate catalogs
        self._fill_combo(self.tipo_activo_combo, data["tipo_activo"])
        self._fill_combo(self.estado_activo_combo, data["estado_activo"])
        self._fill_combo(self.categoria_combo, data["categoria_activo"])
        self._fill_combo(self.importancia_combo, data["importancia"])
        self._fill_combo(self.subsecretaria_combo, data["subsecretarias"])
        self._fill_combo(self.marco_combo, data["marco_habilitante"])
        self._fill_combo(self.criticidad_combo, data["criticidad"])
        self._fill_combo(self.confidencialidad_combo, data["nivel_confidencialidad"])
        self._fill_combo(self.controles_combo, data["controles_acceso"])
        self._fill_combo(self.medidas_combo, data["medidas_seguridad"])

        # Populate asset if edit
        if self.is_edit and "asset" in data:
            self._populate_asset_data(data["asset"], data.get("divisiones", []))

        self.loading_overlay.hide_loading()

    def _fill_combo(self, combo, items):
        combo.clear()
        for item in items:
            combo.addItem(item["nombre"], item["id"])

    def _populate_asset_data(self, data, divisions):
        self.nombre_input.setText(data["nombre_activo"])
        self.descripcion_input.setText(data.get("descripcion") or "")
        self.responsable_input.setText(data.get("responsable") or "")
        self.roles_input.setText(data.get("rol") or "")
        self.url_input.setText(data.get("url_direccion") or "")
        self.procesos_input.setText(data.get("procesos_vinculados") or "")
        self.infra_input.setText(data.get("infraestructura_ti") or "")
        self.convenio_input.setText(data.get("convenio_vinculado") or "")

        self._set_combo_by_data(self.tipo_activo_combo, data.get("tipo_activo_id"))
        self._set_combo_by_data(self.estado_activo_combo, data.get("estado_activo_id"))
        self._set_combo_by_data(self.categoria_combo, data.get("categoria_id"))
        self._set_combo_by_data(self.importancia_combo, data.get("importancia_id"))

        # Subsecretaria
        self._set_combo_by_data(self.subsecretaria_combo, data.get("subsecretaria_id"))
        
        # Divisions (pre-fetched)
        self.division_combo.clear()
        for div in divisions:
            self.division_combo.addItem(div["nombre"], div["id"])
        self._set_combo_by_data(self.division_combo, data.get("division_id"))

        self._set_combo_by_data(self.marco_combo, data.get("marco_habilitante_id"))
        self._set_combo_by_data(self.criticidad_combo, data.get("criticidad_id"))
        self._set_combo_by_data(self.confidencialidad_combo, data.get("nivel_confidencialidad_id"))
        self._set_combo_by_data(self.controles_combo, data.get("controles_acceso_id"))
        self._set_combo_by_data(self.medidas_combo, data.get("medidas_seguridad_id"))

        self.datos_sensibles_combo.setCurrentIndex(1 if data.get("datos_sensibles") else 0)
        self.tipo_sensible_input.setText(data.get("tipo_sensible") or "")

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
        for i in range(combo.count()):
            if combo.itemData(i) == value:
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

            AlertDialog(
                title="Éxito",
                message=msg,
                icon_path="src/resources/icons/alert_success.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()

            self.accept()

        except Exception as e:
            AlertDialog(
                title="Error",
                message=str(e),
                icon_path="src/resources/icons/alert_error.svg",
                confirm_text="Aceptar",
                parent=self
            ).exec()

    def _get_user_id(self):
        return "e13f156d-4bde-41fe-9dfa-9b5a5478d257"
