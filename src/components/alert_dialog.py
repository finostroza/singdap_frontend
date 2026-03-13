from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class AlertDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        icon_path: str,
        confirm_text="Confirmar",
        cancel_text="Cancelar",
        parent=None
    ):
        super().__init__(parent)

        # ===============================
        # Dialog base
        # ===============================
        self.setModal(True)
        self.setWindowTitle(title)
        self.setFixedWidth(420)
        self.setObjectName("alertDialog")

        # ===============================
        # Icon
        # ===============================
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(QIcon(icon_path).pixmap(40, 40))
        icon_label.setObjectName("alertIcon")

        # ===============================
        # Title
        # ===============================
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("alertTitle")

        # ===============================
        # Message
        # ===============================
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setObjectName("alertMessage")

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.addStretch()
        
        if cancel_text:
            cancel_btn = QPushButton(cancel_text)
            cancel_btn.setObjectName("alertCancel")
            cancel_btn.clicked.connect(self.reject)
            buttons_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName("alertConfirm")
        confirm_btn.clicked.connect(self.accept)
        
        buttons_layout.addWidget(confirm_btn)
        buttons_layout.addStretch()

        # ===============================
        # Main layout
        # ===============================
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addSpacing(8)
        layout.addLayout(buttons_layout)
