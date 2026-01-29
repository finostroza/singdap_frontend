import json
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QComboBox,
    QFrame, QHeaderView, QMenu, QFileDialog
)
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
import csv
from PySide6.QtCore import Qt, QTimer, QDateTime, QLocale, QThreadPool

from src.core.api_client import ApiClient
from src.services.catalogo_service import CatalogoService
from src.services.logger_service import LoggerService
from src.workers.api_worker import ApiWorker
from src.workers.combo_loader import ComboLoaderRunnable
from src.components.alert_dialog import AlertDialog
from src.components.loading_overlay import LoadingOverlay
from src.components.dialog_registry import get_dialog_class
from utils import icon

class GenericGridView(QWidget):
    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Services
        self.api = ApiClient()
        self.catalogo_service = CatalogoService()
        self.thread_pool = QThreadPool.globalInstance()
        self._active_runnables = [] # Prevent GC
        
        # Pagination
        self.current_page = 1
        self.page_size = self.config.get("paginacion", {}).get("tamano_pagina", 10)
        self.total_pages = 1
        
        # UI Elements Storage (for later access)
        self.filters_ui = {} # Map filter_id -> QComboBox
        self.indicators_ui = {} # Map indicator field -> QLabel value
        
        # Build UI
        self._build_ui()
        
        # Overlay
        self.loading_overlay = LoadingOverlay(self)
        
        # Initial Load
        QTimer.singleShot(0, self._init_async_filters)
        
        LoggerService().log_event(f"Usuario accedió a {self.config.get('titulo', 'Vista Genérica')}")
        self._reload_all()

    def _load_config(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    # ======================================================
    # UI Builder
    # ======================================================

    def _build_ui(self):
        # Layout
        layout = QVBoxLayout(self)
        
        # 1. Header (Title + User/Date)
        header_top = QHBoxLayout()
        
        title = QLabel(self.config.get("titulo", ""))
        title.setObjectName("pageTitle")
        header_top.addWidget(title)
        header_top.addStretch()
        
        # User/Date Box (Preserving existing functionality)
        # In a purely generic component, this might be injected or optional,
        # but for now we hardcode it as per "Maintain functionality".
        self.user_label = QLabel("Felipe Inostroza") # Placeholder/Hardcoded in original
        self.user_label.setObjectName("topUser")
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("topDatetime")
        
        user_box = QVBoxLayout()
        user_box.addWidget(self.user_label)
        user_box.addWidget(self.datetime_label)
        header_top.addLayout(user_box)
        
        self._update_datetime()
        self._start_datetime_timer()
        
        layout.addLayout(header_top)
        
        # 2. Indicators (if any)
        if self.config.get("indicadores"):
            stats_layout = QHBoxLayout()
            stats_layout.setSpacing(16)
            
            # Sort indicators by order
            indicators = sorted(self.config["indicadores"], key=lambda x: x.get("order", 0))
            
            for ind in indicators:
                card = self._create_stat_card(ind["titulo"], "0")
                self.indicators_ui[ind["campo_api"]] = card.value_label
                stats_layout.addWidget(card)
                
            layout.addLayout(stats_layout)
        
        # 3. Filters & Actions Bar
        filters_layout = QHBoxLayout()
        
        # Search
        search_config = self.config.get("buscador", {})
        if search_config.get("habilitado"):
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText(search_config.get("placeholder", "Buscar..."))
            self.search_input.returnPressed.connect(self._on_search)
            
            search_action = self.search_input.addAction(
                icon("src/resources/icons/search.svg"),
                QLineEdit.TrailingPosition
            )
            search_action.setToolTip("Buscar")
            search_action.triggered.connect(self._on_search)
            
            filters_layout.addWidget(self.search_input)
            
        # Dynamic Combos
        if self.config.get("filtros"):
            sorted_filters = sorted(self.config["filtros"], key=lambda x: x.get("orden", 0))
            for f in sorted_filters:
                combo = QComboBox()
                # Store reference
                self.filters_ui[f["id"]] = combo
                
                # Apply width if configured
                if f.get("ancho"):
                    combo.setFixedWidth(f["ancho"])
                else:
                    # Default min width to avoid extreme truncation
                    combo.setMinimumWidth(150)
                    
                combo.currentIndexChanged.connect(self._on_filter_change)
                filters_layout.addWidget(combo)
                
        # Clear Filters Button
        self.clear_filters_btn = QPushButton("Limpiar filtros")
        self.clear_filters_btn.setObjectName("secondaryButton")
        self.clear_filters_btn.clicked.connect(self._clear_filters)
        filters_layout.addWidget(self.clear_filters_btn)
        
        filters_layout.addStretch()
        
        # Botón de Exportación
        self.export_btn = QPushButton("Exportar Grilla")
        # Igualar dimensiones del botón primario pero conservando un color neutral
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6; 
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)

        export_menu = QMenu(self)
        csv_action = export_menu.addAction("Exportar a CSV")
        pdf_action = export_menu.addAction("Exportar a PDF")
        
        csv_action.triggered.connect(self._export_csv)
        pdf_action.triggered.connect(self._export_pdf)
        
        self.export_btn.setMenu(export_menu)
        filters_layout.addWidget(self.export_btn)

        # New Button
        new_btn_config = self.config.get("boton_nuevo", {})
        if new_btn_config.get("habilitado"):
            self.new_button = QPushButton(new_btn_config.get("texto", "+ Nuevo"))
            self.new_button.setObjectName("primaryButton")
            self.new_button.clicked.connect(self._open_new)
            filters_layout.addWidget(self.new_button)
            
        layout.addLayout(filters_layout)
        
        # 4. Table
        columns = sorted(self.config["columnas"], key=lambda x: x.get("orden", 0))
        # Add actions column if needed
        has_actions = bool(self.config.get("acciones"))
        col_count = len(columns) + (1 if has_actions else 0)
        
        self.table = QTableWidget(0, col_count)
        
        # Headers
        headers = [c["etiqueta"] for c in columns]
        if has_actions:
            headers.append("Acciones")
        
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        
        # Col Widths
        header_view = self.table.horizontalHeader()
        for i, col in enumerate(columns):
            if not col.get("visible", True):
                self.table.setColumnHidden(i, True)
                
            if col.get("stretch"):
                header_view.setSectionResizeMode(i, QHeaderView.Stretch)
            elif col.get("ancho"):
                header_view.setSectionResizeMode(i, QHeaderView.Fixed)
                self.table.setColumnWidth(i, col["ancho"])
                
        if has_actions:
            idx = len(columns)
            header_view.setSectionResizeMode(idx, QHeaderView.Fixed)
            self.table.setColumnWidth(idx, 96) # Standard width for actions
            
        # Height constraint (from original view)
        self.table.setMinimumHeight(40 + (self.page_size * 44))
        self.table.setMaximumHeight(40 + (self.page_size * 44))
        
        layout.addWidget(self.table)
        
        # 5. Pagination
        if self.config.get("paginacion", {}).get("habilitado"):
            self.prev_btn = QPushButton(self.config["paginacion"].get("texto_anterior", "<"))
            self.prev_btn.clicked.connect(self._prev_page)
            
            self.page_label = QLabel()
            
            self.next_btn = QPushButton(self.config["paginacion"].get("texto_siguiente", ">"))
            self.next_btn.clicked.connect(self._next_page)
            
            pagination_layout = QHBoxLayout()
            pagination_layout.addStretch()
            pagination_layout.addWidget(self.prev_btn)
            pagination_layout.addWidget(self.page_label)
            pagination_layout.addWidget(self.next_btn)
            pagination_layout.addStretch()
            
            layout.addLayout(pagination_layout)
            
        layout.addStretch()

    def _create_stat_card(self, title, value):
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
    # Filters Logic
    # ======================================================

    def _init_async_filters(self):
        if not self.config.get("filtros"):
            return
            
        for f in self.config["filtros"]:
            combo = self.filters_ui.get(f["id"])
            if combo:
                self._start_combo_filter_loader(
                    combo, 
                    f["endpoint"], 
                    f["cache_key"], 
                    f["etiqueta_defecto"]
                )

    def _start_combo_filter_loader(self, combo, endpoint, cache_key, default):
        worker = ComboLoaderRunnable(self.catalogo_service.get_catalogo, endpoint, cache_key)
        self._active_runnables.append(worker)

        worker.signals.result.connect(partial(self._on_filter_data, combo, default))
        worker.signals.error.connect(lambda e: LoggerService().log_error(f"Error loading filter {endpoint}", e))
        
        self.thread_pool.start(worker)

    def _on_filter_data(self, combo, default, data):
        combo.clear()
        combo.addItem(default, None)
        if data:
            for item in data:
                combo.addItem(item["nombre"], item["id"])

    def _clear_filters(self):
        if hasattr(self, 'search_input'):
            self.search_input.clear()
        
        for combo in self.filters_ui.values():
            combo.setCurrentIndex(0)
            
        self.current_page = 1
        self._reload_all()

    def _on_search(self):
        query = self.search_input.text() if hasattr(self, 'search_input') else ""
        if query:
            LoggerService().log_event(f"Usuario buscó en {self.config['id']}: '{query}'")
        self.current_page = 1
        self._reload_all()

    def _on_filter_change(self):
        LoggerService().log_event(f"Usuario aplicó filtros en grilla {self.config['id']}")
        self.current_page = 1
        self._reload_all()

    # ======================================================
    # Data Loading
    # ======================================================

    def _reload_all(self):
        self.loading_overlay.show_loading()
        
        # State capture
        page = self.current_page
        size = self.page_size
        
        # Build Filters Dict
        filters = {}
        if hasattr(self, 'search_input'):
            filters[self.config.get("buscador", {}).get("param_api")] = self.search_input.text()
            
        for f in self.config.get("filtros", []):
            combo = self.filters_ui.get(f["id"])
            if combo:
                filters[f["param_api"]] = combo.currentData()

        # Task closure
        def fetch_task():
            # Build URL
            base_url = self.config["endpoints"]["listado"]
            url = f"{base_url}?page={page}&size={size}"
            
            for param, value in filters.items():
                if value:
                    url += f"&{param}={value}"
            
            main_data = self.api.get(url)
            
            indicadores_data = None
            if self.config.get("endpoints", {}).get("indicadores"):
                indicadores_data = self.api.get(self.config["endpoints"]["indicadores"])
                
            return {
                "listado": main_data,
                "indicadores": indicadores_data
            }

        self.worker = ApiWorker(fetch_task, parent=self)
        self.worker.finished.connect(self._on_reload_finished)
        self.worker.error.connect(self._on_reload_error)
        self.worker.start()

    def _on_reload_finished(self, data):
        self._populate_table(data["listado"])
        if data.get("indicadores"):
            self._populate_indicators(data["indicadores"])
        self.loading_overlay.hide_loading()

    def _on_reload_error(self, error):
        self.loading_overlay.hide_loading()
        LoggerService().log_error(f"Error cargando grilla {self.config['id']}", error)
        # TODO: Show alert? Original view just logged and printed
        print(f"Error reloading: {error}")

    def _populate_table(self, response):
        items = response["items"]
        self.total_pages = response["pages"]
        self.table.setRowCount(len(items))
        
        columns = sorted(self.config["columnas"], key=lambda x: x.get("orden", 0))
        id_field = self.config["campo_id"]
        null_value = self.config.get("valor_nulo", "—")
        
        for row, item in enumerate(items):
            # Data cells
            for col_idx, col_config in enumerate(columns):
                val = item.get(col_config["campo_api"])
                text = str(val) if val is not None else null_value
                item_widget = QTableWidgetItem(text)
                
                # Check for specific alignment in config later? 
                # For now, align center-left or center based on type usually looks best.
                # User asked for "alineada", implying it's misaligned. 
                # Usually QTableWidget defaults to Left-Center. Titles are usually Center or Left.
                # If they say "name of field... and info appears misaligned", it might mean headers vs content.
                # Headers are usually centered. Let's align content to Center-Left (VCenter | Left) 
                # OR if they want strict column alignment, maybe everything Left?
                # But headers are centered by default in many themes.
                # Let's try centering everything vertically, and Left horizontally for text, Center for short IDs.
                # To be safe and generic: AlignCenter for everything usually solves "misaligned vs header".
                # Or better: VCenter | HCenter
                item_widget.setTextAlignment(Qt.AlignCenter)
                
                self.table.setItem(row, col_idx, item_widget)
            
            # Actions cell
            if self.config.get("acciones"):
                record_id = item.get(id_field)
                self._add_actions_cell(row, len(columns), record_id)

        self.page_label.setText(f"Página {self.current_page} de {self.total_pages}")

    def _populate_indicators(self, data):
        for ind_config in self.config.get("indicadores", []):
            field = ind_config["campo_api"]
            label = self.indicators_ui.get(field)
            if label:
                val = data.get(field, 0)
                label.setText(str(val))

    # ======================================================
    # Actions
    # ======================================================

    def _add_actions_cell(self, row, col_idx, record_id):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignCenter)
        
        sorted_actions = sorted(self.config["acciones"], key=lambda x: x.get("orden", 0))
        
        for action in sorted_actions:
            btn = QPushButton()
            btn.setIcon(icon(action["icono"]))
            btn.setToolTip(action.get("tooltip", ""))
            
            # Connect action
            # We must bind default args carefully in loop
            btn.clicked.connect(partial(self._execute_action, action, record_id))
            
            l.addWidget(btn)
            
        self.table.setCellWidget(row, col_idx, w)

    def _execute_action(self, action_config, record_id):
        action_type = action_config.get("tipo")
        
        if action_type == "dialog":
            dialog_class_name = action_config.get("dialog_class")
            DialogClass = get_dialog_class(dialog_class_name)
            if DialogClass:
                # Assuming generic constructor signature: (parent, id=...)
                # Need to map 'id' param name if different. Assuming 'activo_id' for ActivoDialog
                # But GenericGridView is generic. 
                # ActivoDialog takes 'activo_id'. A generic dialog might take 'record_id'.
                # For now, let's look at how ActivoDialog is defined: __init__(self, parent=None, activo_id=None)
                # To be generic, we might need a mapping or kwarg expansion.
                # However, for ActivoDialog specifically, it expects `activo_id`.
                # If we pass `activo_id=record_id`, it works for ActivoDialog.
                # For future dialogs, we should standardize on `record_id` or similar.
                # Or we can inspect the class? Too complex.
                # Let's pass it as a generic id kwarg AND specific one if we know it.
                # Or just pass it as position arg if supported? No.
                
                # Hack for now to support ActivoDialog specifically without breaking it:
                kwargs = {}
                if dialog_class_name == "ActivoDialog":
                    kwargs["activo_id"] = record_id
                else:
                    kwargs["record_id"] = record_id # Future proofing
                    
                dialog = DialogClass(self, **kwargs)
                if dialog.exec():
                    self._reload_all()
            else:
                print(f"Unknown dialog class: {dialog_class_name}")

        elif action_type == "delete":
            self._execute_delete(action_config, record_id)

        elif action_type == "export_row":
            self._export_single_row(record_id)

    def _export_single_row(self, record_id):
        endpoint_template = self.config.get("endpoints", {}).get("detalle")
        if not endpoint_template:
            self._show_export_error("No se ha configurado endpoint de detalle.")
            return

        url = endpoint_template.replace("{id}", str(record_id))
        
        self.loading_overlay.show_loading()
        
        # Define worker task that fetches AND enriches
        def fetch_and_enrich():
            # 1. Fetch Raw Data
            data = self.api.get(url)
            if not data: 
                return None
                
            # 2. Enrich if form config is present
            form_config_path = self.config.get("form_config")
            if form_config_path:
                try:
                    return self._enrich_data(data, form_config_path)
                except Exception as e:
                    print(f"Error enriching data: {e}")
                    return data # Fallback to raw
            return data
            
        worker = ApiWorker(fetch_and_enrich, parent=self)
        worker.finished.connect(lambda data: self._save_single_row_csv(data, record_id))
        worker.error.connect(lambda e: (
            self.loading_overlay.hide_loading(),
            self._show_export_error(f"Error obteniendo datos: {e}")
        ))
        self.worker = worker # Keep ref
        worker.start()

    def _enrich_data(self, data, config_path):
        # Load Form Config
        with open(config_path, 'r', encoding='utf-8') as f:
            form_config = json.load(f)
            
        # Build Field Map
        field_map = {}
        for section in form_config.get("sections", []):
            for field in section.get("fields", []):
                field_map[field["key"]] = field
                
        enriched = data.copy()
        
        # Process each field
        for key, value in data.items():
            if value is None:
                continue
                
            field_cfg = field_map.get(key)
            if not field_cfg:
                continue
                
            ftype = field_cfg.get("type")
            
            # Static Options (e.g. BoolYesNo)
            if ftype == "combo_static":
                options = field_cfg.get("options", [])
                # Handle boolean vs string comparison
                for opt in options:
                    # Loose comparison for bools/strings
                    if str(opt["id"]) == str(value):
                        enriched[key] = opt["nombre"]
                        break
                        
            # Dynamic Combos
            elif ftype == "combo":
                source = field_cfg.get("source")
                cache_key = field_cfg.get("cache_key")
                
                # Handling dependent combos (url params may need values)
                # For complex dependencies, this simple enricher might fall short
                # But typically 'source' is static or we can try to fetch generic catalogs
                # If source has {value}, we might skip or try to resolve.
                # But for standard catalogs (Estado, Tipo, etc) it works suitable.
                
                if source and "{" not in source:     
                    try:
                        # Synchronous fetch (ok since we are in worker thread)
                        options = self.catalogo_service.get_catalogo(source, cache_key)
                        if options:
                            # Search for ID
                            # Handle standard ID format (sometimes UUID string, sometimes int)
                            found = False
                            # Support multiple selection (list of IDs)
                            if isinstance(value, list):
                                names = []
                                for v in value:
                                    for opt in options:
                                        if str(opt["id"]) == str(v):
                                            names.append(opt["nombre"])
                                            break
                                enriched[key] = ", ".join(names)
                                found = True
                            else:
                                for opt in options:
                                    if str(opt["id"]) == str(value):
                                        enriched[key] = opt["nombre"]
                                        found = True
                                        break
                    except Exception as e:
                        print(f"Error resolving catalog {source}: {e}")
                        
        return enriched

    def _save_single_row_csv(self, data, record_id):
        self.loading_overlay.hide_loading()
        if not data:
            self._show_export_error("No se obtuvieron datos.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            f"Exportar Registro {record_id}", 
            f"registro_{record_id}.csv", 
            "CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        if not file_path.endswith('.csv'):
            file_path += '.csv'
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Option A: Vertical (Property | Value) - Better for reading a single record form
                writer.writerow(["Campo", "Valor"])
                for key, value in data.items():
                    writer.writerow([key, str(value) if value is not None else ""])
                    
        except Exception as e:
            LoggerService().log_error("Error guardando CSV único", e)
            self._show_export_error(f"Error al guardar archivo: {str(e)}")

    def _execute_delete(self, action_config, record_id):
        confirm_config = action_config.get("confirmacion", {})
        
        confirm = AlertDialog(
            title=confirm_config.get("titulo", "Eliminar"),
            message=confirm_config.get("mensaje", "¿Estás seguro?"),
            icon_path=confirm_config.get("icono", "src/resources/icons/alert_warning.svg"),
            confirm_text=confirm_config.get("boton_confirmar", "Eliminar"),
            cancel_text=confirm_config.get("boton_cancelar", "Cancelar"),
            parent=self
        )
        
        if confirm.exec():
            try:
                endpoint = self.config["endpoints"]["eliminar"].replace("{id}", str(record_id))
                self.api.delete(endpoint)
                
                LoggerService().log_event(f"Usuario eliminó registro ID: {record_id} en {self.config['id']}")
                self._reload_all()
            except Exception as e:
                LoggerService().log_error(f"Error eliminando ID: {record_id}", e)
                AlertDialog(
                    title="Error", 
                    message=str(e), 
                    icon_path="src/resources/icons/alert_error.svg", 
                    confirm_text="Ok", 
                    parent=self
                ).exec()

    def _open_new(self):
        new_config = self.config.get("boton_nuevo", {})
        dialog_class_name = new_config.get("dialog_class")
        DialogClass = get_dialog_class(dialog_class_name)
        
        if DialogClass:
            # New mode usually implies no ID argument
            dialog = DialogClass(self)
            if dialog.exec():
                self._reload_all()

    # ======================================================
    # Lógica de Exportación
    # ======================================================

    def _show_export_error(self, message="No hay registros para exportar"):
        AlertDialog(
            title="Aviso", 
            message=message, 
            icon_path="src/resources/icons/alert_info.svg", 
            confirm_text="Entendido", 
            parent=self
        ).exec()

    def _export_csv(self):
        if self.table.rowCount() == 0:
            self._show_export_error()
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "", "CSV (*.csv)")
        if not file_path:
            return
            
        if not file_path.endswith('.csv'):
            file_path += '.csv'

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Prepara encabezados
                headers = []
                visible_cols = []
                
                for col in range(self.table.columnCount()):
                    if self.table.isColumnHidden(col):
                        continue
                        
                    header_item = self.table.horizontalHeaderItem(col)
                    label = header_item.text() if header_item else ""
                    if label == "Acciones":
                        continue
                        
                    headers.append(label)
                    visible_cols.append(col)
                
                writer.writerow(headers)
                
                # Prepara filas
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in visible_cols:
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
                    
        except Exception as e:
            LoggerService().log_error("Error exportando a CSV", e)
            self._show_export_error(f"Error al exportar: {str(e)}")

    def _export_pdf(self):
        if self.table.rowCount() == 0:
            self._show_export_error()
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "", "PDF (*.pdf)")
        if not file_path:
            return
            
        if not file_path.endswith('.pdf'):
            file_path += '.pdf'
            
        try:
            doc = QTextDocument()
            
            # Estilo HTML simple
            html = """
            <html>
            <head>
            <style>
                body { font-family: sans-serif; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th { background-color: #f2f2f2; font-weight: bold; padding: 8px; border: 1px solid #ccc; text-align: center; font-size: 10pt; }
                td { padding: 8px; border: 1px solid #ccc; font-size: 10pt; }
            </style>
            </head>
            <body>
            """
            
            html += f"<h1>{self.config.get('titulo', 'Reporte')}</h1>"
            html += f"<p>Generado el: {QDateTime.currentDateTime().toString('dd/MM/yyyy HH:mm')}</p>"
            html += "<table><thead><tr>"
            
            # Encabezados y Columnas
            visible_cols = []
            for col in range(self.table.columnCount()):
                if self.table.isColumnHidden(col):
                    continue
                header_item = self.table.horizontalHeaderItem(col)
                label = header_item.text() if header_item else ""
                if label == "Acciones":
                    continue
                
                html += f"<th>{label}</th>"
                visible_cols.append(col)
                
            html += "</tr></thead><tbody>"
            
            # Filas
            for row in range(self.table.rowCount()):
                html += "<tr>"
                for col in visible_cols:
                    item = self.table.item(row, col)
                    text = item.text() if item else ""
                    html += f"<td>{text}</td>"
                html += "</tr>"
                
            html += "</tbody></table></body></html>"
            
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            
            doc.print_(printer)
            
        except Exception as e:
            LoggerService().log_error("Error exportando a PDF", e)
            self._show_export_error(f"Error al exportar: {str(e)}")

    def _execute_delete(self, action_config, record_id):
        confirm_config = action_config.get("confirmacion", {})
        
        confirm = AlertDialog(
            title=confirm_config.get("titulo", "Eliminar"),
            message=confirm_config.get("mensaje", "¿Estás seguro?"),
            icon_path=confirm_config.get("icono", "src/resources/icons/alert_warning.svg"),
            confirm_text=confirm_config.get("boton_confirmar", "Eliminar"),
            cancel_text=confirm_config.get("boton_cancelar", "Cancelar"),
            parent=self
        )
        
        if confirm.exec():
            try:
                endpoint = self.config["endpoints"]["eliminar"].replace("{id}", str(record_id))
                self.api.delete(endpoint)
                
                LoggerService().log_event(f"Usuario eliminó registro ID: {record_id} en {self.config['id']}")
                self._reload_all()
            except Exception as e:
                LoggerService().log_error(f"Error eliminando ID: {record_id}", e)
                AlertDialog(
                    title="Error", 
                    message=str(e), 
                    icon_path="src/resources/icons/alert_error.svg", 
                    confirm_text="Ok", 
                    parent=self
                ).exec()

    def _open_new(self):
        new_config = self.config.get("boton_nuevo", {})
        dialog_class_name = new_config.get("dialog_class")
        DialogClass = get_dialog_class(dialog_class_name)
        
        if DialogClass:
            # Modo creación generalmente no implica argumento ID
            dialog = DialogClass(self)
            if dialog.exec():
                self._reload_all()

    def _execute_action(self, action_config, record_id):
        action_type = action_config.get("tipo")
        
        if action_type == "dialog":
            dialog_class_name = action_config.get("dialog_class")
            DialogClass = get_dialog_class(dialog_class_name)
            if DialogClass:
                # Asumimos una firma de constructor genérica: (parent, id=...)
                # Para ActivoDialog, se espera 'activo_id'.
                # Para futuros diálogos, deberíamos estandarizar en 'record_id'.
                # Solución temporal para soportar ActivoDialog sin romperlo:
                
                kwargs = {}
                if dialog_class_name == "ActivoDialog":
                    kwargs["activo_id"] = record_id
                else:
                    kwargs["record_id"] = record_id # A futuro
                    
                dialog = DialogClass(self, **kwargs)
                if dialog.exec():
                    self._reload_all()
            else:
                print(f"Unknown dialog class: {dialog_class_name}")

        elif action_type == "delete":
            self._execute_delete(action_config, record_id)

        elif action_type == "export_row":
            self._export_single_row(record_id)

    def _export_single_row(self, record_id):
        endpoint_template = self.config.get("endpoints", {}).get("detalle")
        if not endpoint_template:
            self._show_export_error("No se ha configurado endpoint de detalle.")
            return

        url = endpoint_template.replace("{id}", str(record_id))
        
        self.loading_overlay.show_loading()
        
        # Define tarea en segundo plano que obtiene y enriquece la información
        def fetch_and_enrich():
            # 1. Obtener Datos Crudos desde la fuente
            data = self.api.get(url)
            if not data: 
                return None
                
            # 2. Enriquecer datos si existe configuración de formulario (traducir IDs a texto)
            form_config_path = self.config.get("form_config")
            if form_config_path:
                try:
                    return self._enrich_data(data, form_config_path)
                except Exception as e:
                    print(f"Error enriching data: {e}")
                    return data # Fallback a crudo
            return data
            
        worker = ApiWorker(fetch_and_enrich, parent=self)
        worker.finished.connect(lambda data: self._save_single_row_csv(data, record_id))
        worker.error.connect(lambda e: (
            self.loading_overlay.hide_loading(),
            self._show_export_error(f"Error obteniendo datos: {e}")
        ))
        self.worker = worker # Mantener referencia
        worker.start()

    def _enrich_data(self, data, config_path):
        # Cargar Configuración del Formulario
        with open(config_path, 'r', encoding='utf-8') as f:
            form_config = json.load(f)
            
        # Construir Mapa de Campos
        field_map = {}
        for section in form_config.get("sections", []):
            for field in section.get("fields", []):
                field_map[field["key"]] = field
                
        enriched = data.copy()
        
        # Procesar cada campo
        for key, value in data.items():
            if value is None:
                continue
                
            field_cfg = field_map.get(key)
            if not field_cfg:
                continue
                
            ftype = field_cfg.get("type")
            
            # Opciones Estáticas (ej. BoolYesNo)
            if ftype == "combo_static":
                options = field_cfg.get("options", [])
                # Manejar comparación booleana vs string
                for opt in options:
                    # Comparación laxa
                    if str(opt["id"]) == str(value):
                        enriched[key] = opt["nombre"]
                        break
                        
            # Combos Dinámicos
            elif ftype == "combo":
                source = field_cfg.get("source")
                cache_key = field_cfg.get("cache_key")
                
                # Manejo de combos dependientes
                # Si la fuente tiene {value}, podríamos intentar resolver o saltar.
                # Para catálogos estándar (Estado, Tipo, etc) funciona adecuadamente.
                
                if source and "{" not in source:     
                    try:
                        # Busqueda síncrona (segura ya que estamos en hilo worker)
                        options = self.catalogo_service.get_catalogo(source, cache_key)
                        if options:
                            # Buscar por ID
                            # Manejar formato estándar de ID
                            found = False
                            # Soporte selección múltiple (lista de IDs)
                            if isinstance(value, list):
                                names = []
                                for v in value:
                                    for opt in options:
                                        if str(opt["id"]) == str(v):
                                            names.append(opt["nombre"])
                                            break
                                enriched[key] = ", ".join(names)
                                found = True
                            else:
                                for opt in options:
                                    if str(opt["id"]) == str(value):
                                        enriched[key] = opt["nombre"]
                                        found = True
                                        break
                    except Exception as e:
                        print(f"Error resolving catalog {source}: {e}")
                        
        return enriched

    def _save_single_row_csv(self, data, record_id):
        self.loading_overlay.hide_loading()
        if not data:
            self._show_export_error("No se obtuvieron datos.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            f"Exportar Registro {record_id}", 
            f"registro_{record_id}.csv", 
            "CSV (*.csv)"
        )
        
        if not file_path:
            return
            
        if not file_path.endswith('.csv'):
            file_path += '.csv'
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Opción A: Formato vertical (Campo | Valor), ideal para lectura de registro único
                writer.writerow(["Campo", "Valor"])
                for key, value in data.items():
                    writer.writerow([key, str(value) if value is not None else ""])
                    
        except Exception as e:
            LoggerService().log_error("Error guardando CSV único", e)
            self._show_export_error(f"Error al guardar archivo: {str(e)}")

    # ======================================================
    # Pagination
    # ======================================================

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._reload_all()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._reload_all()
