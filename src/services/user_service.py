from src.core.api_client import ApiClient

class UserService:
    def __init__(self):
        self.api = ApiClient()

    def get_me(self) -> dict:
        return self.api.get("/users/me")

    def get_user(self, user_id: str) -> dict:
        return self.api.get(f"/users/{user_id}")

    def get_permissions(self, user_id: str) -> dict:
        return self.api.get(f"/users/{user_id}/permisos")

    def list_users(self) -> list[dict]:
        return self.api.get("/users")

    def list_modulos(self) -> list[dict]:
        return self.api.get("/admin/modulos")

    def list_privilegios(self) -> list[dict]:
        return self.api.get("/admin/privilegios")

    def update_estado(self, user_id: str, activo: bool) -> dict:
        return self.api.patch(f"/users/{user_id}/estado", {"activo": activo})

    def update_permiso(self, user_id: str, accion_id: str, permitido: bool) -> dict:
        """Actualiza un permiso específico de un usuario mediante PATCH."""
        return self.api.patch(f"/users/{user_id}/permisos/{accion_id}", {"permitido": permitido})

    def list_modulos_con_acciones(self) -> list[dict]:
        """Obtiene la matriz maestra de módulos con sus respectivos IDs de acción (permisos)."""
        return self.api.get("/admin/modulos/con-acciones")
