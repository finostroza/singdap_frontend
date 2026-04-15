import json
from src.core.api_client import ApiClient
from src.services.cache_manager import CacheManager
from src.workers.combo_loader import ComboLoaderRunnable
from PySide6.QtCore import QThreadPool, QObject

class InventoryCacheService(QObject):
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InventoryCacheService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.api = ApiClient()
        self.cache = CacheManager()
        self.thread_pool = QThreadPool.globalInstance()
        self._initialized = True

    def refresh_inventory_cache(self):
        """
        Inicia la carga del inventario en segundo plano.
        """
        print("[InventoryCacheService] Refrescando cache de inventario...")
        worker = ComboLoaderRunnable(self._do_fetch)
        self.thread_pool.start(worker)

    def _do_fetch(self):
        try:
            # 1. Consultar API con size=1000
            # Usamos get_raw o get básico. ApiClient.get ya lanza excepciones.
            data = self.api.get("/activos/catalogos", params={"size": 1000})
            
            # 2. Obtener lista de items (puede venir directo o paginado)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("items", [])
            
            # 3. Filtrar y mapear
            # Regla: solo 'activo' = 'activo'
            # Mapeo: {id: activo_id, nombre: nombre_activo}
            filtered = []
            for item in items:
                # Normalizar estado para comparación
                estado = str(item.get("estado_activo") or "").lower()
                if estado == "activo":
                    filtered.append({
                        "id": item.get("activo_id"),
                        "nombre": item.get("nombre_activo")
                    })
            
            # 4. Guardar en cache global bajo una llave conocida
            self.cache.set("catalogo_inventario_activos", filtered)
            print(f"[InventoryCacheService] Cache actualizado con {len(filtered)} activos de un total de {len(items)} recibidos.")
            return filtered
        except Exception as e:
            print(f"[InventoryCacheService] Error al refrescar cache: {e}")
            return []
