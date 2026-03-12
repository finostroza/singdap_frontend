import os
from src.components.generic_grid_view import GenericGridView
from PySide6.QtCore import Signal

class SeguimientoListadoGrid(GenericGridView):
    action_triggered = Signal(str, str, str) # action_id, record_id, tipo

    def __init__(self, parent=None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(src_dir, "config", "grillas", "seguimiento.json")
        
        super().__init__(config_path=config_path, parent=parent)
        # Disable internal reload to use ViewModel signals
        try:
            self.refresh_btn.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
            
        self.refresh_btn.clicked.connect(lambda: self.parent().viewmodel.cargar_listado() if self.parent() and hasattr(self.parent(), 'viewmodel') else self._reload_all())

    def _execute_action(self, action_config, record_id):
        action_id = action_config.get("id")
        
        # We need the 'tipo' from the raw items to know if it's RAT or EIPD
        # Find the item in self._raw_items
        item = next((i for i in self._raw_items if str(i.get(self.config["campo_id"])) == str(record_id)), None)
        tipo = item.get("tipo") if item else "RAT"
        
        if action_id == "editar_grilla":
            self.action_triggered.emit(action_id, str(record_id), tipo)
        else:
            super()._execute_action(action_config, record_id)

    def populate(self, items):
        # GenericGridView handles population from its own _reload_all
        # But if we want to manually populate from ViewModel signals, we need to be careful
        # Actually, GenericGridView fetches data itself. 
        # For now, let's let GenericGridView handle its own data loading.
        pass
