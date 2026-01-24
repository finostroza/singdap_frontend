from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QHBoxLayout,
    QDialog,
    QApplication,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QSize, QEasingCurve, Signal
from PySide6.QtGui import QPixmap

from src.components.alert_dialog import AlertDialog
from src.services.cache_manager import CacheManager
from utils import icon, resource_path


class Sidebar(QWidget):
    logout_requested = Signal()
    def __init__(self):
        super().__init__()

        # ===============================
        # Configuración
        # ===============================
        self.expanded_width = 280
        self.collapsed_width = 64
        self.is_collapsed = False

        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.expanded_width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # ===============================
        # Logo (arriba, centrado)
        # ===============================
        self.logo = QLabel()
        self.logo.setObjectName("sidebarLogo")
        self.logo.setAlignment(Qt.AlignCenter)

        logo_path = resource_path("src/resources/images/logo_gobierno.png")
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            self.logo.setPixmap(
                pixmap.scaledToWidth(
                    100,
                    Qt.SmoothTransformation
                )
            )

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
        self.btn_inventario = self._nav_button(
            "Inventario",
            "src/resources/icons/inventory.svg",
            active=True,
        )

        self.btn_mantenedores = self._nav_button(
            "Mantenedores",
            "src/resources/icons/maintainers.svg",
        )

        self.btn_eipd = self._nav_button(
            "EIPD (Ex PIA)",
            "src/resources/icons/shield.svg",
        )

        self.btn_roles = self._nav_button(
            "Usuarios / Roles",
            "src/resources/icons/users.svg",
        )

        self.btn_rat = self._nav_button(
            "RAT",
            "src/resources/icons/file.svg",
        )

        self.nav_buttons = [
            self.btn_inventario,
            self.btn_mantenedores,
            self.btn_eipd,
            self.btn_roles,
            self.btn_rat,
        ]

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
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(10)

        layout.addWidget(self.logo)
        layout.addSpacing(8)
        layout.addLayout(title_row)
        layout.addSpacing(24)

        for btn in self.nav_buttons:
            layout.addWidget(btn)

        layout.addStretch()
        layout.addWidget(self.logout_btn)

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
        start = self.width()
        end = (
            self.collapsed_width
            if not self.is_collapsed
            else self.expanded_width
        )

        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(220)
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(self._update_visibility)

        self.is_collapsed = not self.is_collapsed
        self.animation.start()

    # ===============================
    # Update visibility
    # ===============================
    def _update_visibility(self):
        show_text = not self.is_collapsed

        self.logo.setVisible(show_text)
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
