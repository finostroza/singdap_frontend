from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
)
from PySide6.QtCore import Signal

from src.views.sidebar import Sidebar
from src.views.activos.activos_view import ActivosView
from src.views.usuarios.usuarios_view import UsuariosView
from src.views.eipd.eipd_view import EipdView
from src.views.rat.rat_view import RatView
from src.views.trazabilidad.trazabilidad_view import TrazabilidadView
from src.views.dashboard.dashboard_view import DashboardView
from src.viewmodels.dashboard_viewmodel import DashboardViewModel
from src.views.seguimiento.seguimiento_riesgos_view import SeguimientoRiesgosView
from src.services.permission_service import PermissionService
from src.views.home.home_view import HomeView


class MainWindow(QMainWindow):
    logout_signal = Signal()
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SINGDAP- Sistema de Inventario y Gestión de Datos Personales")
        self.setMinimumSize(1500, 768)
        self.resize(1600, 900)

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

        from src.viewmodels.seguimiento_viewmodel import SeguimientoViewModel
        
        self.home_view = HomeView()
        self.activos_view = ActivosView()
        self.rat_view = RatView()
        self.eipd_view = EipdView()
        self.seguimiento_view = SeguimientoRiesgosView(SeguimientoViewModel())
        self.trazabilidad_view = TrazabilidadView()
        self.usuarios_view = UsuariosView()
        self.dashboard_view = DashboardView(DashboardViewModel())

        # Stack indexes (Matching Sidebar order)
        self.stack.addWidget(self.home_view)           # 0
        self.stack.addWidget(self.activos_view)        # 1
        self.stack.addWidget(self.rat_view)            # 2
        self.stack.addWidget(self.eipd_view)           # 3
        self.stack.addWidget(self.seguimiento_view)    # 4
        self.stack.addWidget(self.trazabilidad_view)   # 5
        self.stack.addWidget(self.usuarios_view)       # 6
        self.stack.addWidget(self.dashboard_view)      # 7

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
        self.sidebar.home_requested.connect(
            lambda: self._navigate(0, 0)
        )

        self.sidebar.btn_home.clicked.connect(
            lambda: self._navigate(0, 0)
        )

        self.sidebar.btn_inventario.clicked.connect(
            lambda: self._navigate(1, 1)
        )

        self.sidebar.btn_rat.clicked.connect(
            lambda: self._navigate(2, 2)
        )

        self.sidebar.btn_eipd.clicked.connect(
            lambda: self._navigate(3, 3)
        )

        self.sidebar.btn_seguimiento.clicked.connect(
            lambda: self._navigate(4, 4)
        )

        self.sidebar.btn_trazabilidad.clicked.connect(
            lambda: self._navigate(5, 5)
        )

        self.sidebar.btn_roles.clicked.connect(
            lambda: self._navigate(6, 6)
        )

        self.sidebar.btn_dashboard.clicked.connect(
            lambda: self._navigate(7, 7)
        )

        # ===============================
        # Estado inicial
        # ===============================
        perm_service = PermissionService()
        # Home es la vista por defecto ahora
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
