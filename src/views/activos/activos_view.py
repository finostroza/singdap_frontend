import os
from src.components.generic_grid_view import GenericGridView

from src.services.cache_manager import CacheManager

class ActivosView(GenericGridView):
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(src_dir, "config", "grillas", "activos.json")
        
        super().__init__(config_path=config_path)
        self.cache = CacheManager()

    def refresh(self):
        """Asegurar que al entrar al módulo se vea el grid y se actualice"""
        self._reload_all()

    def _on_reload_finished(self, data):
        """Sobrescribimos para inyectar indicadores calculados localmente si la API falla."""
        # 1. Ejecutar lógica estándar (poblar tabla e indicadores de API)
        super()._on_reload_finished(data)
        
        # 2. Suplementar/Corregir con indicadores de la cache local (calculados en InventoryCacheService)
        local_stats = self.cache.get("indicadores_activos_local")
        if local_stats:
            print(f"[ActivosView] Suplementando indicadores con cache local: {local_stats}")
            # Forzamos la actualización de las tarjetas con los datos de la cache
            self._populate_indicators(local_stats)
