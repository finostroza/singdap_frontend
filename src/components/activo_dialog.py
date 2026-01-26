from src.components.generic_form_dialog import GenericFormDialog
from pathlib import Path

class ActivoDialog(GenericFormDialog):
    def __init__(self, parent=None, activo_id=None):
        # Resolve config relative to THIS file or project root
        base_dir = Path(__file__).resolve().parent.parent.parent # singdap_frontend/
        config_path = base_dir / "src" / "config" / "formularios" / "activos.json"
        
        super().__init__(str(config_path), parent=parent, record_id=activo_id)

