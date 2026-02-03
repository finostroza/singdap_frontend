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
        self._initialized = True

    def set_token(self, token: str):
        self.token = token
    
    def set_user_id(self, user_id: str):
        self.user_id = user_id

    def clear_session(self):
        self.token = None
        self.user_id = None

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
    def get(self, path: str):
        url = self._build_url(path)
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    # ===============================
    # POST
    # ===============================
    def post(self, path: str, data: dict):
        url = f"{self.base_url}{path}"
        response = requests.post(
            url,
            json=data,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    # ===============================
    # DELETE
    # ===============================
    
    def delete(self, endpoint):
        r = requests.delete(self.base_url + endpoint)
        r.raise_for_status()
        return r.json() if r.content else None
    
    # ===============================
    # PUT 
    # ===============================
    def put(self, endpoint: str, payload: dict):
        url = f"{self.base_url}{endpoint}"
        response = requests.put(url, json=payload)
        response.raise_for_status()
        return response.json()
