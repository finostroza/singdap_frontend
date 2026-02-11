print("Starting main.py...")
import sys
print("Importing PySide6...")
from PySide6.QtWidgets import QApplication

print("Importing local modules...")
from src.core.api_client import ApiClient
from src.services.auth_service import AuthService
from src.viewmodels.login_viewmodel import LoginViewModel
from src.views.login_view import LoginView
from utils import load_styles, icon
print("All imports completed.")



def main():
    app = QApplication(sys.argv)
    
    app.setWindowIcon(icon("src/resources/images/app.ico"))

    load_styles(app)

    api_client = ApiClient()
    auth_service = AuthService(api_client)
    login_vm = LoginViewModel(auth_service)

    view = LoginView(login_vm)
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
