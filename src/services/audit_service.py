from src.core.api_client import ApiClient

class AuditService:
    def __init__(self):
        self.api = ApiClient()

    def get_audit_logs(self, page: int = 1, size: int = 20, fecha_desde: str = None, fecha_hasta: str = None, action: str = None, entity: str = None, usuario: str = None) -> dict:
        """
        Obtiene los logs de auditoría según los filtros proporcionados.
        """
        params = {
            "page": page,
            "size": size
        }
        if fecha_desde: params["fecha_desde"] = fecha_desde
        if fecha_hasta: params["fecha_hasta"] = fecha_hasta
        if action: params["action"] = action
        if entity: params["entity"] = entity
        if usuario: params["usuario"] = usuario

        # Endpoint: /admin/audit-log o /audit-log según docs
        # Por la imagen y contexto usaremos /audit-log
        return self.api.get("/audit-log", params=params)
