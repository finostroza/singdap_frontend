from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker
import json
import os

class DashboardViewModel(QObject):
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_stats_ready = Signal(dict)
    on_instituciones_ready = Signal(object)  # lista o dict según respuesta API
    on_instituciones_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.api = ApiClient()

    @Slot()
    def cargar_estadisticas(self):
        self.on_loading.emit(True)
        self.worker = ApiWorker(self.api.get, "/dashboard/estadisticas")
        self.worker.finished.connect(self._handle_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    @Slot(bool)
    def cargar_instituciones(self, force_api=False):
        """Carga datos de instituciones. Por defecto carga local. Solo API si force_api es True."""
        # Cargar datos locales siempre primero para asegurar visualización
        self._cargar_datos_locales()
        
        # Solo consultamos la API si se solicita explícitamente (ej. botón Recargar)
        if force_api:
            print("DEBUG DASHBOARD: Iniciando consulta API para instituciones...")
            self.worker_inst = ApiWorker(self.api.get, "/dashboard/instituciones")
            self.worker_inst.finished.connect(self._handle_instituciones_success)
            self.worker_inst.error.connect(lambda e: self.on_instituciones_error.emit(str(e)))
            self.worker_inst.start()

    def _cargar_datos_locales(self):
        """Carga datos desde el archivo local instituciones_data.json."""
        try:
            # Intentar varias rutas posibles del archivo local
            paths = [
                os.path.join(os.getcwd(), "src", "data", "instituciones_data.json"),
                os.path.join(os.path.dirname(__file__), "..", "data", "instituciones_data.json")
            ]
            
            for path in paths:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.on_instituciones_ready.emit(data)
                        return True
        except Exception as e:
            print(f"Error al cargar datos locales: {e}")
        return False

    def _handle_success(self, data):
        self.on_loading.emit(False)
        if isinstance(data, dict):
            self.on_stats_ready.emit(data)
        else:
            self.on_error.emit("Formato de respuesta inválido")

    def _handle_instituciones_success(self, data):
        self.on_instituciones_ready.emit(data)

    def _handle_error(self, error_msg):
        self.on_loading.emit(False)
        self.on_error.emit(str(error_msg))
