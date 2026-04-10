from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QWidget,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt
import re


class ApiDetailDialog(QDialog):
    def __init__(self, data, title="Detalle de Información", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.resize(1220, 860)
        self.setStyleSheet("background-color: #f4f7fb;")

        # Estado inicial y configuración de datos
        self.current_view_mode = "table"
        self.presentacion = None
        self.raw_payload = data

        if isinstance(data, dict) and "presentacion" in data:
            self.presentacion = data.get("presentacion")
            self.raw_payload = data.get("response_payload")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_header(title)
        self._build_body()
        self._build_footer()
        self._refresh_body()

    def _build_header(self, title):
        header = QFrame()
        header.setFixedHeight(86)
        header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e3e8ef;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(26, 0, 26, 0)
        layout.setSpacing(12)

        text_wrap = QVBoxLayout()
        text_wrap.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #0f172a; font-size: 20px; font-weight: 700;")

        lbl_subtitle = QLabel("Detalle de respuesta con vista tabular o listado")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")

        text_wrap.addWidget(lbl_title)
        text_wrap.addWidget(lbl_subtitle)
        layout.addLayout(text_wrap)
        layout.addStretch()

        self.btn_toggle_view = QPushButton()
        self.btn_toggle_view.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_view.setFixedHeight(36)
        self.btn_toggle_view.clicked.connect(self._toggle_view)
        self.btn_toggle_view.setStyleSheet(
            "QPushButton {"
            "  background-color: #006FB3;"
            "  color: white;"
            "  border: none;"
            "  border-radius: 8px;"
            "  padding: 0 14px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #005fa3; }"
            "QPushButton:disabled { background-color: #9db7c9; }"
        )
        layout.addWidget(self.btn_toggle_view)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(32, 32)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet(
            "QPushButton {"
            "  border: 1px solid #d8e0ea;"
            "  border-radius: 16px;"
            "  background-color: #ffffff;"
            "  color: #64748b;"
            "  font-size: 18px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  background-color: #f1f5f9;"
            "  color: #0f172a;"
            "}"
        )
        layout.addWidget(btn_close)

        self.main_layout.addWidget(header)

    def _build_body(self):
        content_host = QWidget()
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(22, 18, 22, 18)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(2, 2, 2, 2)
        self.body_layout.setSpacing(14)

        self.scroll.setWidget(self.body)
        content_layout.addWidget(self.scroll)
        self.main_layout.addWidget(content_host)

    def _build_footer(self):
        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet("background-color: #ffffff; border-top: 1px solid #e3e8ef;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.addStretch()

        btn = QPushButton("Cerrar")
        btn.setFixedHeight(38)
        btn.setFixedWidth(130)
        btn.clicked.connect(self.accept)
        btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #0f172a;"
            "  color: white;"
            "  border: none;"
            "  border-radius: 8px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #1e293b; }"
        )
        layout.addWidget(btn)

        self.main_layout.addWidget(footer)

    def _refresh_body(self):
        self._clear_body()
        self._update_toggle_button()

        if self.presentacion:
            if self.current_view_mode == "table":
                self._render_canonical_table(self.presentacion)
            else:
                self._render_canonical_list(self.presentacion)
        else:
            if self.current_view_mode == "table":
                self._render_legacy_table(self.raw_payload)
            else:
                self._render_legacy_list(self.raw_payload)

        self.body_layout.addStretch()

    def _toggle_view(self):
        """Alterna entre la vista de tabla y la de listado."""
        self.current_view_mode = "list" if self.current_view_mode == "table" else "table"
        self._refresh_body()

    def _update_toggle_button(self):
        enabled = self._can_toggle_view()
        self.btn_toggle_view.setVisible(enabled)
        self.btn_toggle_view.setEnabled(enabled)
        self.btn_toggle_view.setText("Ver listado" if self.current_view_mode == "table" else "Ver tabla")

    def _can_toggle_view(self):
        if self.presentacion:
            return bool(self.presentacion.get("groups") or self.presentacion.get("table") or self.presentacion.get("collections"))
        payload = self.raw_payload.get("data") if isinstance(self.raw_payload, dict) else self.raw_payload
        return isinstance(payload, (list, dict))

    def _clear_body(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_canonical_table(self, model):
        if model.get("template") == "smart_table":
            self.body_layout.addWidget(self._build_table_section("Resultados", model.get("table")))
            return

        groups = model.get("groups", [])
        if groups:
            self.body_layout.addWidget(self._build_groups_table(groups))

        for section in model.get("collections", []):
            title = f"{section.get('title', 'Registros')} ({section.get('count', 0)})"
            self.body_layout.addWidget(self._build_table_section(title, section.get("table")))

        if not groups and not model.get("collections"):
            self.body_layout.addWidget(self._empty("No hay información para visualizar."))

    def _render_canonical_list(self, model):
        if model.get("template") == "smart_table":
            self.body_layout.addWidget(self._build_list_section("Listado", model.get("table")))
            return

        groups = model.get("groups", [])
        if groups:
            self.body_layout.addWidget(self._build_groups_list(groups))

        for section in model.get("collections", []):
            title = f"{section.get('title', 'Registros')} ({section.get('count', 0)})"
            self.body_layout.addWidget(self._build_list_section(title, section.get("table")))

        if not groups and not model.get("collections"):
            self.body_layout.addWidget(self._empty("No hay información para visualizar."))

    def _render_legacy_table(self, data):
        payload = data.get("data") if isinstance(data, dict) else data

        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            columns = sorted(list({k for row in payload if isinstance(row, dict) for k in row.keys()}))
            table_model = {
                "columns": [{"key": col, "label": self._humanize_label(col)} for col in columns],
                "rows": [{k: self._display(v) for k, v in row.items()} for row in payload],
            }
            self.body_layout.addWidget(self._build_table_section("Contenido", table_model))
            return

        if isinstance(payload, dict) and payload:
            table_model = {
                "columns": [
                    {"key": "campo", "label": "Campo"},
                    {"key": "valor", "label": "Valor"},
                ],
                "rows": [{"campo": self._humanize_label(k), "valor": self._display(v)} for k, v in payload.items()],
            }
            self.body_layout.addWidget(self._build_table_section("Contenido", table_model))
            return

        self.body_layout.addWidget(self._empty("No fue posible estructurar la respuesta para su visualización."))

    def _render_legacy_list(self, data):
        payload = data.get("data") if isinstance(data, dict) else data

        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            columns = sorted(list({k for row in payload if isinstance(row, dict) for k in row.keys()}))
            table_model = {
                "columns": [{"key": col, "label": self._humanize_label(col)} for col in columns],
                "rows": [{k: self._display(v) for k, v in row.items()} for row in payload],
            }
            self.body_layout.addWidget(self._build_list_section("Listado", table_model))
            return

        if isinstance(payload, dict) and payload:
            table_model = {
                "columns": [
                    {"key": "campo", "label": "Campo"},
                    {"key": "valor", "label": "Valor"},
                ],
                "rows": [{"campo": self._humanize_label(k), "valor": self._display(v)} for k, v in payload.items()],
            }
            self.body_layout.addWidget(self._build_list_section("Listado", table_model))
            return

        self.body_layout.addWidget(self._empty("No fue posible estructurar la respuesta para su visualización."))

    def _build_groups_table(self, groups):
        container = self._section_card()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        for group in groups:
            title = QLabel(group.get("title", "Sección"))
            title.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 700;")
            layout.addWidget(title)

            items = group.get("items", [])
            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Campo", "Valor"])
            table.setRowCount(len(items))
            self._configure_resizable_table(table, default_column_width=340)
            table.setSelectionMode(QTableWidget.NoSelection)

            for i, item in enumerate(items):
                field = QTableWidgetItem(item.get("label", ""))
                field.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                value = QTableWidgetItem(self._display(item.get("value", "")))
                value.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(i, 0, field)
                table.setItem(i, 1, value)

            layout.addWidget(table)

        return container

    def _build_groups_list(self, groups):
        container = self._section_card()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        for group in groups:
            title = QLabel(group.get("title", "Sección"))
            title.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 700;")
            layout.addWidget(title)

            block = self._list_block(group.get("items", []), show_title=False)
            layout.addWidget(block)

        return container

    def _build_table_section(self, title, table_model):
        section = self._section_card()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 700;")
        top.addWidget(lbl)

        rows_count = len(table_model.get("rows", [])) if table_model else 0
        badge = QLabel(f"{rows_count} registros")
        badge.setStyleSheet(
            "QLabel {"
            "  color: #334155;"
            "  background-color: #eef3f9;"
            "  border: 1px solid #dde6f0;"
            "  border-radius: 10px;"
            "  padding: 3px 10px;"
            "  font-size: 11px;"
            "  font-weight: 600;"
            "}"
        )
        top.addStretch()
        top.addWidget(badge)
        layout.addLayout(top)

        if not table_model or not table_model.get("columns"):
            layout.addWidget(self._empty("Sin registros para esta sección."))
            return section

        columns = table_model.get("columns", [])
        rows = table_model.get("rows", [])
        max_rows = 200
        rows_to_render = rows[:max_rows]

        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setRowCount(len(rows_to_render))
        table.setHorizontalHeaderLabels([col.get("label", col.get("key", "")) for col in columns])
        self._configure_resizable_table(table)

        for i, row in enumerate(rows_to_render):
            for j, col in enumerate(columns):
                key = col.get("key")
                item = QTableWidgetItem(self._display(row.get(key, "")))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(i, j, item)

        layout.addWidget(table)

        if len(rows) > max_rows:
            info = QLabel(f"Mostrando {max_rows} de {len(rows)} registros.")
            info.setStyleSheet("color: #64748b; font-size: 12px;")
            layout.addWidget(info)

        return section

    def _build_list_section(self, title, table_model):
        section = self._section_card()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(14)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #0f172a; font-size: 14px; font-weight: 700;")
        layout.addWidget(lbl)

        if not table_model or not table_model.get("columns"):
            layout.addWidget(self._empty("Sin registros para esta sección."))
            return section

        columns = table_model.get("columns", [])
        rows = table_model.get("rows", [])

        max_rows = 200
        rows_to_render = rows[:max_rows]

        for idx, row in enumerate(rows_to_render, start=1):
            items = [
                {"label": col.get("label", col.get("key", "")), "value": self._display(row.get(col.get("key"), ""))}
                for col in columns
            ]
            block = self._list_block(items, title=f"Registro {idx}")
            layout.addWidget(block)

        if len(rows) > max_rows:
            info = QLabel(f"Mostrando {max_rows} de {len(rows)} registros.")
            info.setStyleSheet("color: #64748b; font-size: 12px;")
            layout.addWidget(info)

        return section

    def _list_block(self, items, title=None, show_title=True):
        block = QFrame()
        block.setStyleSheet("background-color: #ffffff; border: none;")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        if show_title and title:
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 700;")
            layout.addWidget(title_lbl)

        for idx, item in enumerate(items):
            row = QHBoxLayout()
            row.setSpacing(16)

            lbl_field = QLabel(item.get("label", ""))
            lbl_field.setFixedWidth(300)
            lbl_field.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")

            lbl_value = QLabel(item.get("value", ""))
            lbl_value.setWordWrap(True)
            lbl_value.setStyleSheet("color: #0f172a; font-size: 12px;")

            row.addWidget(lbl_field)
            row.addWidget(lbl_value, 1)
            layout.addLayout(row)

            if idx < len(items) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("color: #f1f5f9; background-color: #f1f5f9; min-height: 1px;")
                layout.addWidget(line)

        return block

    def _section_card(self):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #edf2f7;"
            "  border-radius: 12px;"
            "}"
        )
        return frame

    def _configure_resizable_table(self, table, default_column_width=220):
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideNone)
        table.setShowGrid(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)

        table.setStyleSheet(
            "QTableWidget {"
            "  background-color: #ffffff;"
            "  border: 1px solid #dbe4ee;"
            "  border-radius: 10px;"
            "  gridline-color: transparent;"
            "  alternate-background-color: #f8fbff;"
            "}"
            "QTableWidget::item {"
            "  padding: 8px 10px;"
            "  border-bottom: 1px solid #eef3f8;"
            "  color: #1f2937;"
            "  font-size: 12px;"
            "}"
            "QTableWidget::item:selected {"
            "  background-color: #e6f1fb;"
            "  color: #111827;"
            "}"
            "QHeaderView::section {"
            "  background-color: #f5f8fc;"
            "  color: #334155;"
            "  border: none;"
            "  border-right: 1px solid #e7edf4;"
            "  border-bottom: 1px solid #dbe4ee;"
            "  padding: 9px;"
            "  font-size: 12px;"
            "  font-weight: 700;"
            "}"
        )

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(120)

        for idx in range(table.columnCount()):
            table.setColumnWidth(idx, default_column_width)

    def _display(self, value):
        if value is None:
            return ""
        return str(value)

    def _humanize_label(self, key):
        """Convierte las claves técnicas de la API en nombres legibles para el usuario."""
        normalized = re.sub(r"^(DN_|DG_|CD_|ID_)+", "", str(key).upper())
        tokens = [token for token in normalized.split("_") if token]
        acronyms = {"RUN", "RUT", "DV", "AFC", "CIC", "FCS", "API"}
        words = [token if token in acronyms else token.capitalize() for token in tokens]
        return " ".join(words).strip() or str(key)

    def _empty(self, text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #94a3b8; font-size: 13px; padding: 22px;")
        return label
