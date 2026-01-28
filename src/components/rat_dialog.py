from src.components.generic_form_dialog import GenericFormDialog
from pathlib import Path

class RatDialog(GenericFormDialog):
    def __init__(self, parent=None, rat_id=None, **kwargs):
        # Resolve config relative to THIS file or project root
        base_dir = Path(__file__).resolve().parent.parent.parent # singdap_frontend/
        config_path = base_dir / "src" / "config" / "formularios" / "rat.json"
        
        # GridView passes arguments based on "campo_id" in grid config.
        # For RAT, likely "rat_id" or "id".
        # We accept rat_id explicitly, but check kwargs just in case.
        target_id = rat_id
        if target_id is None:
             target_id = kwargs.get("id")
        
        super().__init__(str(config_path), parent=parent, record_id=target_id)
