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
    on_indicadores_ready = Signal(dict)
    on_actualizacion_exitosa = Signal(str)

    def __init__(self):
        super().__init__()
        self.client = ApiClient()
        self._items = []
        self._detalle = None
        # Separate workers to avoid overwriting and thread crashes
        self.worker_list = None
        self.worker_detalle = None
        self.worker_update = None

    @Slot()
    def cargar_listado(self, tipo: Optional[str] = None):
        self.on_loading.emit(True)
        path = "/riesgos/seguimiento"
        if tipo:
            path += f"?tipo={tipo}"
        
        # Prevent double triggering same type or crashing previous same type
        if self.worker_list and self.worker_list.isRunning():
            self.worker_list.terminate() # or just wait, but terminate is safer for cleanup
            self.worker_list.wait()
            
        self.worker_list = ApiWorker(self.client.get, path)
        self.worker_list.finished.connect(self._handle_listado_success)
        self.worker_list.error.connect(self._handle_error)
        self.worker_list.start()

    def _handle_listado_success(self, response):
        self.on_loading.emit(False)
        items = response if isinstance(response, list) else response.get("items", [])
        self._items = items
        
        # Calculate Indicators
        indicadores = {
            "rat_pendientes": 0,
            "rat_subsanados": 0,
            "eipd_pendientes": 0,
            "eipd_subsanados": 0
        }
        for item in items:
            if item.get("tipo") == "RAT":
                if item.get("n_riesgos") == item.get("n_subsanados"):
                    indicadores["rat_subsanados"] += 1
                else:
                    indicadores["rat_pendientes"] += 1
            else: # EIPD
                if item.get("n_riesgos") == item.get("n_subsanados"):
                    indicadores["eipd_subsanados"] += 1
                else:
                    indicadores["eipd_pendientes"] += 1
        
        self.on_indicadores_ready.emit(indicadores)
        self.on_listado_ready.emit(items)

    @Slot(str, str)
    def cargar_detalle(self, tipo: str, item_id: str):
        self.on_loading.emit(True)
        endpoint = f"/riesgos/{tipo.lower()}/{item_id}"
        
        if self.worker_detalle and self.worker_detalle.isRunning():
            self.worker_detalle.terminate()
            self.worker_detalle.wait()
            
        self.worker_detalle = ApiWorker(self.client.get, endpoint)
        self.worker_detalle.finished.connect(self._handle_detalle_success)
        self.worker_detalle.error.connect(self._handle_error)
        self.worker_detalle.start()

    def _handle_detalle_success(self, response):
        self.on_loading.emit(False)
        self._detalle = response
        self.on_detalle_ready.emit(response)

    @Slot(str, str, dict)
    def actualizar_riesgo(self, tipo: str, riesgo_id: str, payload: dict):
        self.on_loading.emit(True)
        endpoint = f"/riesgos/{tipo.lower()}/{riesgo_id}"
        
        if self.worker_update and self.worker_update.isRunning():
            self.worker_update.terminate()
            self.worker_update.wait()
            
        self.worker_update = ApiWorker(self.client.patch, endpoint, payload)
        self.worker_update.finished.connect(self._handle_actualizacion_success)
        self.worker_update.error.connect(self._handle_error)
        self.worker_update.start()

    def _handle_actualizacion_success(self, response):
        self.on_loading.emit(False)
        msg = response.get("mensaje", "Riesgo actualizado correctamente.")
        self.on_actualizacion_exitosa.emit(msg)

    def _handle_error(self, error_msg):
        self.on_loading.emit(False)
        self.on_error.emit(f"Error: {error_msg}")
