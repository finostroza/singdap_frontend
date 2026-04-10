import threading
from typing import Dict, List, Optional
from src.core.api_client import ApiClient
from src.services.logger_service import LoggerService

class PermissionService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PermissionService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.api = ApiClient()
        self._user_permissions: Dict[str, Dict[str, bool]] = {}
        self._is_admin = False
        
        # Mapeo de Módulos (Ampliado para soportar detección por perfil)
        self.module_aliases = {
            "INVENTARIO": ["inventario", "activo", "activos", "inventory"],
            "EIPD": ["eipd", "pia", "impacto"],
            "USUARIOS": ["usuario", "usuarios", "rol", "roles", "admin"],
            "RAT": ["rat", "tratamiento"],
            "TRAZABILIDAD": ["trazabilidad", "trace"],
            "MANTENEDORES": ["mantenedor", "catalogo", "catalogos"],
            "SEGUIMIENTO": ["seguimiento", "riesgos", "followup"],
            "DASHBOARD": ["dashboard", "tablero", "indicadores", "panal", "reporte", "reportes"],
            "AUDITORIA": ["auditoria", "log", "audit", "historial"]
        }
        
        self._initialized = True

    def set_admin_status(self, is_admin: bool):
        self._is_admin = is_admin

    def _create_empty_perms(self):
        return {
            "VER": False,
            "CREAR": False,
            "EDITAR": False,
            "ELIMINAR": False,
            "APROBAR": False,
            "EXPORTAR": False
        }

    def set_permissions(self, permissions_payload: dict):
        """
        Calcula y almacena una matriz simplificada de permisos por módulo.
        Soporta permisos explícitos y permisos implícitos por perfil.
        """
        print(f"DEBUG PERMS: Payload recibido -> {permissions_payload}")
        if not permissions_payload:
            return
            
        self._user_permissions = {}
        
        if self._is_admin:
            return

        # 1. PERMISOS POR PERFILES (Acceso implícito basado en el nombre del rol/perfil)
        perfiles = [str(p).upper() for p in permissions_payload.get("perfiles", [])]
        for profile in perfiles:
            for mod_key, aliases in self.module_aliases.items():
                # Si el alias del módulo está contenido en el nombre del perfil (ej: 'CUSTODIO_ACTIVOS')
                if any(alias.upper() in profile for alias in aliases):
                    if mod_key not in self._user_permissions:
                        self._user_permissions[mod_key] = self._create_empty_perms()
                    self._user_permissions[mod_key]["VER"] = True

        # 2. PERMISOS EXPLÍCITOS (Lista de permisos granulares)
        permisos_raw = permissions_payload.get("permisos", [])
        for p in permisos_raw:
            # Detección flexible de claves de módulo y acción
            mod_code = p.get("modulo_codigo") or p.get("modulo_nombre") or p.get("modulo_id", "")
            acc_code = p.get("accion_codigo") or p.get("accion_nombre") or p.get("accion_id", "")
            
            # Manejo resiliente de booleano (soporta strings "True"/"False", ints 1/0, Bools)
            raw_permitido = p.get("permitido", False)
            if isinstance(raw_permitido, str):
                is_allowed = raw_permitido.lower() in ["true", "1", "t", "y", "yes", "si", "sí"]
            else:
                is_allowed = bool(raw_permitido)
            
            mod_key = self._resolve_module_key(str(mod_code))
            
            if mod_key not in self._user_permissions:
                self._user_permissions[mod_key] = self._create_empty_perms()
            
            action_type = self._detect_action(str(acc_code))
            if action_type:
                map_to_standard = {
                    "view": "VER", "create": "CREAR", "edit": "EDITAR",
                    "delete": "ELIMINAR", "approve": "APROBAR", "export": "EXPORTAR"
                }
                std_key = map_to_standard.get(action_type)
                if std_key:
                    # Registramos el valor real del backend
                    if is_allowed:
                        if mod_key not in self._user_permissions:
                            self._user_permissions[mod_key] = self._create_empty_perms()
                        self._user_permissions[mod_key][std_key] = True
                        # REGLA DE ORO: Si puede realizar cualquier acción en el módulo, debe poder VERLO.
                        self._user_permissions[mod_key]["VER"] = True
                        print(f"DEBUG PERMS: Concedido {mod_key} -> {std_key}")
                    else:
                        if mod_key not in self._user_permissions:
                            self._user_permissions[mod_key] = self._create_empty_perms()
                        # Solo sobreescribimos si no estaba ya habilitado (por perfil o similar)
                        if not self._user_permissions[mod_key].get(std_key, False):
                            self._user_permissions[mod_key][std_key] = False

        print(f"DEBUG PERMS: Matriz Final de Seguridad -> {self._user_permissions}")

    def _resolve_module_key(self, code: str) -> str:
        if not code: return "UNKNOWN"
        code_upper = code.upper()
        standard_keys = ["DASHBOARD", "REPORTES", "INVENTARIO", "EIPD", "USUARIOS", "RAT", "TRAZABILIDAD", "MANTENEDORES", "SEGUIMIENTO", "AUDITORIA"]
        
        if code_upper in standard_keys:
            return code_upper
            
        code_lower = code.lower()
        for key, aliases in self.module_aliases.items():
            if any(alias in code_lower for alias in aliases):
                return key
        return code_upper

    def _detect_action(self, text: str) -> Optional[str]:
        if not text: return None
        text = text.lower()
        view_tokens = ["view", "ver", "read", "leer", "list", "listar", "get", "consulta", "consultar"]
        create_tokens = ["create", "crear", "new", "nuevo", "alta", "insert", "registrar"]
        edit_tokens = ["edit", "editar", "update", "actualizar", "modificar", "modifica", "write", "escribir"]
        delete_tokens = ["delete", "eliminar", "remove", "borrar", "quitar"]
        approve_tokens = ["approve", "aprobar", "autorizar", "validar", "firma", "firmar"]
        export_tokens = ["export", "exportar", "download", "descargar", "csv", "excel", "pdf"]

        if any(token in text for token in delete_tokens): return "delete"
        if any(token in text for token in create_tokens): return "create"
        if any(token in text for token in edit_tokens): return "edit"
        if any(token in text for token in view_tokens): return "view"
        if any(token in text for token in approve_tokens): return "approve"
        if any(token in text for token in export_tokens): return "export"
        return None

    def has_permission(self, module_name: str, action: str) -> bool:
        if self._is_admin:
            return True
        module_perms = self._user_permissions.get(module_name.upper())
        if not module_perms:
            return False
        return module_perms.get(action.upper(), False)

    def has_module_access(self, module_name: str) -> bool:
        if self._is_admin:
            return True
        return self.has_permission(module_name, "VER")

    def clear(self):
        self._user_permissions = {}
        self._is_admin = False
