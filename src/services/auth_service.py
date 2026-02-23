from src.core.api_client import ApiClient


class AuthService:
    def __init__(self, api_client: ApiClient):
        self.api = api_client

    def login(self, rut: str, password: str) -> dict:
        return self.api.post(
            "/auth/login",
            {
                "rut": rut,
                "password": password
            }
        )
