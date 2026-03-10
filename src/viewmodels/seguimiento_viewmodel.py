from typing import List, Dict, Optional
from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker

class SeguimientoViewModel(QObject):
    # Signals
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_listado_ready = Signal(list)
    on_detalle_ready = Signal(dict)
    on_actualizacion_exitosa = Signal(str)

    def __init__(self):
        super().__init__()
        self.client = ApiClient()
        self._items = []
        self._detalle = None

    @Slot()
    def cargar_listado(self, tipo: Optional[str] = None):
        self.on_loading.emit(True)
        path = "/riesgos/seguimiento"
        if tipo:
            path += f"?tipo={tipo}"
        
        self.worker = ApiWorker(self.client.get, path)
        self.worker.finished.connect(self._handle_listado_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    def _handle_listado_success(self, response):
        self.on_loading.emit(False)
        items = response.get("items", [])
        self._items = items
        self.on_listado_ready.emit(items)

    @Slot(str, str)
    def cargar_detalle(self, tipo: str, item_id: str):
        self.on_loading.emit(True)
        # tipo: 'RAT' o 'EIPD'
        endpoint = f"/riesgos/{tipo.lower()}/{item_id}"
        
        self.worker = ApiWorker(self.client.get, endpoint)
        self.worker.finished.connect(self._handle_detalle_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    def _handle_detalle_success(self, response):
        self.on_loading.emit(False)
        self._detalle = response
        self.on_detalle_ready.emit(response)

    @Slot(str, str, dict)
    def actualizar_riesgo(self, tipo: str, riesgo_id: str, payload: dict):
        self.on_loading.emit(True)
        endpoint = f"/riesgos/{tipo.lower()}/{riesgo_id}"
        
        self.worker = ApiWorker(self.client.patch, endpoint, payload)
        self.worker.finished.connect(self._handle_actualizacion_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    def _handle_actualizacion_success(self, response):
        self.on_loading.emit(False)
        msg = response.get("mensaje", "Riesgo actualizado correctamente.")
        self.on_actualizacion_exitosa.emit(msg)

    def _handle_error(self, error_msg):
        self.on_loading.emit(False)
        self.on_error.emit(f"Error: {error_msg}")
