import json
from src.components.generic_form_dialog import GenericFormDialog
from pathlib import Path
from PySide6.QtWidgets import QComboBox, QMessageBox, QApplication, QDateEdit, QLineEdit, QTextEdit, QCheckBox, QLabel
from PySide6.QtCore import Qt

from src.workers.api_worker import ApiWorker

class EipdDialog(GenericFormDialog):
    def __init__(self, parent=None, eipd_id=None, **kwargs):
        # Resolve config relative to THIS file or project root
        base_dir = Path(__file__).resolve().parent.parent.parent # singdap_frontend/
        config_path = base_dir / "src" / "config" / "formularios" / "eipd.json"
        
        target_id = eipd_id
        if target_id is None:
             target_id = kwargs.get("id")
        
        super().__init__(str(config_path), parent=parent, record_id=target_id)

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
            "justificacion": "justificacion"
        }

        for eipd_key, rat_key in mapping.items():
            widget = self.inputs.get(eipd_key)
            value = rat.get(rat_key)

            if not widget:
                continue

            if isinstance(widget, QLineEdit):
                text = ""

                if isinstance(value, list):
                    # Mostrar listas como texto legible
                    text = ", ".join(str(v) for v in value)

                elif isinstance(value, dict):
                    # Fallback simple
                    text = json.dumps(value, ensure_ascii=False)

                elif value is not None:
                    text = str(value)

                widget.setText(text)
                widget.setReadOnly(True)
            # COMBO SIMPLE
            elif isinstance(widget, QComboBox):
                self._set_combo_value(widget, value)
                widget.setEnabled(False)

            # COMBO MULTIPLE
            elif widget.__class__.__name__ == "CheckableComboBox":
                values = value or []
                for i in range(widget.count()):
                    item = widget.model().item(i, 0)
                    item.setCheckState(
                        Qt.Checked if widget.itemData(i) in values else Qt.Unchecked
                    )
                widget.updateText()
                widget.setEnabled(False)
