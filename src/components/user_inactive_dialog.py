from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import os

class UserInactiveDialog(QDialog):
    def __init__(self, title="Acceso Inhabilitado", message=None, parent=None):
        super().__init__(parent)

        # Contenido por defecto si no se proporciona
        if message is None:
            message = (
                "<b>Estimada(o) Usuaria(o):</b><br><br>"
                "El acceso al sistema se encuentra inhabilitado para usted en estos momentos.<br><br>"
                "Si usted requiere acceso a la plataforma, debe solicitar la habilitación correspondiente "
                "enviando un correo electrónico a:<br><br>"
                "<span style='color: #0072ce; font-weight: bold;'>📧 gobernanza-datos@desarrollosocial.gob.cl</span><br><br>"
                "En su solicitud indique su nombre, unidad o departamento, y motivo de acceso."
            )

        # ===============================
        # Dialog base
        # ===============================
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(500)
        
        # Main container with border radius and white background (via QSS)
        self.container = QFrame(self)
        self.container.setObjectName("alertDialog")
        self.container.setFixedWidth(480)
        
        # ===============================
        # Icon
        # ===============================
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Base dir relative to this file (src/components/user_inactive_dialog.py)
        # We need to go up one level to src/, then find resources
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "resources", "images", "app.ico")
        icon_label.setPixmap(QIcon(icon_path).pixmap(50, 50))
        icon_label.setObjectName("alertIcon")
        icon_label.setStyleSheet("margin-top: 10px;")

        # ===============================
        # Title
        # ===============================
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("alertTitle")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b;")

        # ===============================
        # Message
        # ===============================
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        message_label.setWordWrap(True)
        message_label.setObjectName("alertMessage")
        message_label.setStyleSheet("font-size: 14px; line-height: 1.6; color: #475569; padding: 10px;")

        # ===============================
        # Buttons
        # ===============================
        confirm_btn = QPushButton("Aceptar")
        confirm_btn.setObjectName("alertConfirm")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setMinimumHeight(45)
        confirm_btn.clicked.connect(self.accept)
        
        confirm_btn.setStyleSheet("""
            QPushButton#alertConfirm {
                background-color: #006FB3;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#alertConfirm:hover {
                background-color: #005fa3;
            }
        """)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(20, 0, 20, 10)
        buttons_layout.addWidget(confirm_btn)

        # ===============================
        # Main layout
        # ===============================
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addLayout(buttons_layout)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container, alignment=Qt.AlignCenter)
        
    def showEvent(self, event):
        # Center dialog relative to parent
        if self.parentWidget():
            parent_geo = self.parentWidget().geometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )
        super().showEvent(event)
