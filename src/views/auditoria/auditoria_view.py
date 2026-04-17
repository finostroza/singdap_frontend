import os
from PySide6.QtWidgets import QDateEdit, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import QDate, Qt
from src.components.generic_grid_view import GenericGridView
from src.workers.api_worker import ApiWorker

class AuditoriaView(GenericGridView):
    def __init__(self):
        # Construct path to auditoria.json config
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(src_dir, "config", "grillas", "auditoria.json")
        
        # Primero configuramos variables de control
        self.page_size = 10
        self._validating_date = False
        self.cached_users = [] # Memoria local para búsqueda por nombre
        
        # Cargamos la base pero SIN recarga automática inmediata (la forzaremos después)
        super().__init__(config_path=config_path)
        
        # Add date filters to UI
        self._setup_date_filters()
        
        # Forzar la carga inicial con los filtros de fecha ya estables
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._reload_all)

    def refresh(self):
        """Carga la lista completa de usuarios (activos e inactivos) para mapear nombre -> id."""
        def fetch_users():
            # Buscamos hasta 1000 usuarios sin filtrar por actividad para encontrar logs históricos
            return self.user_service.list_users(size=1000)
            
        self.users_worker = ApiWorker(fetch_users)
        self.users_worker.finished.connect(self._on_users_loaded)
        self.users_worker.start()

    def _on_users_loaded(self, response):
        items = []
        if isinstance(response, list):
            items = response
        elif isinstance(response, dict):
            items = response.get("items", [])
            if not items and "data" in response:
                items = response["data"]
                
        self.cached_users = items
        print(f"[AUDITORIA] Cache de usuarios cargada: {len(self.cached_users)} registros")

    def _setup_date_filters(self):
        """Agrega los campos de fecha desde/hasta a la barra de filtros."""
        # Fecha Desde
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setMinimumWidth(120)
        # Default to 30 days ago
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setObjectName("gridToolbarCombo")
        
        # Fecha Hasta
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setMinimumWidth(120)
        # El usuario solicita que 'hasta' sea menor a today (ayer por defecto)
        self.date_to.setDate(QDate.currentDate().addDays(-1))
        self.date_to.setObjectName("gridToolbarCombo")
        
        # Labels and Layout
        lbl_from = QLabel("Desde:")
        lbl_from.setStyleSheet("color: #64748b; font-weight: bold; margin-left: 8px;")
        lbl_to = QLabel("Hasta:")
        lbl_to.setStyleSheet("color: #64748b; font-weight: bold; margin-left: 8px;")
        
        # Find index to insert filters (after search input but before column combo)
        # Search input is at index 0
        self.filters_layout.insertWidget(1, lbl_from)
        self.filters_layout.insertWidget(2, self.date_from)
        self.filters_layout.insertWidget(3, lbl_to)
        self.filters_layout.insertWidget(4, self.date_to)
        
        # Connect date changes to reload
        self.date_from.dateChanged.connect(self._on_search)
        self.date_to.dateChanged.connect(self._on_date_to_changed)

    def _on_date_to_changed(self):
        """Valida que la fecha hasta sea menor a hoy usando un timer para despejar eventos."""
        if self._validating_date:
            return
            
        today = QDate.currentDate()
        selected = self.date_to.date()
        
        if selected >= today:
            self._validating_date = True
            # Forzamos el reseteo visual inmediato antes del popup
            self.date_to.blockSignals(True)
            self.date_to.setDate(today.addDays(-1))
            self.date_to.blockSignals(False)
            
            # Lanzamos el popup en el siguiente ciclo de eventos para evitar duplicidad
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1, self._show_date_error_popup)
            return

        self._on_search()

    def _show_date_error_popup(self):
        """Muestra el popup de error y libera la bandera de validación."""
        from src.components.alert_dialog import AlertDialog
        dialog = AlertDialog(
            title="Fecha Inválida",
            message="fecha_hasta debe ser anterior a la fecha de hoy",
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Entendido",
            cancel_text="",
            parent=self
        )
        dialog.exec()
        self._validating_date = False
        self._on_search()

    def _reload_all(self):
        """Sobrescribe la recarga para incluir los parámetros de fecha."""
        if not hasattr(self, 'date_from') or self.date_from is None:
            return

        self.loading_overlay.show_loading()
        
        page = self.current_page
        size = 10 # Forzamos 10 elementos por página conforme a lo solicitado
        base_url = self.config["endpoints"]["listado"]
        
        # Formato ISO requerido
        df = self.date_from.date().toString("yyyy-MM-dd")
        dt = self.date_to.date().toString("yyyy-MM-dd")

        def fetch_task():
            if not self.permission_service.has_module_access(self.perm_module):
                return {"listado": {"items": [], "pages": 1}, "indicadores": None}
            
            # Parametros en diccionario para mayor seguridad y alineación con la API
            params = {
                "fecha_desde": df,
                "fecha_hasta": dt,
                "page": page,
                "size": size # Valor de 10 solicitado
            }
            
            # Search query inteligente basada en el combo de la Toolbar
            query_text = self.search_input.text().strip()
            if query_text:
                scope = self.column_filter_combo.currentData()
                
                # Mapeo de parámetros según backend (OpenAPI)
                if scope == "__all__":
                    params["search"] = query_text
                elif scope == "action":
                    params["action"] = query_text
                elif scope == "entity":
                    params["entity"] = query_text
                elif scope == "usuario_nombre": # Columna Usuario
                    # Si es un UUID, lo enviamos directo bajo 'user_id'
                    if len(query_text) > 30 and "-" in query_text:
                        params["user_id"] = query_text
                    else:
                        # Buscamos match en la cache local (vía múltiples campos posibles)
                        match_id = None
                        ql = query_text.lower()
                        for u in self.cached_users:
                            # Recopilar todos los campos de identidad posibles
                            posibles_nombres = [
                                str(u.get("nombre_completo") or "").lower(),
                                str(u.get("fullname") or "").lower(),
                                str(u.get("nombre") or "").lower(),
                                str(u.get("username") or "").lower(),
                                str(u.get("rut") or "").lower(),
                                str(u.get("email") or "").lower()
                            ]
                            if any(ql in n for n in posibles_nombres if n):
                                # Priorizar 'id', luego 'backend_id'
                                match_id = u.get("id") or u.get("backend_id")
                                break
                        
                        if match_id:
                            params["user_id"] = str(match_id)
                            print(f"[AUDITORIA] Search match: '{query_text}' -> user_id: {match_id}")
                        else:
                            # Si no hay match ID, enviamos a 'search' para que el backend busque en texto libre
                            params["search"] = query_text
                            print(f"[AUDITORIA] No match for: '{query_text}', using fallback search")
                
            return {
                "listado": self.api.get(base_url, params=params),
                "indicadores": None
            }

        self.worker = ApiWorker(fetch_task, parent=self)
        self.worker.finished.connect(self._on_reload_finished)
        self.worker.error.connect(self._on_reload_error)
        self.worker.start()

    def _on_reload_finished(self, data):
        try:
            if not data: data = {}
            listado = data.get("listado") or {}
            
            # Calcular indicadores dinámicamente para Auditoría
            total_real = 0
            if isinstance(listado, dict):
                total_real = listado.get("total", 0)
            
            # Calcular días usando daysTo (nativo de QDate)
            q1 = self.date_from.date()
            q2 = self.date_to.date()
            delta = q1.daysTo(q2) + 1
            
            # Inyectar indicadores para que GenericGridView los muestre
            data["indicadores"] = {
                "total_actividades": total_real,
                "total_dias": max(0, delta)
            }
        except Exception as e:
            print(f"Error calculando indicadores en Auditoría: {e}")
        finally:
            # Es fundamental llamar al super() para que oculte el overlay de carga
            super()._on_reload_finished(data)




