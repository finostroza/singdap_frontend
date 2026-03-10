from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from src.services.permission_service import PermissionService

class SeguimientoRiesgosView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Seguimiento de Riesgos")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        
        subtitle = QLabel("Modulo en desarrollo - Seguimiento de Riesgos de RAT y EIPD")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setStyleSheet("font-size: 16px; color: #666;")
        
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
        
        # 🛡️ Control de Acceso
        self.permission_service = PermissionService()
        if not self.permission_service.has_module_access("SEGUIMIENTO"):
             self._show_permission_block()

    def _show_permission_block(self):
        overlay = QFrame(self)
        overlay.setObjectName("permissionBlockOverlay")
        overlay.setStyleSheet("background-color: transparent;")
        
        l = QVBoxLayout(overlay)
        l.setAlignment(Qt.AlignCenter)
        
        from utils import icon
        icon_label = QLabel()
        icon_label.setPixmap(icon("src/resources/icons/lock.svg").pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        
        msg_label = QLabel("Acceso denegado a Seguimiento de Riesgos.")
        msg_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #64748b;")
        msg_label.setAlignment(Qt.AlignCenter)
        
        l.addWidget(icon_label)
        l.addWidget(msg_label)
        overlay.show()
        
        self.layout().addWidget(overlay)
