from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker

class DashboardViewModel(QObject):
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_stats_ready = Signal(dict)

    def __init__(self):
        super().__init__()
        self.api = ApiClient()

    @Slot()
    def cargar_estadisticas(self):
        self.on_loading.emit(True)
        # Endpoint: /dashboard/estadisticas
        self.worker = ApiWorker(self.api.get, "/dashboard/estadisticas")
        self.worker.finished.connect(self._handle_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    def _handle_success(self, data):
        self.on_loading.emit(False)
        # We ensure data is a dict
        if isinstance(data, dict):
            self.on_stats_ready.emit(data)
        else:
            self.on_error.emit("Formato de respuesta inválido")

    def _handle_error(self, error_msg):
        self.on_loading.emit(False)
        self.on_error.emit(str(error_msg))
