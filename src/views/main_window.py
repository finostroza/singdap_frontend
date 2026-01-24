from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
)
from PySide6.QtCore import Signal

from src.views.sidebar import Sidebar
from src.views.activos.activos_view import ActivosView
from src.views.mantenedores.mantenedores_view import MantenedoresView
from src.views.usuarios.usuarios_view import UsuariosView
from src.views.eipd.eipd_view import EipdView


class MainWindow(QMainWindow):
    logout_signal = Signal()
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SINGDAP - Sistema de Inventario")
        self.setMinimumSize(1200, 720)

        # ===============================
        # Container principal
        # ===============================
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===============================
        # Sidebar
        # ===============================
        self.sidebar = Sidebar()

        # ===============================
        # Stack de vistas
        # ===============================
        self.stack = QStackedWidget()

        self.activos_view = ActivosView()
        self.mantenedores_view = MantenedoresView()
        self.usuarios_view = UsuariosView()
        self.eipd_view = EipdView()

        # Stack indexes
        self.stack.addWidget(self.activos_view)        # 0
        self.stack.addWidget(self.mantenedores_view)   # 1
        self.stack.addWidget(self.usuarios_view)       # 2
        self.stack.addWidget(self.eipd_view)           # 3

        # ===============================
        # Layout
        # ===============================
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack)

        layout.setStretch(0, 0)  # sidebar fijo
        layout.setStretch(1, 1)  # contenido flexible

        container.setLayout(layout)
        self.setCentralWidget(container)

        # ===============================
        # Navegación (ALINEADA AL SIDEBAR)
        # ===============================
        self.sidebar.btn_inventario.clicked.connect(
            lambda: self._navigate(0, 0)
        )

        self.sidebar.btn_mantenedores.clicked.connect(
            lambda: self._navigate(1, 1)
        )

        # EIPD (sidebar index 2)
        self.sidebar.btn_eipd.clicked.connect(
            lambda: self._navigate(3, 2)
        )

        # Usuarios / Roles (sidebar index 3)
        self.sidebar.btn_roles.clicked.connect(
            lambda: self._navigate(2, 3)
        )

        # ===============================
        # Estado inicial
        # ===============================
        self._navigate(0, 0)
        
        self.sidebar.logout_requested.connect(self._on_logout_requested)

    def _on_logout_requested(self):
        self.close()
        self.logout_signal.emit()

    # ======================================================
    # Navigation handler
    # ======================================================

    def _navigate(self, stack_index: int, sidebar_index: int):
        self.stack.setCurrentIndex(stack_index)
        self.sidebar.set_active(sidebar_index)
