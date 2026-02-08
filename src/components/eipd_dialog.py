import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QLabel,
    QTableWidgetItem
)
from PySide6.QtCore import Qt, QTimer

from src.components.generic_form_dialog import GenericFormDialog
from src.workers.api_worker import ApiWorker


class EipdDialog(GenericFormDialog):

    AMBITS = [
        "Lícitud y Lealtad",
        "Finalidad",
        "Proporcionalidad",
        "Calidad",
        "Responsabilidad",
        "Seguridad",
        "Transparencia e Información",
        "Confidencialidad",
        "Coordinación",
    ]

    def __init__(self, parent=None, eipd_id=None, **kwargs):
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "src" / "config" / "formularios" / "eipd.json"

        target_id = eipd_id or kwargs.get("id")

        super().__init__(str(config_path), parent=parent, record_id=target_id)

        # Nivel en tiempo real (cuando el form ya existe)
        QTimer.singleShot(0, self._bind_niveles_en_tiempo_real)

    def _load_section(self, section_index: int):
        super()._load_section(section_index)

        # Sección 2 = Matriz de riesgos
        if section_index == 2:
            self._preload_matriz_riesgos()


    # ------------------------------------------------------------------
    # MATRIZ DE RIESGOS (PRECARGA)
    # ------------------------------------------------------------------
    def _preload_matriz_riesgos(self):
        table = self.inputs.get("matriz_riesgos")

        if not table:
            return

        table.setRowCount(len(self.AMBITS))

        for row, ambito in enumerate(self.AMBITS):
            item = QTableWidgetItem(ambito)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, item)

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
    # NIVEL EN TIEMPO REAL (ÁMBITOS)
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
            ("licitud_probabilidad", "licitud_impacto"),
            ("finalidad_probabilidad", "finalidad_impacto"),
            ("proporcionabilidad_probabilidad", "proporcionabilidad_impacto"),
            ("calidad_probabilidad", "calidad_impacto"),
            ("responsabilidad_probabilidad", "responsabilidad_impacto"),
            ("seguridad_probabilidad", "seguridad_impacto"),
            ("transparencia_probabilidad", "transparencia_impacto"),
            ("confidencialidad_probabilidad", "confidencialidad_impacto"),
            ("coordinacion_probabilidad", "coordinacion_impacto"),
        ]

        for prob_key, impact_key in ambitos:
            prob = self.inputs.get(prob_key)
            impact = self.inputs.get(impact_key)

            if not prob or not impact:
                continue

            nivel_label = QLabel("Nivel: -", self)
            nivel_label.setStyleSheet("""
                QLabel {
                    background-color: #e2e8f0;
                    border-radius: 10px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 600;
                    color: #0f172a;
                }
            """)

            impact.parentWidget().layout().addWidget(nivel_label)

            def make_update(p, i, lbl):
                def update():
                    nivel = RISK_LEVEL_MATRIX.get(
                        (p.currentText(), i.currentText()), "-"
                    )
                    lbl.setText(f"Nivel: {nivel}")
                return update

            updater = make_update(prob, impact, nivel_label)
            prob.currentIndexChanged.connect(updater)
            impact.currentIndexChanged.connect(updater)
            updater()

    # ------------------------------------------------------------------
    # Apply RAT data (SIN ROMPER NADA)
    # ------------------------------------------------------------------
    def _apply_rat_data(self, rat: dict):
        mapping = {
            "descripcion_general": "descripcion_alcance",
            "resultados_esperados": "resultados_esperados",
            "categorias_datos_rat": "categorias_datos_personales",
            "alcance_analisis": "sintesis_analisis",
            "conclusiones_rat": "conclusiones_rat",
            "marco_normativo_rat": "mecanismo_habilitante",
            "finalidades": "finalidad_tratamiento",
            "categorias_datos_inst": "categorias_datos_inst",
            "origen_recoleccion": "origen_datos",
            "justificacion": "justificacion",
        }

        for eipd_key, rat_key in mapping.items():
            widget = self.inputs.get(eipd_key)
            value = rat.get(rat_key)

            if not widget:
                continue

            if isinstance(widget, QLineEdit):
                if isinstance(value, list):
                    widget.setText(", ".join(map(str, value)))
                elif isinstance(value, dict):
                    widget.setText(json.dumps(value, ensure_ascii=False))
                elif value is not None:
                    widget.setText(str(value))
                widget.setReadOnly(True)

            elif isinstance(widget, QComboBox):
                self._set_combo_value(widget, value)
                widget.setEnabled(False)
