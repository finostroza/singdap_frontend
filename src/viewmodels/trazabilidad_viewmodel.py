from typing import List, Dict
from PySide6.QtCore import QObject, Signal, Slot
from src.core.api_client import ApiClient
from src.workers.api_worker import ApiWorker
import re


class TrazabilidadViewModel(QObject):
    on_loading = Signal(bool)
    on_error = Signal(str)
    on_validation_error = Signal(str)
    on_results_ready = Signal(list)        # Tab "Consultas API"
    on_instituciones_ready = Signal(list)  # Tab "Por Institución"
    on_instituciones_error = Signal(str)
    on_users_ready = Signal(list)          # Listado de responsables
    on_email_sent = Signal(dict)           # Resultado envío correo

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
        """Dispara las consultas de trazabilidad e instituciones en paralelo."""
        if not self.validate_run(run_con_dv):
            return
        run_limpio = run_con_dv.strip()
        run_sin_dv = self._strip_dv(run_limpio)
        
        self.on_loading.emit(True)
        self._consultar_api(run_limpio)
        self._consultar_instituciones(run_sin_dv)

    # ── Consulta API (envía RUN con DV) ───────────────────────────────────

    def _consultar_api(self, run_con_dv: str):
        payload = {"run": run_con_dv}
        self._worker_consulta = ApiWorker(self.client.post, "/trazabilidad/consulta", payload)
        self._worker_consulta.finished.connect(self._handle_consulta_success)
        self._worker_consulta.error.connect(self._handle_consulta_error)
        self._worker_consulta.start()

    def _handle_consulta_success(self, response):
        self.on_loading.emit(False)
        results = None
        if isinstance(response, list):
            results = response
        elif isinstance(response, dict):
            for key in ["data", "results", "consultas", "items", "registros"]:
                if key in response and isinstance(response[key], list):
                    results = response[key]
                    break
            if results is None:
                pass

        if results is not None:
            self._results = results
            self.on_results_ready.emit(self._results)
        else:
            self.on_error.emit("Respuesta inesperada del servicio de consultas.")

    def _handle_consulta_error(self, error_msg):
        self.on_loading.emit(False)
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
                pass

        if results is not None:
            self._instituciones = results
            self.on_instituciones_ready.emit(self._instituciones)
        else:
            self.on_instituciones_error.emit("Respuesta inesperada del servicio de instituciones.")

    def _handle_instituciones_error_slot(self, error_msg):
        self.on_loading.emit(False)
        self.on_instituciones_error.emit(f"Error al consultar instituciones: {error_msg}")

    # ── Usuarios (para Persona Responsable) ───────────────────────────────

    def fetch_users(self):
        """Obtiene el listado de usuarios responsables (limite 1000)."""
        params = {"size": "1000"} 
        self._worker_users = ApiWorker(self.client.get, "/users/", params)
        self._worker_users.finished.connect(self._handle_users_success)
        self._worker_users.error.connect(lambda e: (
            self.on_loading.emit(False), 
            self.on_error.emit(f"Error cargando usuarios: {e}")))
        self._worker_users.start()

    def _handle_users_success(self, response):
        users = []
        if isinstance(response, list):
            users = response
        elif isinstance(response, dict):
            # Buscar en claves conocidas
            for key in ["data", "items", "results", "users", "usuarios", "registros"]:
                if key in response and isinstance(response[key], list):
                    users = response[key]
                    break
            
            # Si no se encuentra, buscar CUALQUIER lista en el objeto
            if not users:
                for val in response.values():
                    if isinstance(val, list) and len(val) > 0:
                        users = val
                        break
        
        active_users = []
        for u in users:
            if not isinstance(u, dict): continue
            
            # Buscar claves de forma insensible a mayúsculas
            u_low = {k.lower(): v for k, v in u.items()}
            
            is_active = (u_low.get("is_active") if u_low.get("is_active") is not None 
                        else u_low.get("isactive") if u_low.get("isactive") is not None
                        else u_low.get("active", True)) # Default True si no existe
            
            nombre = (u_low.get("nombre_completo") or 
                      u_low.get("fullname") or 
                      u_low.get("nombre_completo") or # por si acaso
                      u_low.get("name") or 
                      u_low.get("completo") or
                      "Usuario sin nombre")
            
            email = u_low.get("email") or u_low.get("correo") or u_low.get("mail") or ""
            
            # Normalizar booleano de activación
            is_active_bool = False
            if is_active is True or str(is_active).lower() in ["true", "1", "yes", "active"]:
                is_active_bool = True
            
            if is_active_bool:
                active_users.append({
                    "nombre_completo": str(nombre).strip(),
                    "email": str(email).lower().strip()
                })
        
        # Siempre emitir, aunque esté vacío para limpiar el combo si es necesario
        if active_users:
            active_users.sort(key=lambda x: x["nombre_completo"].lower())
            
        self.on_users_ready.emit(active_users)

    # ── Envío de Correo ───────────────────────────────────────────────────
    
    def enviar_email(self, payload: dict):
        """Envía el requerimiento por email usando la API de correos (Formulario)."""
        self.on_loading.emit(True)
        # Endpoint actualizado para envío de formulario formateado
        self._worker_email = ApiWorker(self.client.post, "/emails/enviar-formulario", payload)
        self._worker_email.finished.connect(self._handle_email_success)
        self._worker_email.error.connect(self._handle_email_error)
        self._worker_email.start()

    def _handle_email_success(self, response):
        self.on_loading.emit(False)
        # Analizar respuesta según requerimiento: { "enviado": bool, "error_detalle": str }
        enviado = response.get("enviado", False)
        error_msg = response.get("error_detalle", "")
        
        self.on_email_sent.emit({
            "success": enviado,
            "error": error_msg
        })

    def _handle_email_error(self, error_msg):
        self.on_loading.emit(False)
        self.on_email_sent.emit({
            "success": False,
            "error": error_msg
        })

    # ── Acceso a datos ────────────────────────────────────────────────────

    def get_results(self) -> List[Dict]:
        return self._results

    def get_instituciones(self) -> List[Dict]:
        return self._instituciones
