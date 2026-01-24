from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from src.components.loading_overlay import LoadingOverlay


class UsuariosView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

        # ===============================
        # Header
        # ===============================
        title = QLabel("SINGDAP · Módulo Usuarios")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Perfil habilita módulo · Rol define función · Privilegio autoriza acción"
        )
        subtitle.setObjectName("pageSubtitle")

        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(subtitle)

        # ===============================
        # Tabs
        # ===============================
        tabs_layout = QHBoxLayout()

        self.tab_users = QPushButton("Usuarios")
        self.tab_users.setObjectName("tabActive")

        self.tab_packs = QPushButton("Packs de Acceso")
        self.tab_packs.setObjectName("tab")

        self.tab_audit = QPushButton("Auditoría")
        self.tab_audit.setObjectName("tab")

        tabs_layout.addWidget(self.tab_users)
        tabs_layout.addWidget(self.tab_packs)
        tabs_layout.addWidget(self.tab_audit)
        tabs_layout.addStretch()

        # ===============================
        # Main content (3 columns)
        # ===============================
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        content_layout.addWidget(self._users_list_card(), 1)
        content_layout.addWidget(self._detail_card(), 1)
        content_layout.addWidget(self._matrix_card(), 1)

        # ===============================
        # Layout
        # ===============================
        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(tabs_layout)
        layout.addSpacing(8)
        layout.addLayout(content_layout)
        layout.addStretch()

    # ======================================================
    # Card: Users list
    # ======================================================

    def _users_list_card(self):
        card = QFrame()
        card.setObjectName("card")

        title = QLabel("Usuarios")
        title.setObjectName("cardTitle")

        search = QLineEdit()
        search.setPlaceholderText("Buscar (nombre, mail, id…)")

        users = QListWidget()
        users.setObjectName("userList")

        for name in [
            "Héctor Poblete",
            "María González",
            "Carlos Rivas",
            "Ana Torres",
            "Jorge Muñoz",
        ]:
            users.addItem(self._user_item(name))

        layout = QVBoxLayout(card)
        layout.addWidget(title)
        layout.addWidget(search)
        layout.addWidget(users)

        return card

    def _user_item(self, name):
        item = QListWidgetItem(name)
        item.setToolTip("Usuario")
        return item

    # ======================================================
    # Card: Detail + Packs
    # ======================================================

    def _detail_card(self):
        card = QFrame()
        card.setObjectName("card")

        header = QHBoxLayout()
        title = QLabel("Detalle y asignación")
        title.setObjectName("cardTitle")

        status = QLabel("Activo")
        status.setObjectName("statusActive")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(status)

        user_name = QLabel("Héctor Poblete")
        user_name.setObjectName("sectionTitle")

        email = QLabel("hector.poblete@ministerio.cl")
        email.setObjectName("mutedText")

        packs_title = QLabel("Packs disponibles")
        packs_title.setObjectName("sectionTitle")

        packs = QVBoxLayout()
        packs.addWidget(self._pack_card("PACK Admin Sistema", "Asignado"))
        packs.addWidget(self._pack_card("PACK Gestor Usuarios", "Asignar"))
        packs.addWidget(self._pack_card("PACK Custodio Inventario", "Asignar"))
        packs.addWidget(self._pack_card("PACK Auditor Global", "Asignar"))

        layout = QVBoxLayout(card)
        layout.addLayout(header)
        layout.addWidget(user_name)
        layout.addWidget(email)
        layout.addSpacing(8)
        layout.addWidget(packs_title)
        layout.addLayout(packs)
        layout.addStretch()

        return card

    def _pack_card(self, name, action):
        frame = QFrame()
        frame.setObjectName("packCard")

        title = QLabel(name)
        title.setObjectName("packTitle")

        btn = QPushButton(action)
        btn.setObjectName(
            "primaryButtonSmall" if action == "Asignado" else "secondaryButtonSmall"
        )

        layout = QHBoxLayout(frame)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(btn)

        return frame

    # ======================================================
    # Card: Matrix
    # ======================================================

    def _matrix_card(self):
        card = QFrame()
        card.setObjectName("card")

        title = QLabel("Matriz efectiva por módulos")
        title.setObjectName("cardTitle")

        table = QTableWidget(8, 4)
        table.setHorizontalHeaderLabels(["Módulo", "View", "Create", "Edit"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )

        modules = [
            "Inventario de Activos",
            "RAT",
            "PIA / EIPD",
            "Trazabilidad",
            "Solicitudes",
            "Auditoría",
            "Mantenedores",
            "Usuarios",
        ]

        for row, module in enumerate(modules):
            table.setItem(row, 0, QTableWidgetItem(module))
            for col in range(1, 4):
                table.setItem(row, col, QTableWidgetItem("✓"))

        layout = QVBoxLayout(card)
        layout.addWidget(title)
        layout.addWidget(table)

        return card
