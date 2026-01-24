import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from src.viewmodels.login_viewmodel import LoginViewModel
from src.views.main_window import MainWindow
from src.components.loading_overlay import LoadingOverlay



class LoginView(QWidget):
    def __init__(self, vm: LoginViewModel):
        super().__init__()
        self.vm = vm

        self.setWindowTitle("SINGDAP")
        self.setMinimumSize(900, 600)

        # ===============================
        # Card container
        # ===============================
        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(360)

        # ===============================
        # Logo
        # ===============================
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, "resources", "images", "logo_gobierno.png")

        pixmap = QPixmap(logo_path)
        self.logo_label.setPixmap(
            pixmap.scaled(
                160,
                80,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        # ===============================
        # Title
        # ===============================
        self.title = QLabel("SINGDAP")
        self.title.setObjectName("title")
        self.title.setAlignment(Qt.AlignCenter)

        self.subtitle = QLabel("Gobierno de Chile")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)

        # ===============================
        # Inputs
        # ===============================
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Email")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)

        # ===============================
        # Buttons
        # ===============================
        self.login_button = QPushButton("Ingreso SSO Ministerial (SAML)")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setDefault(True)


        # ===============================
        # Status
        # ===============================
        self.status_label = QLabel("")
        self.status_label.setObjectName("error")
        self.status_label.setAlignment(Qt.AlignCenter)

        # ===============================
        # Card layout
        # ===============================
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        card_layout.addWidget(self.logo_label)
        card_layout.addWidget(self.title)
        card_layout.addWidget(self.subtitle)
        card_layout.addSpacing(8)

        card_layout.addWidget(self.user_input)
        card_layout.addWidget(self.password_input)

        card_layout.addWidget(self.login_button)

        card_layout.addWidget(self.status_label)

        self.card.setLayout(card_layout)

        # ===============================
        # Main layout (center screen)
        # ===============================
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addWidget(self.card, alignment=Qt.AlignCenter)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # ===============================
        # Signals
        # ===============================
        self.login_button.clicked.connect(self._on_login)

        self.vm.login_success.connect(self._on_success)
        self.vm.login_error.connect(self._on_error)
        self.vm.loading_changed.connect(self._on_loading)

        self.loading_overlay = LoadingOverlay(self)

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    # ===============================
    # Handlers
    # ===============================

    def _on_login(self):
        user = self.user_input.text().strip()
        password = self.password_input.text()

        if not user or not password:
            self._set_error("Debe ingresar usuario y contraseña")
            return

        self.status_label.setText("")
        
        # Mostrar loading inmediatamente
        self.loading_overlay.show_loading()
        
        # Diferir login para permitir renderizado del overlay
        QTimer.singleShot(100, lambda: self.vm.login(user, password))

    def _on_success(self, data: dict):
        access_token = data.get("access_token")

        if not access_token:
            self._set_error("Respuesta de autenticación inválida")
            return

        # Guardar token (provisorio, luego lo mejoramos)
        self.vm.auth_service.api.set_token(access_token)

        # Abrir ventana principal
        self.main_window = MainWindow()
        self.main_window.show()

        # Cerrar login
        self.close()


    def _on_error(self, error: str):
        self._set_error(error)

    def _on_loading(self, loading: bool):
        self.login_button.setEnabled(not loading)
        self.user_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)

        if loading:
            self.loading_overlay.show_loading()
        else:
            self.loading_overlay.hide_loading()

    # ===============================
    # Helpers
    # ===============================

    def _set_error(self, message: str):
        self.status_label.setObjectName("error")
        self.status_label.setText(message)
        self.status_label.style().polish(self.status_label)
