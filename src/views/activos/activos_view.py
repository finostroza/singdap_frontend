from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QComboBox,
    QFrame, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QDateTime, QLocale
from src.components.activo_dialog import ActivoDialog
from src.components.alert_dialog import AlertDialog
from src.core.api_client import ApiClient
from utils import icon
from src.components.loading_overlay import LoadingOverlay


class ActivosView(QWidget):
    def __init__(self):
        super().__init__()

        # ===============================
        # API
        # ===============================
        self.api = ApiClient()

        # ===============================
        # Pagination
        # ===============================
        self.current_page = 1
        self.page_size = 7
        self.total_pages = 1

        # ===============================
        # Header user
        # ===============================
        self.user_label = QLabel("Felipe Inostroza")
        self.user_label.setObjectName("topUser")

        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("topDatetime")

        user_box = QVBoxLayout()
        user_box.addWidget(self.user_label)
        user_box.addWidget(self.datetime_label)

        self._update_datetime()
        self._start_datetime_timer()

        # ===============================
        # Title
        # ===============================
        title = QLabel("Inventario de Activos de Datos")
        title.setObjectName("pageTitle")

        header_top = QHBoxLayout()
        header_top.addWidget(title)
        header_top.addStretch()
        header_top.addLayout(user_box)

        # ===============================
        # Stats
        # ===============================
        self.total_card = self._stat_card("Total Activos", "0")
        self.sensibles_card = self._stat_card("Con datos sensibles", "0")
        self.eipd_card = self._stat_card("EIPD pendiente", "0")
        self.confid_card = self._stat_card("Confid. Reservado", "0")

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        stats_layout.addWidget(self.total_card)
        stats_layout.addWidget(self.sensibles_card)
        stats_layout.addWidget(self.eipd_card)
        stats_layout.addWidget(self.confid_card)

        # ===============================
        # Filters
        # ===============================
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o ID…")
        self.search_input.returnPressed.connect(self._on_search)

        search_action = self.search_input.addAction(
            icon("src/resources/icons/search.svg"),
            QLineEdit.TrailingPosition
        )
        search_action.setToolTip("Buscar")
        search_action.triggered.connect(self._on_search)

        self.subsecretaria_filter = QComboBox()
        self.tipo_filter = QComboBox()
        self.eipd_filter = QComboBox()

        self.subsecretaria_filter.currentIndexChanged.connect(self._on_filter_change)
        self.tipo_filter.currentIndexChanged.connect(self._on_filter_change)
        self.eipd_filter.currentIndexChanged.connect(self._on_filter_change)

        self.clear_filters_btn = QPushButton("Limpiar filtros")
        self.clear_filters_btn.setObjectName("secondaryButton")
        self.clear_filters_btn.clicked.connect(self._clear_filters)

        self.new_button = QPushButton("+ Nuevo")
        self.new_button.setObjectName("primaryButton")
        self.new_button.clicked.connect(self.open_new_activo)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(self.subsecretaria_filter)
        filters_layout.addWidget(self.tipo_filter)
        filters_layout.addWidget(self.eipd_filter)
        filters_layout.addWidget(self.clear_filters_btn)
        filters_layout.addStretch()
        filters_layout.addWidget(self.new_button)

        # ===============================
        # Table
        # ===============================
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Tipo", "Estado",
            "Subsecretaría", "División",
            "Confid.", "EIPD", "Acciones"
        ])

        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 96)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.setMinimumHeight(40 + (7 * 44))
        self.table.setMaximumHeight(40 + (7 * 44))

        # ===============================
        # Pagination
        # ===============================
        self.prev_btn = QPushButton("⟨ Anterior")
        self.prev_btn.clicked.connect(self._prev_page)

        self.page_label = QLabel()

        self.next_btn = QPushButton("Siguiente ⟩")
        self.next_btn.clicked.connect(self._next_page)

        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()

        # ===============================
        # Layout
        # ===============================
        layout = QVBoxLayout(self)
        layout.addLayout(header_top)
        layout.addLayout(stats_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.table)
        layout.addLayout(pagination_layout)
        layout.addStretch()

        # ===============================
        # Initial load
        # ===============================
        self.loading_overlay = LoadingOverlay(self)  # Initialize Overlay

        self._load_filters_from_api()
        self._reload_all()

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    # ======================================================
    # Helpers
    # ======================================================

    def _stat_card(self, title, value):
        card = QFrame()
        card.setObjectName("statCard")

        t = QLabel(title)
        t.setObjectName("statTitle")

        v = QLabel(value)
        v.setObjectName("statValue")

        layout = QVBoxLayout(card)
        layout.addWidget(t)
        layout.addWidget(v)

        card.value_label = v
        return card

    def _update_datetime(self):
        locale = QLocale(QLocale.Spanish, QLocale.Chile)
        now = QDateTime.currentDateTime()
        self.datetime_label.setText(
            f"{locale.toString(now.date(), 'dddd d MMMM yyyy')} · {now.toString('HH:mm')}"
        )

    def _start_datetime_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_datetime)
        self._timer.start(1000)

    # ======================================================
    # Filters
    # ======================================================

    def _load_filters_from_api(self):
        self._load_combo(self.subsecretaria_filter, "/setup/subsecretarias", "Todas las Subsecretarías")
        self._load_combo(self.tipo_filter, "/catalogos/tipo-activo", "Todos los tipos")
        self._load_combo(self.eipd_filter, "/catalogos/estado-evaluacion", "Estado EIPD: Todos")

    def _load_combo(self, combo, endpoint, default):
        combo.clear()
        combo.addItem(default, None)
        for item in self.api.get(endpoint):
            combo.addItem(item["nombre"], item["id"])

    def _clear_filters(self):
        self.search_input.clear()
        self.subsecretaria_filter.setCurrentIndex(0)
        self.tipo_filter.setCurrentIndex(0)
        self.eipd_filter.setCurrentIndex(0)
        self.current_page = 1
        self._reload_all()

    def _on_search(self):
        self.current_page = 1
        self._reload_all()

    def _on_filter_change(self):
        self.current_page = 1
        self._reload_all()

    # ======================================================
    # Data
    # ======================================================

    def _reload_all(self):
        self.loading_overlay.show_loading()
        # Pequeño delay para permitir que la UI renderice el overlay antes de bloquear con requests
        QTimer.singleShot(100, self._execute_reload)

    def _execute_reload(self):
        try:
            self._load_activos_from_api()
            self._load_indicadores()
        finally:
            self.loading_overlay.hide_loading()

    def _load_activos_from_api(self):
        url = f"/activos/catalogos?page={self.current_page}&size={self.page_size}"

        if self.search_input.text():
            url += f"&search={self.search_input.text()}"

        if self.subsecretaria_filter.currentData():
            url += f"&subsecretaria_id={self.subsecretaria_filter.currentData()}"

        if self.tipo_filter.currentData():
            url += f"&tipo_activo_id={self.tipo_filter.currentData()}"

        if self.eipd_filter.currentData():
            url += f"&estado_evaluacion_id={self.eipd_filter.currentData()}"

        response = self.api.get(url)
        items = response["items"]
        self.total_pages = response["pages"]

        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            values = [
                item["codigo_activo"],
                item["nombre_activo"],
                item["tipo_activo"],
                item["estado_activo"],
                item["subsecretaria"],
                item.get("division") or "—",
                item.get("nivel_confidencialidad") or "—",
                item.get("categoria") or "—",
            ]

            for col, val in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(val)))

            self._add_actions(row, item["activo_id"])

        self.page_label.setText(f"Página {self.current_page} de {self.total_pages}")

    def _load_indicadores(self):
        data = self.api.get("/activos/indicadores")
        self.total_card.value_label.setText(str(data["total_activos"]))
        self.sensibles_card.value_label.setText(str(data["confidencial"]))
        self.eipd_card.value_label.setText(str(data["eipd_pendiente"]))
        self.confid_card.value_label.setText(str(data["confidencial"]))

    # ======================================================
    # Actions
    # ======================================================

    def _add_actions(self, row, activo_id):
        edit_btn = QPushButton()
        edit_btn.setIcon(icon("src/resources/icons/edit.svg"))
        edit_btn.clicked.connect(lambda: self._edit_activo(activo_id))

        delete_btn = QPushButton()
        delete_btn.setIcon(icon("src/resources/icons/delete.svg"))
        delete_btn.clicked.connect(lambda: self._delete_activo(activo_id))

        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignCenter)
        l.addWidget(edit_btn)
        l.addWidget(delete_btn)

        self.table.setCellWidget(row, 8, w)

    def _edit_activo(self, activo_id):
        dialog = ActivoDialog(self, activo_id=activo_id)
        if dialog.exec():
            self._reload_all()

    def _delete_activo(self, activo_id):
        confirm = AlertDialog(
            title="Eliminar activo",
            message="¿Deseas eliminar este activo?",
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Eliminar",
            cancel_text="Cancelar",
            parent=self
        )
        if confirm.exec():
            self.api.delete(f"/activos/{activo_id}")
            self._reload_all()

    # ======================================================
    # Pagination
    # ======================================================

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._load_activos_from_api()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_activos_from_api()

    # ======================================================
    # Dialog
    # ======================================================

    def open_new_activo(self):
        dialog = ActivoDialog(self)
        if dialog.exec():
            self._reload_all()
