from typing import List, Dict
from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker
import re


class TrazabilidadViewModel(QObject):
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_validation_error = Signal(str)
    on_results_ready = Signal(list)        # POST /trazabilidad/consulta        → Tab "Consultas API"
    on_instituciones_ready = Signal(list)  # GET  /trazabilidad/instituciones/{run} → Tab "Por Institución"
    on_instituciones_error = Signal(str)

    _RUT_RE = re.compile(r"^\d{7,8}-[\dkK]$")

    def __init__(self):
        super().__init__()
        self._results = []
        self._instituciones = []
        self.client = ApiClient()
        self._worker_consulta = None
        self._worker_instituciones = None

    def validate_run(self, run: str) -> bool:
        clean = run.strip()
        if not clean:
            self.on_validation_error.emit("El RUN no puede estar vacío.")
            return False
        if not self._RUT_RE.match(clean):
            self.on_validation_error.emit(
                "Formato de RUN inválido.\nIngrese el RUN con dígito verificador (Ej: 12345678-9)."
            )
            return False
        return True

    @staticmethod
    def _strip_dv(run_con_dv: str) -> str:
        """Retorna solo los dígitos sin guión ni dígito verificador."""
        return run_con_dv.strip().split("-")[0].strip()

    @Slot(str)
    def consultar_todo(self, run_con_dv: str):
        """Dispara ambas consultas en paralelo con el mismo RUN ingresado."""
        if not self.validate_run(run_con_dv):
            return
        run_limpio = run_con_dv.strip()
        run_sin_dv = self._strip_dv(run_limpio)
        print(f"[DEBUG] consultar_todo → con_dv='{run_limpio}' | sin_dv='{run_sin_dv}'")
        self.on_loading.emit(True)
        self._consultar_api(run_limpio)
        self._consultar_instituciones(run_sin_dv)

    # ── Consulta API (envía RUN con DV) ───────────────────────────────────

    def _consultar_api(self, run_con_dv: str):
        payload = {"run": run_con_dv}
        print(f"[DEBUG /trazabilidad/consulta] payload enviado: {payload}")
        self._worker_consulta = ApiWorker(self.client.post, "/trazabilidad/consulta", payload)
        self._worker_consulta.finished.connect(self._handle_consulta_success)
        self._worker_consulta.error.connect(self._handle_consulta_error)
        self._worker_consulta.start()

    def _handle_consulta_success(self, response):
        self.on_loading.emit(False)
        print(f"[DEBUG /trazabilidad/consulta] tipo={type(response).__name__} respuesta={response}")
        results = None
        if isinstance(response, list):
            results = response
        elif isinstance(response, dict):
            for key in ["data", "results", "consultas", "items", "registros"]:
                if key in response and isinstance(response[key], list):
                    results = response[key]
                    break
            if results is None:
                print(f"[DEBUG /trazabilidad/consulta] claves disponibles: {list(response.keys())}")

        if results is not None:
            self._results = results
            self.on_results_ready.emit(self._results)
        else:
            self.on_error.emit("Respuesta inesperada del servicio de consultas.")

    def _handle_consulta_error(self, error_msg):
        self.on_loading.emit(False)
        print(f"[DEBUG /trazabilidad/consulta] ERROR: {error_msg}")
        if "404" in error_msg:
            self.on_error.emit("Servicio de trazabilidad no encontrado.")
        elif "400" in error_msg and "RUN configurado" in error_msg:
            self.on_error.emit(
                "Su usuario no tiene un RUN configurado para realizar consultas.\n"
                "Contacte al administrador."
            )
        else:
            self.on_error.emit(f"Error al consultar trazabilidad: {error_msg}")

    # ── Consulta por Institución (envía RUN sin DV) ────────────────────────

    def _consultar_instituciones(self, run_sin_dv: str):
        self._worker_instituciones = ApiWorker(
            self.client.get, f"/trazabilidad/instituciones/{run_sin_dv}"
        )
        self._worker_instituciones.finished.connect(self._handle_instituciones_success)
        self._worker_instituciones.error.connect(self._handle_instituciones_error_slot)
        self._worker_instituciones.start()

    def _handle_instituciones_success(self, response):
        self.on_loading.emit(False)
        print(f"[DEBUG /trazabilidad/instituciones] tipo={type(response).__name__} respuesta={response}")
        results = None
        if isinstance(response, list):
            results = response
        elif isinstance(response, dict):
            if "consultasInstituciones" in response and isinstance(response["consultasInstituciones"], list):
                results = response["consultasInstituciones"]
            else:
                for key in ["consultas", "results", "data", "items"]:
                    if key in response and isinstance(response[key], list):
                        results = response[key]
                        break
            if results is None:
                print(f"[DEBUG /trazabilidad/instituciones] claves disponibles: {list(response.keys())}")

        if results is not None:
            self._instituciones = results
            self.on_instituciones_ready.emit(self._instituciones)
        else:
            self.on_instituciones_error.emit("Respuesta inesperada del servicio de instituciones.")

    def _handle_instituciones_error_slot(self, error_msg):
        self.on_loading.emit(False)
        print(f"[DEBUG /trazabilidad/instituciones] ERROR: {error_msg}")
        self.on_instituciones_error.emit(f"Error al consultar instituciones: {error_msg}")

    # ── Acceso a datos ────────────────────────────────────────────────────

    def get_results(self) -> List[Dict]:
        return self._results

    def get_instituciones(self) -> List[Dict]:
        return self._instituciones
