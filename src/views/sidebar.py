from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QHBoxLayout,
    QFrame,
    QDialog,
    QApplication,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap

from src.core.api_client import ApiClient
from src.components.alert_dialog import AlertDialog
from src.services.cache_manager import CacheManager
from src.services.permission_service import PermissionService
from utils import icon, resource_path


class Sidebar(QWidget):
    logout_requested = Signal()
    home_requested = Signal()
    def __init__(self):
        super().__init__()

        # ===============================
        # Configuración
        # ===============================
        self.expanded_width = 256
        self.collapsed_width = 64
        self.is_collapsed = False

        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.expanded_width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self.expanded_width)

        # ===============================
        # Logo (arriba, centrado)
        # ===============================
        self.logo = QLabel()
        self.logo.setObjectName("sidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setCursor(Qt.PointingHandCursor)
        self.logo.mousePressEvent = lambda _: self.home_requested.emit()

        logo_path = resource_path("src/resources/images/logo_gobierno.png")
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            self.logo.setPixmap(
                pixmap.scaledToWidth(
                    100,
                    Qt.SmoothTransformation
                )
            )

        self.logo_container = QFrame()
        self.logo_container.setObjectName("sidebarLogoContainer")
        self.logo_container.setAttribute(Qt.WA_StyledBackground, True)
        self.logo_container.setStyleSheet("background-color: #ffffff;")
        logo_container_layout = QVBoxLayout(self.logo_container)
        logo_container_layout.setContentsMargins(12, 16, 12, 16)
        logo_container_layout.addWidget(self.logo)

        # ===============================
        # Toggle + Title
        # ===============================
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("sidebarToggle")
        self.toggle_btn.setFixedSize(36, 36)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)

        self.title = QLabel("SINGDAP")
        self.title.setObjectName("sidebarTitle")
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(self.title)
        title_row.addStretch()
        title_row.addWidget(self.toggle_btn)

        # ===============================
        # Navigation buttons
        # ===============================
        self.btn_home = self._nav_button(
            "Inicio",
            "src/resources/icons/home_white.svg",
            active=True,
        )

        self.btn_inventario = self._nav_button(
            "Inventario",
            "src/resources/icons/inventory.svg",
            active=False,
        )

        self.btn_rat = self._nav_button(
            "RAT",
            "src/resources/icons/file.svg",
        )

        self.btn_eipd = self._nav_button(
            "EIPD (Ex PIA)",
            "src/resources/icons/shield.svg",
        )

        self.btn_seguimiento = self._nav_button(
            "Seguimiento de riesgos",
            "src/resources/icons/alert_warning_white.svg",
        )

        self.btn_trazabilidad = self._nav_button(
            "Trazabilidad por Ciudadano",
            "src/resources/icons/search_white.svg",
        )

        self.btn_roles = self._nav_button(
            "Usuarios / Roles",
            "src/resources/icons/users.svg",
        )

        self.btn_dashboard = self._nav_button(
            "Reportes",
            "src/resources/icons/dashboard.svg",
        )

        self.btn_auditoria = self._nav_button(
            "Auditoría",
            "src/resources/icons/maintainers.svg",
        )

        self.nav_buttons = [
            self.btn_home,
            self.btn_inventario,
            self.btn_rat,
            self.btn_eipd,
            self.btn_seguimiento,
            self.btn_trazabilidad,
            self.btn_roles,
            self.btn_dashboard,
            self.btn_auditoria,
        ]
        
        # ===============================
        # Permission Filtering
        # ===============================
        perm_service = PermissionService()
        self.btn_dashboard.setVisible(perm_service.has_module_access("DASHBOARD"))
        self.btn_inventario.setVisible(perm_service.has_module_access("INVENTARIO"))
        self.btn_rat.setVisible(perm_service.has_module_access("RAT"))
        self.btn_eipd.setVisible(perm_service.has_module_access("EIPD"))
        self.btn_seguimiento.setVisible(perm_service.has_module_access("SEGUIMIENTO"))
        self.btn_trazabilidad.setVisible(perm_service.has_module_access("TRAZABILIDAD"))
        self.btn_auditoria.setVisible(perm_service.has_module_access("AUDITORIA"))

        # Gestión de Usuarios / Roles basada en permisos
        self.btn_roles.setVisible(perm_service.has_module_access("USUARIOS"))

        # ===============================
        # Logout
        # ===============================
        self.logout_btn = QPushButton("Cerrar sesión")
        self.logout_btn.setObjectName("sidebarLogout")
        self.logout_btn.setIcon(icon("src/resources/icons/logout.svg"))
        self.logout_btn.setIconSize(QSize(18, 18))
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setProperty("fullText", "Cerrar sesión")
        self.logout_btn.setToolTip("Cerrar sesión")
        self.logout_btn.clicked.connect(self.on_logout)

        # ===============================
        # Layout principal
        # ===============================
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(0)

        # Logo: ocupa el ancho completo del sidebar
        layout.addWidget(self.logo_container)

        # Contenido con márgenes laterales
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 0)
        content_layout.setSpacing(10)

        content_layout.addSpacing(4)
        content_layout.addLayout(title_row)
        content_layout.addSpacing(24)

        for btn in self.nav_buttons:
            content_layout.addWidget(btn)

        content_layout.addStretch()
        content_layout.addWidget(self.logout_btn)

        layout.addLayout(content_layout)

    # ===============================
    # Nav button helper
    # ===============================
    def _nav_button(self, text, icon_path, active=False):
        btn = QPushButton(text)
        btn.setIcon(icon(icon_path))
        btn.setIconSize(QSize(18, 18))
        btn.setCursor(Qt.PointingHandCursor)

        btn.setObjectName(
            "sidebarItemActive" if active else "sidebarItem"
        )
        btn.setProperty("fullText", text)
        btn.setToolTip(text)

        return btn

    # ===============================
    # Toggle sidebar
    # ===============================
    def toggle(self):
        self.is_collapsed = not self.is_collapsed
        target_width = (
            self.collapsed_width if self.is_collapsed else self.expanded_width
        )
        self.setFixedWidth(target_width)
        self._update_visibility()

    # ===============================
    # Update visibility
    # ===============================
    def _update_visibility(self):
        show_text = not self.is_collapsed

        self.logo_container.setVisible(show_text)
        self.title.setVisible(show_text)

        for btn in self.nav_buttons:
            btn.setText(btn.property("fullText") if show_text else "")

        self.logout_btn.setText(
            self.logout_btn.property("fullText") if show_text else ""
        )

    # ===============================
    # Logout action
    # ===============================
    def on_logout(self):
        dialog = AlertDialog(
            title="Cerrar sesión",
            message="¿Estás seguro que deseas cerrar sesión?",
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Cerrar sesión",
            cancel_text="Cancelar",
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            # Clear cache on logout
            try:
                CacheManager().clear()
                api = ApiClient()
                api.clear_session()
    
            except Exception:
                pass
            self.logout_requested.emit()

    def set_active(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName(
                "sidebarItemActive" if i == index else "sidebarItem"
            )
            btn.style().unpolish(btn)
            btn.style().polish(btn)
