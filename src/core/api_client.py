import base64
import json
import requests
from src.config.settings import API_BASE_URL


class ApiClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApiClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.base_url = API_BASE_URL.rstrip('/')
        self.token = None
        self.user_id = None
        self.user_name = None
        self.rol_ris = None
        self._initialized = True

    def set_token(self, token: str):
        self.token = token
    
    def _decode_token(self):
        if not self.token:
            return {}

        try:
            payload_part = self.token.split(".")[1]
            padded = payload_part + "=" * (-len(payload_part) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            return json.loads(decoded)
        except Exception:
            return {}
        
    @property
    def roles(self):
        payload = self._decode_token()
        return payload.get("rol", [])

    @property
    def is_admin(self):
        return "ADMIN" in self.roles

    @property
    def is_auditor(self):
        return "AUDITOR" in self.roles
    
    def set_user_id(self, user_id: str):
        self.user_id = user_id

    def set_user_name(self, name: str):
        self.user_name = name

    def set_rol_ris(self, rol_ris: str):
        self.rol_ris = rol_ris

    def clear_session(self):
        self.token = None
        self.user_id = None
        self.user_name = None
        self.rol_ris = None

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _build_url(self, path: str) -> str:
        # 👉 Evita // y permite query params sin problemas
        return f"{self.base_url}/{path.lstrip('/')}"

    # ===============================
    # GET
    # ===============================
    def get(self, path: str, params: dict = None):
        url = self._build_url(path)
        print(f"[API REQUEST] GET {url} | Params: {params}")
        try:
            response = requests.get(url, headers=self._headers(), params=params)
            print(f"[API RESPONSE] {response.status_code} GET {path}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[API ERROR] GET {path}: {str(e)}")
            raise e

    def get_raw(self, path: str, params: dict = None):
        url = self._build_url(path)
        print(f"[API REQUEST] GET RAW {url}")
        try:
            response = requests.get(url, headers=self._headers(), params=params)
            print(f"[API RESPONSE] {response.status_code} GET RAW {path}")
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[API ERROR] GET RAW {path}: {str(e)}")
            raise e

    # ===============================
    # POST
    # ===============================
    def post(self, path: str, data: dict):
        url = self._build_url(path)
        print(f"[API REQUEST] POST {url} | Data: {data}")
        response = requests.post(url, json=data, headers=self._headers())
        print(f"[API RESPONSE] {response.status_code} POST {path}")
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 422:
                try:
                    detail = response.json().get("detail")
                    print(f"[API ERROR 422] Errores de validación en {path}: {detail}")
                except Exception:
                    print(f"[API ERROR 422] Fallo de validación en {path}: {response.text}")
            else:
                 print(f"[API ERROR] POST {path} ({response.status_code}): {response.text}")
            raise e
        return response.json()

    # ===============================
    # DELETE
    # ===============================
    def delete(self, path: str):
        url = self._build_url(path)
        print(f"[API REQUEST] DELETE {url}")
        response = requests.delete(url, headers=self._headers())
        print(f"[API RESPONSE] {response.status_code} DELETE {path}")
        try:
            response.raise_for_status()
        except Exception as e:
            print(f"[API ERROR] DELETE {path}: {str(e)}")
            raise e
        return response.json() if response.content else None
    
    # ===============================
    # PUT 
    # ===============================
    def put(self, path: str, payload: dict):
        url = self._build_url(path)
        print(f"[API REQUEST] PUT {url} | Payload: {payload}")
        response = requests.put(url, json=payload, headers=self._headers())
        print(f"[API RESPONSE] {response.status_code} PUT {path}")
        try:
            response.raise_for_status()
        except Exception as e:
            print(f"[API ERROR] PUT {path}: {str(e)}")
            raise e
        return response.json()

    # ===============================
    # PATCH
    # ===============================
    def patch(self, path: str, payload: dict):
        url = self._build_url(path)
        print(f"[API REQUEST] PATCH {url} | Payload: {payload}")
        response = requests.patch(url, json=payload, headers=self._headers())
        print(f"[API RESPONSE] {response.status_code} PATCH {path}")
        try:
            response.raise_for_status()
        except Exception as e:
            print(f"[API ERROR] PATCH {path}: {str(e)}")
            raise e
        return response.json()
