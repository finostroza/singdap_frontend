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

    def list_users(self, page: int = 1, size: int = 10, nombre: str = None, rut: str = None, email: str = None, is_active: bool = None) -> dict:
        params = {"page": page, "size": size}
        if nombre: params["nombre"] = nombre
        if rut: params["rut"] = rut
        if email: params["email"] = email
        if is_active is not None: params["is_active"] = is_active
        return self.api.get("/users", params=params)

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
    def delete_user(self, user_id: str) -> dict:
        """Elimina un usuario de la base de datos."""
        return self.api.delete(f"/users/{user_id}")
