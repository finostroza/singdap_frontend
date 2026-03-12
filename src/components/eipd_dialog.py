import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QLabel,
    QTableWidgetItem
)
from PySide6.QtCore import Qt, QTimer

from src.components.generic_form_dialog import GenericFormDialog
from src.components.custom_inputs import CheckableComboBox
from src.workers.api_worker import ApiWorker


class EipdDialog(GenericFormDialog):

    def __init__(self, parent=None, eipd_id=None, **kwargs):
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "src" / "config" / "formularios" / "eipd.json"

        target_id = eipd_id or kwargs.get("id") or kwargs.get("record_id")

        # ⚠️ Inicializar ANTES de super().__init__ porque _rebuild_footer
        # se llama dentro de _init_ui() que se ejecuta en el constructor padre
        from src.core.api_client import ApiClient
        client = ApiClient()
        self.eipd_estado = "BORRADOR"
        self._is_admin_user = client.is_admin

        super().__init__(str(config_path), parent=parent, record_id=target_id)
        self._catalog_label_cache = {}

        # Nivel en tiempo real (Section 1 labels)
        QTimer.singleShot(100, self._bind_niveles_en_tiempo_real)

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------
    def _on_record_data(self, data):
        self.eipd_estado = data.get("estado_eipd", "BORRADOR")
        super()._on_record_data(data)

        # Lock form if not editable
        if self.eipd_estado in ["ENVIADO", "APROBADO", "RECHAZADO"]:
            self._lock_form()
        
        # Trigger footer rebuild on the last page
        last_idx = self.stack.count() - 1
        self._rebuild_footer(last_idx, is_last=True)

    def _lock_form(self):
        for w in self.inputs.values():
            if hasattr(w, "set_read_only"):
                try:
                    w.set_read_only(True)
                except Exception:
                    pass
            w.setEnabled(False)

    # ------------------------------------------------------------------
    # Footer with state-based buttons
    # ------------------------------------------------------------------
    def _rebuild_footer(self, index, is_last):
        # If it's not the last page, use default behavior
        if not is_last:
            super()._rebuild_footer(index, is_last)
            return

        layout = self.footer_layouts.get(index)
        if not layout:
            return

        self._clear_layout(layout)

        from PySide6.QtWidgets import QPushButton

        # Anterior
        if index > 0:
            btn_prev = QPushButton("Anterior")
            btn_prev.setObjectName("secondaryButton")
            btn_prev.clicked.connect(self.sidebar.prev_step)
            layout.addWidget(btn_prev)

        layout.addStretch()

        estado = self.eipd_estado
        is_admin = self._is_admin_user

        if estado in ["BORRADOR", "EN_PROCESO", "RECHAZADO"]:
            # Guardar + Enviar
            btn_guardar = QPushButton("Guardar")
            btn_guardar.setObjectName("primaryButton")
            btn_guardar.clicked.connect(self._submit)
            layout.addWidget(btn_guardar)

            btn_enviar = QPushButton("Enviar")
            btn_enviar.setObjectName("dangerButton")

            is_ready = False
            if self.record_id:
                try:
                    total = self.progress_bar.maximum()
                    filled = self.progress_bar.value()
                    if total > 0 and filled >= total:
                        is_ready = True
                except (RuntimeError, AttributeError):
                    pass

            btn_enviar.setEnabled(is_ready)
            if not is_ready:
                btn_enviar.setToolTip(
                    "Debe guardar y completar el 100% de los campos para enviar."
                )

            btn_enviar.clicked.connect(self._submit_enviar)
            layout.addWidget(btn_enviar)

        elif estado == "ENVIADO" and is_admin:
            # Aprobar + Rechazar (admin only)
            btn_aprobar = QPushButton("Aprobar")
            btn_aprobar.setObjectName("successButton")
            btn_aprobar.clicked.connect(self._aprobar_eipd)
            layout.addWidget(btn_aprobar)

            btn_rechazar = QPushButton("Rechazar")
            btn_rechazar.setObjectName("dangerButton")
            btn_rechazar.clicked.connect(self._mostrar_rechazo)
            layout.addWidget(btn_rechazar)

        # else: APROBADO or ENVIADO (non-admin) → no buttons, just "Anterior"

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def _submit_enviar(self):
        from PySide6.QtWidgets import QMessageBox, QApplication
        from PySide6.QtCore import Qt

        try:
            res = QMessageBox.question(
                self,
                "Confirmar Envío",
                "¿Está seguro que desea enviar el EIPD? Una vez enviado no podrá ser editado.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.api.put(
                f"/eipd/{self.record_id}/estado", {"estado": "ENVIADO"}
            )
            QApplication.restoreOverrideCursor()

            QMessageBox.information(
                self, "EIPD Enviado",
                "El EIPD ha sido enviado correctamente."
            )
            self.accept()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "Error", f"No se pudo enviar el EIPD:\n{str(e)}"
            )

    def _aprobar_eipd(self):
        from PySide6.QtWidgets import QMessageBox
        self.api.put(
            f"/eipd/{self.record_id}/estado", {"estado": "APROBADO"}
        )
        QMessageBox.information(
            self, "EIPD Aprobado", "El EIPD ha sido aprobado."
        )
        self.accept()

    def _mostrar_rechazo(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        comentario, ok = QInputDialog.getMultiLineText(
            self,
            "Rechazar EIPD",
            "Ingrese el motivo del rechazo:",
        )
        if ok and comentario.strip():
            self.api.put(
                f"/eipd/{self.record_id}/estado",
                {"estado": "RECHAZADO", "comentario": comentario},
            )
            QMessageBox.information(
                self, "EIPD Rechazado", "El EIPD ha sido rechazado."
            )
            self.accept()

    # ------------------------------------------------------------------
    # RAT integration
    # ------------------------------------------------------------------
    def _on_trigger_changed(self, trigger_key, index):
        super()._on_trigger_changed(trigger_key, index)

        if trigger_key == "identificacion_rat_catalogo":
            rat_id = self.inputs[trigger_key].currentData()
            if rat_id:
                self._load_rat_full(rat_id)

    def _load_rat_full(self, rat_id: str):
        def fetch():
            return self.api.get(f"/rat/{rat_id}/full")

        worker = ApiWorker(fetch, parent=self)
        worker.finished.connect(self._apply_rat_data)
        worker.error.connect(self._on_load_error)
        worker.start()

    # ------------------------------------------------------------------
    # NIVEL EN TIEMPO REAL (Section 1 Labels)
    # ------------------------------------------------------------------
    def _bind_niveles_en_tiempo_real(self):
        RISK_LEVEL_MATRIX = {
            ("Despreciable", "Despreciable"): "Bajo",
            ("Despreciable", "Limitado"): "Bajo",
            ("Despreciable", "Significativo"): "Medio",
            ("Despreciable", "Máximo"): "Medio",
            ("Limitado", "Despreciable"): "Bajo",
            ("Limitado", "Limitado"): "Medio",
            ("Limitado", "Significativo"): "Medio",
            ("Limitado", "Máximo"): "Alto",
            ("Significativo", "Despreciable"): "Medio",
            ("Significativo", "Limitado"): "Medio",
            ("Significativo", "Significativo"): "Alto",
            ("Significativo", "Máximo"): "Alto",
            ("Máximo", "Despreciable"): "Medio",
            ("Máximo", "Limitado"): "Alto",
            ("Máximo", "Significativo"): "Alto",
            ("Máximo", "Máximo"): "Muy Alto",
        }

        ambitos = [
            ("licitud_probabilidad", "licitud_impacto", "licitud"),
            ("finalidad_probabilidad", "finalidad_impacto", "finalidad"),
            ("proporcionabilidad_probabilidad", "proporcionabilidad_impacto", "proporcionabilidad"),
            ("calidad_probabilidad", "calidad_impacto", "calidad"),
            ("responsabilidad_probabilidad", "responsabilidad_impacto", "responsabilidad"),
            ("seguridad_probabilidad", "seguridad_impacto", "seguridad"),
            ("transparencia_probabilidad", "transparencia_impacto", "transparencia"),
            ("confidencialidad_probabilidad", "confidencialidad_impacto", "confidencialidad"),
            ("coordinacion_probabilidad", "coordinacion_impacto", "coordinacion"),
        ]

        for prob_key, impact_key, prefix in ambitos:
            prob = self.inputs.get(prob_key)
            impact = self.inputs.get(impact_key)

            if not prob or not impact:
                continue

            nivel_label = QLabel("Nivel: -", self)
            nivel_label.setStyleSheet("""
                QLabel {
                    background-color: #f1f5f9;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 600;
                    color: #0f172a;
                }
            """)

            # Add to layout if not already there
            if impact.parentWidget() and impact.parentWidget().layout():
                impact.parentWidget().layout().addWidget(nivel_label)

            def make_update(p, i, lbl, pref):
                def update():
                    nivel = RISK_LEVEL_MATRIX.get(
                        (p.currentText(), i.currentText()), "Bajo"
                    )
                    lbl.setText(f"Nivel: {nivel}")
                    # Also trigger the matrix sync!
                    self._sync_risk_matrix(pref)
                return update

            updater = make_update(prob, impact, nivel_label, prefix)
            prob.currentIndexChanged.connect(updater)
            impact.currentIndexChanged.connect(updater)
            updater()

    # ------------------------------------------------------------------
    # Apply RAT data (SIN ROMPER NADA)
    # ------------------------------------------------------------------
    def _get_catalog_labels(self, endpoint: str, cache_key: str) -> dict[str, str]:
        cache_id = f"{endpoint}::{cache_key}"
        if cache_id in self._catalog_label_cache:
            return self._catalog_label_cache[cache_id]

        labels = {}
        try:
            rows = self.catalogo_service.get_catalogo(endpoint, cache_key) or []
            labels = {
                str(item.get("id")): item.get("nombre", "")
                for item in rows
                if item.get("id") is not None
            }
        except Exception:
            labels = {}

        self._catalog_label_cache[cache_id] = labels
        return labels

    def _map_catalog_values(self, values, endpoint: str, cache_key: str):
        labels = self._get_catalog_labels(endpoint, cache_key)

        if isinstance(values, list):
            return [labels.get(str(v), str(v)) for v in values]

        if values is None:
            return None

        return labels.get(str(values), str(values))

    def _first_non_empty(self, *values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            return value
        return None

    def _resolve_eipd_value(self, eipd_key: str, rat: dict):
        if eipd_key == "categorias_datos_rat":
            tipos_datos = self._map_catalog_values(
                rat.get("tipos_datos"),
                "/catalogos/rat/tipo-datos",
                "catalogo_rat_tipo_datos"
            )
            if tipos_datos:
                return tipos_datos

            categorias = self._first_non_empty(
                rat.get("categorias_datos_personales"),
                rat.get("categorias_datos_inst"),
            )
            return self._map_catalog_values(
                categorias,
                "/catalogos/rat/categoria-datos-personales",
                "catalogo_rat_categoria_datos_personales"
            )

        if eipd_key == "marco_normativo_rat":
            nombre_mecanismo = rat.get("nombre_mecanismo")
            if nombre_mecanismo:
                return nombre_mecanismo
            return self._map_catalog_values(
                rat.get("mecanismo_habilitante"),
                "/catalogos/marco-habilitante",
                "catalogo_marco_habilitante_rat"
            )

        if eipd_key == "origen_recoleccion":
            fuente = self._first_non_empty(rat.get("fuente_datos"))
            medio_origen = self._first_non_empty(rat.get("medio_recoleccion_origen"))
            forma = self._first_non_empty(rat.get("forma_recoleccion"))

            # Prioriza la etapa 5 del RAT institucional
            partes_origen = [p for p in [fuente, medio_origen, forma] if p]
            if partes_origen:
                return partes_origen

            origen_raw = self._first_non_empty(
                rat.get("origen_datos"),
                rat.get("origen_datos_titulares"),
            )
            medio_raw = self._first_non_empty(
                rat.get("medio_recoleccion"),
                rat.get("medio_recoleccion_titulares"),
            )
            origen = self._map_catalog_values(
                origen_raw,
                "/catalogos/rat/origen-datos",
                "catalogo_rat_origen_datos"
            )
            medio = self._map_catalog_values(
                medio_raw,
                "/catalogos/rat/medio-recoleccion",
                "catalogo_rat_medio_recoleccion"
            )
            partes_fallback = [p for p in [origen, medio] if p]
            if partes_fallback:
                return partes_fallback
            return None

        if eipd_key == "conclusiones_rat":
            return rat.get("sintesis_analisis")

        if eipd_key == "titulares_datos":
            poblaciones = self._map_catalog_values(
                self._first_non_empty(
                    rat.get("poblaciones_vulnerables_inst"),
                    rat.get("poblaciones_vulnerables"),
                ),
                "/catalogos/rat/poblacion-especial",
                "catalogo_rat_poblacion-especial"
            )
            poblaciones_otro = rat.get("poblaciones_vulnerables_otro")

            partes = []
            if isinstance(poblaciones, list):
                partes.extend([str(p) for p in poblaciones if p])
            elif poblaciones:
                partes.append(str(poblaciones))
            if poblaciones_otro:
                partes.append(str(poblaciones_otro))

            if partes:
                return partes
            return None

        rat_key_map = {
            "descripcion_general": "descripcion_alcance",
            "resultados_esperados": "resultados_esperados",
            "alcance_analisis": "sintesis_analisis",
            "exclusiones_analisis": "exclusiones_analisis",
            "justificacion": "justificacion",
        }

        if eipd_key == "finalidades":
            return self._first_non_empty(
                rat.get("finalidad_tratamiento"),
                rat.get("finalidad_tratamiento_inst"),
                rat.get("finalidad_principal_ia"),
            )

        rat_key = rat_key_map.get(eipd_key)
        if not rat_key:
            return None
        return rat.get(rat_key)

    def _apply_rat_data(self, rat: dict):
        readonly_keys = {
            "marco_normativo_rat",
            "descripcion_general",
            "finalidades",
            "resultados_esperados",
            "titulares_datos",
            "categorias_datos_rat",
            "origen_recoleccion",
            "alcance_analisis",
            "conclusiones_rat",
            "justificacion",
        }

        eipd_keys = [
            "descripcion_general",
            "resultados_esperados",
            "categorias_datos_rat",
            "alcance_analisis",
            "conclusiones_rat",
            "marco_normativo_rat",
            "finalidades",
            "titulares_datos",
            "origen_recoleccion",
            "exclusiones_analisis",
            "justificacion",
            "unidades_perfiles_acceso",
            "diagrama_flujo_datos_personales",
        ]

        # Visibility logic for Exclusiones (only for PROCESO)
        tipo_rat = rat.get("tipo_rat")
        is_proceso = (tipo_rat == "PROCESO")
        
        block_excl = self.blocks.get("exclusiones_analisis")
        if block_excl:
            block_excl.setVisible(is_proceso)

        for eipd_key in eipd_keys:
            widget = self.inputs.get(eipd_key)
            value = self._resolve_eipd_value(eipd_key, rat)

            if not widget:
                continue

            if isinstance(widget, QLineEdit):
                if isinstance(value, list):
                    widget.setText(", ".join(map(str, value)))
                elif isinstance(value, dict):
                    widget.setText(json.dumps(value, ensure_ascii=False))
                elif value is not None:
                    widget.setText(str(value))
                widget.setReadOnly(eipd_key in readonly_keys)

            elif isinstance(widget, QPlainTextEdit):
                if isinstance(value, list):
                    widget.setPlainText(", ".join(map(str, value)))
                elif isinstance(value, dict):
                    widget.setPlainText(json.dumps(value, ensure_ascii=False))
                elif value is not None:
                    widget.setPlainText(str(value))
                widget.setReadOnly(eipd_key in readonly_keys)
            
            # Handle FilePickerWidget specifically if needed, 
            # though it's usually not in RAT data
            elif hasattr(widget, "setText") and not isinstance(widget, (QLineEdit, QPlainTextEdit)):
                if value is not None:
                    widget.setText(str(value))
                if hasattr(widget, "setReadOnly"):
                    widget.setReadOnly(eipd_key in readonly_keys)

            elif isinstance(widget, CheckableComboBox):
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except Exception:
                        value = []
                if not isinstance(value, list):
                    value = []
                widget.setCurrentData(value)

            elif isinstance(widget, QComboBox):
                self._set_combo_value(widget, value)
