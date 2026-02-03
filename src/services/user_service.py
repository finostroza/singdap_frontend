from src.core.api_client import ApiClient

class UserService:
    def __init__(self):
        self.api = ApiClient()

    def get_me(self) -> dict:
        return self.api.get("/users/me")
