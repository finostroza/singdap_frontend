from PySide6.QtCore import QObject, Signal
from src.services.auth_service import AuthService
from src.workers.api_worker import ApiWorker


class LoginViewModel(QObject):
    login_success = Signal(dict)
    login_error = Signal(str)
    loading_changed = Signal(bool)

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service

    def login(self, rut: str, password: str):
        self.loading_changed.emit(True)

        def do_login():
            return self.auth_service.login(rut, password)

        self.worker = ApiWorker(do_login)
        self.worker.finished.connect(self._on_login_success)
        self.worker.error.connect(self._on_login_error)
        self.worker.start()

    def _on_login_success(self, result):
        self.login_success.emit(result)
        self.loading_changed.emit(False)

    def _on_login_error(self, error):
        self.login_error.emit(error)
        self.loading_changed.emit(False)
