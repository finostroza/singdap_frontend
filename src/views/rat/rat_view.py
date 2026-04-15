import os
from src.components.generic_grid_view import GenericGridView

class RatView(GenericGridView):
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(src_dir, "config", "grillas", "rat.json")
        
        super().__init__(config_path=config_path)

    def refresh(self):
        """Asegurar que al entrar al módulo se vea el grid y se actualice"""
        if hasattr(self.grid_view, "refresh"):
            self.grid_view.refresh()
