import requests
from src.core.api_client import ApiClient


class AuthService:
    def __init__(self, api_client: ApiClient):
        self.api = api_client

    def login(self, rut: str, password: str) -> dict:
        url = self.api._build_url("/auth/login")
        try:
            response = requests.post(url, json={"rut": rut, "password": password}, headers=self.api._headers(), timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise Exception("CONNECTION_ERROR")
        except requests.exceptions.Timeout:
            raise Exception("CONNECTION_ERROR")
        except requests.exceptions.HTTPError as e:
            response = e.response
            msg = ""
            try:
                data = response.json()
                msg = data.get("error") or data.get("detail") or str(e)
            except Exception:
                msg = response.text or str(e)
                
            msg_lower = str(msg).lower()
            
            # Regla 2: Usuario existente pero inactivo
            if "desactivado" in msg_lower or "inactivo" in msg_lower or "inhabilitad" in msg_lower:
                raise Exception("INACTIVE_USER")
            # Regla 3: Usuario que pasa SSO pero no está en registros
            elif "no encontrad" in msg_lower or "no exist" in msg_lower or "registrad" in msg_lower:
                raise Exception("NOT_FOUND")
            # Regla 1 (fallback de servidor/conexión)
            elif response.status_code >= 500:
                raise Exception("CONNECTION_ERROR")
            # Regla 1: Errores de credenciales, SSO fallido o genericos 401/403
            else:
                raise Exception("SSO_FAILED")
        except Exception as e:
            raise Exception("CONNECTION_ERROR")
