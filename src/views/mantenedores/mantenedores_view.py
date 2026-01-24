from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QGridLayout, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.core.api_client import ApiClient
from src.components.loading_overlay import LoadingOverlay


class MantenedoresView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

        self.api = ApiClient()

        # ===============================
        # Title
        # ===============================
        title = QLabel("Mantenedores")
        title.setObjectName("pageTitle")

        subtitle = QLabel("CRUD genérico de catálogos (valores para selects)")
        subtitle.setObjectName("pageSubtitle")

        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(subtitle)

        # ===============================
        # Cards grid
        # ===============================
        grid = QGridLayout()
        grid.setSpacing(16)

        self.cards = [
            self._catalog_card("Subsecretarías", "/setup/subsecretarias"),
            self._catalog_card("Divisiones / Departamentos", "/setup/divisiones"),
            self._catalog_card("Tipos de Activo", "/catalogos/tipo-activo"),
            self._catalog_card("Confidencialidad", "/catalogos/confidencialidad"),
            self._catalog_card("Categoría de Datos Personales", "/catalogos/categoria-datos"),
            self._catalog_card("Base de legitimación", "/catalogos/base-legitimacion"),
        ]

        for i, card in enumerate(self.cards):
            grid.addWidget(card, i // 3, i % 3)

        grid_container = QWidget()
        grid_container.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_container)
        scroll.setFrameShape(QFrame.NoFrame)

        # ===============================
        # Layout
        # ===============================
        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(scroll)
        layout.addStretch()

    # ======================================================
    # Card builder
    # ======================================================

    def _catalog_card(self, title_text, endpoint):
        card = QFrame()
        card.setObjectName("catalogCard")

        # Header
        title = QLabel(title_text)
        title.setObjectName("cardTitle")

        add_btn = QPushButton("Agregar")
        add_btn.setObjectName("primaryButtonSmall")
        add_btn.clicked.connect(lambda: self._add_item(endpoint))

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(add_btn)

        # Search
        search = QLineEdit()
        search.setPlaceholderText("Buscar…")

        search_action = search.addAction(
            QIcon("src/resources/icons/search.svg"),
            QLineEdit.TrailingPosition
        )

        # List
        list_widget = QListWidget()
        list_widget.setObjectName("catalogList")

        # Dummy data (hasta conectar API)
        for name in ["Ejemplo 1", "Ejemplo 2", "Ejemplo 3"]:
            list_widget.addItem(self._catalog_item(name))

        search.textChanged.connect(
            lambda text: self._filter_list(list_widget, text)
        )

        # Layout
        layout = QVBoxLayout(card)
        layout.addLayout(header)
        layout.addWidget(search)
        layout.addWidget(list_widget)

        return card

    # ======================================================
    # List item
    # ======================================================

    def _catalog_item(self, text):
        item = QListWidgetItem(text)
        return item

    def _filter_list(self, list_widget, text):
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ======================================================
    # Actions (placeholders)
    # ======================================================

    def _add_item(self, endpoint):
        print(f"Agregar en {endpoint}")
        # TODO: abrir dialog genérico

    def _edit_item(self, item_id, endpoint):
        print(f"Editar {item_id} en {endpoint}")

    def _delete_item(self, item_id, endpoint):
        print(f"Eliminar {item_id} en {endpoint}")
