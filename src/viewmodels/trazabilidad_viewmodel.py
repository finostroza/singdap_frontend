from typing import List, Dict, Optional
from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker
import re

class TrazabilidadViewModel(QObject):
    # Signals
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_results_ready = Signal(list) # Emits list of results
    on_validation_error = Signal(str)

    def __init__(self):
        super().__init__()
        self._results = []
        self.client = ApiClient()
        self.worker = None

    def validate_run(self, run: str) -> bool:
        clean_run = run.strip()
        if not clean_run:
            self.on_validation_error.emit("El RUN no puede estar vacío.")
            return False
        return True

    @Slot(str)
    def consultar_trazabilidad(self, run: str):
        if not self.validate_run(run):
            return

        self.on_loading.emit(True)
        
        # Backend expects { "run": "..." }
        payload = {"run": run.strip()}
        
        # Use ApiWorker to make the call asynchronous
        self.worker = ApiWorker(self.client.post, "/trazabilidad/consulta", payload)
        self.worker.finished.connect(self._handle_success)
        self.worker.error.connect(self._handle_error)
        self.worker.start()

    def _handle_success(self, response):
        self.on_loading.emit(False)
        if isinstance(response, list):
            self._results = response
            self.on_results_ready.emit(self._results)
        else:
            self.on_error.emit("Respuesta inesperada del servidor.")

    def _handle_error(self, error_msg):
        self.on_loading.emit(False)
        if "404" in error_msg:
            self.on_error.emit("Servicio de trazabilidad no encontrado.")
        elif "400" in error_msg and "RUN configurado" in error_msg:
             self.on_error.emit("Su usuario no tiene un RUN configurado para realizar consultas. Contacte al administrador.")
        else:
            self.on_error.emit(f"Error al consultar: {error_msg}")

    def get_results(self) -> List[Dict]:
        return self._results
