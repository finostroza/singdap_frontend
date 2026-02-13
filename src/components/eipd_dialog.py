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

        super().__init__(str(config_path), parent=parent, record_id=target_id)
        self._catalog_label_cache = {}

        # Nivel en tiempo real (Section 1 labels)
        QTimer.singleShot(100, self._bind_niveles_en_tiempo_real)

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
            "exclusiones_analisis",
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
        ]

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
