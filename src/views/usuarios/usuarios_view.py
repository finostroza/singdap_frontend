from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QAbstractScrollArea,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
    QMessageBox,
)
from PySide6.QtCore import Qt

from src.components.loading_overlay import LoadingOverlay
from src.core.api_client import ApiClient
from src.services.cache_manager import CacheManager
from src.services.user_service import UserService
from src.workers.api_worker import ApiWorker


class UsuariosView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)
        self.api = ApiClient()
        self.user_service = UserService()
        self.cache_manager = CacheManager()
        self.permissions_cache_key = "usuarios_permissions_v2"
        self.permissions_overrides = {}

        self.current_user_index = 0
        self.status_toggle_worker = None
        self.refresh_worker = None
        self.refresh_worker = None
        self.active_workers = [] # Lista para mantener referencias vivas de hilos en ejecución
        self.users_data = []
        self.master_action_ids = {} # Diccionario maestro: {MOD_KEY: {ACCION: ID}}
        self.warned_missing_update_api = False
        self.list_users_api_available = True
        self.permissions_update_api_available = False

        self.modules = [
            ("Inventario de Activos", "INVENTARIO"),
            ("EIPD (Ex PIA)", "EIPD"),
            ("Usuarios / Roles", "USUARIOS"),
            ("RAT", "RAT"),
            ("Trazabilidad", "TRAZABILIDAD"),
            ("Mantenedores", "MANTENEDORES"),
        ]

        self.module_aliases = {
            "INVENTARIO": ["inventario", "activo", "activos"],
            "EIPD": ["eipd", "pia"],
            "USUARIOS": ["usuario", "usuarios", "rol", "roles"],
            "RAT": ["rat"],
            "TRAZABILIDAD": ["trazabilidad"],
            "MANTENEDORES": ["mantenedor", "catalogo", "catalogos", "catalog"],
        }

        self.privilege_name_by_code = {}

        title = QLabel("Modulo de Usuarios")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Administra usuarios, consulta su estado de acceso y revisa la matriz efectiva de permisos por modulo."
        )
        subtitle.setObjectName("pageSubtitle")

        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(subtitle)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        users_card = self._users_list_card()
        matrix_card = self._matrix_card()
        users_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        matrix_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        matrix_card.setMinimumWidth(0)

        content_layout.addWidget(users_card, 6)
        content_layout.addWidget(matrix_card, 5)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addSpacing(8)
        layout.addLayout(content_layout)

        self._load_backend_data()

    def _users_list_card(self):
        card = QFrame()
        card.setObjectName("card")

        title = QLabel("Usuarios")
        title.setObjectName("cardTitle")

        subtitle = QLabel("Selecciona un usuario para ver su matriz efectiva por modulos")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        top_titles = QVBoxLayout()
        top_titles.setSpacing(2)
        top_titles.addWidget(title)
        top_titles.addWidget(subtitle)

        self.search = QLineEdit()
        self.search.setObjectName("usersSearch")
        self.search.setPlaceholderText("Buscar (nombre, mail, id)...")
        self.search.textChanged.connect(self._on_search_changed)
        self.search.setFixedWidth(360)

        self.users_list = QListWidget()
        self.users_list.setObjectName("userListModern")
        self.users_list.setFrameShape(QFrame.NoFrame)
        self.users_list.setSpacing(10)
        self.users_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.users_list.itemClicked.connect(self._on_user_selected)

        layout = QVBoxLayout(card)
        layout.addLayout(top_titles)
        layout.addWidget(self.search, alignment=Qt.AlignLeft)
        layout.addSpacing(8)
        layout.addWidget(self.users_list)

        return card

    def _matrix_card(self):
        card = QFrame()
        card.setObjectName("card")

        title = QLabel("Matriz efectiva por modulos")
        title.setObjectName("cardTitle")

        subtitle = QLabel(
            "Cada fila representa un modulo del sistema y muestra las acciones habilitadas para el usuario seleccionado."
        )
        subtitle.setObjectName("pageSubtitle")

        self.selected_user_hint = QLabel("")
        self.selected_user_hint.setObjectName("matrixHint")

        self.matrix_edit_hint = QLabel("")
        self.matrix_edit_hint.setObjectName("matrixHint")

        # Aumentamos a 7 columnas para incluir 'ELIMINAR'
        self.table = QTableWidget(len(self.modules), 7)
        self.table.setObjectName("permissionTable")
        self.table.setHorizontalHeaderLabels(
            ["Modulo", "VER", "CREAR", "EDITAR", "ELIMINAR", "APROBAR", "EXPORTAR"]
        )
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setMinimumWidth(0)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        
        # Ajustamos el redimensionamiento para las 7 columnas
        for i in range(7):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)

        # Definimos anchos un poco mayores para asegurar legibilidad total
        self.table.setColumnWidth(0, 180) # Nombre del Modulo
        self.table.setColumnWidth(1, 75)  # Ver
        self.table.setColumnWidth(2, 75)  # Crear
        self.table.setColumnWidth(3, 75)  # Editar
        self.table.setColumnWidth(4, 90)  # Eliminar (Ahora con espacio suficiente)
        self.table.setColumnWidth(5, 90)  # Aprobar
        self.table.setColumnWidth(6, 90)  # Exportar
        self.table.cellClicked.connect(self._on_permission_cell_clicked)

        for row, (module_name, _) in enumerate(self.modules):
            module_item = QTableWidgetItem(module_name)
            module_item.setFlags(module_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, module_item)
            self.table.setRowHeight(row, 56)

        layout = QVBoxLayout(card)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.selected_user_hint)
        layout.addWidget(self.matrix_edit_hint)
        layout.addSpacing(6)
        layout.addWidget(self.table)

        return card

    def _load_backend_data(self):
        self.loading_overlay.show_loading()

        def fetch_data():
            result = {
                "users": [],
                "list_users_api_available": True,
                "permissions_update_api_available": False,
                "privilege_name_by_code": {},
            }

            me = self.user_service.get_me()
            me_permissions = self.user_service.get_permissions(str(me["id"]))

            try:
                privilegios = self.user_service.list_privilegios()
                result["privilege_name_by_code"] = {
                    p.get("codigo", ""): p.get("nombre", "") for p in privilegios
                }
                
                # CARGAMOS EL CATÁLOGO MAESTRO DE IDS DE ACCIÓN
                try:
                    master_data = self.user_service.list_modulos_con_acciones()
                    result["master_action_ids"] = self._map_master_actions(master_data)
                except Exception as e:
                    print(f"Error cargando catálogo maestro: {e}")
                    result["master_action_ids"] = {}
            except Exception as e:
                print(f"Error cargando privilegios: {e}")
                result["privilege_name_by_code"] = {}
                result["master_action_ids"] = {}

            users = []
            if self.api.is_admin:
                try:
                    users = self.user_service.list_users()
                except Exception:
                    result["list_users_api_available"] = False

            if not users:
                users = [me]

            for user in users:
                user_id = str(user.get("id", ""))
                perms_payload = me_permissions if user_id == str(me.get("id")) else None
                if perms_payload is None:
                    try:
                        perms_payload = self.user_service.get_permissions(user_id)
                    except Exception:
                        perms_payload = {
                            "permisos": []
                        }

                result["users"].append(
                    self._build_user_from_api(
                        user,
                        perms_payload,
                        result["privilege_name_by_code"],
                    )
                )

            return result

        self.worker = ApiWorker(fetch_data)
        self.worker.finished.connect(self._on_data_loaded)
        self.worker.error.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, data):
        self.loading_overlay.hide_loading()
        self.users_data = data.get("users", [])
        self.list_users_api_available = data.get("list_users_api_available", True)
        self.permissions_update_api_available = data.get(
            "permissions_update_api_available", False
        )
        self.privilege_name_by_code = data.get("privilege_name_by_code", {})
        self.master_action_ids = data.get("master_action_ids", {})
        self.permissions_overrides = self._load_permissions_overrides()

        if not self.users_data:
            self.users_data = [
                {
                    "name": "Sin datos",
                    "email": "",
                    "id": "-",
                    "status": "Inactivo",
                    "packs": 0,
                    "permissions": {
                        module_key: (False, False, False, False, False, False)
                        for _, module_key in self.modules
                    },
                }
            ]
        else:
            for user in self.users_data:
                # Solo aplicamos el mockup (overrides) si el usuario NO tiene permisos reales del backend
                # Si el usuario ya tiene permisos (vienen del API), esos mandan sobre la cache.
                has_real_perms = any(any(v) for v in user["permissions"].values())
                if not has_real_perms:
                    self._apply_permissions_override(user)

        self.current_user_index = 0
        self._populate_user_list()
        self._update_matrix_for_user(self.current_user_index)

    def _on_data_error(self, error):
        self.loading_overlay.hide_loading()
        QMessageBox.warning(
            self,
            "Usuarios / Roles",
            f"No fue posible cargar datos desde backend.\n\nDetalle: {error}",
        )
        self.users_data = []
        self._populate_user_list()
        self._update_edit_hint()

    def _build_user_from_api(self, user, permissions_payload, privilege_name_by_code):
        user_id_raw = str(user.get("id", ""))
        display_id = user.get("rut") or user_id_raw[:8].upper() or "-"

        permissions = self._map_permissions_to_modules(
            permissions_payload,
            privilege_name_by_code,
        )

        return {
            "name": user.get("nombre_completo") or user.get("email") or "Usuario",
            "email": user.get("email", ""),
            "id": display_id,
            "backend_id": user_id_raw,
            "status": "Activo" if user.get("is_active", False) else "Inactivo",
            "packs": len((permissions_payload or {}).get("packs", [])),
            "permissions": permissions.get("matrix", {}),
            "action_ids": permissions.get("action_ids", {}),
        }

    def _map_permissions_to_modules(self, payload, privilege_name_by_code):
        payload = payload or {}

        # El backend real entrega "permisos" como una lista de objetos
        api_permisos = payload.get("permisos", [])

        # Mapeo para el backend real
        real_backend_matrix = {}
        action_ids = {} # Guardaremos los accion_id aquí
        
        if api_permisos:
            for item in api_permisos:
                raw_mod = item.get("modulo_codigo", "").upper()
                acc_code = item.get("accion_codigo", "").upper()
                is_allowed = bool(item.get("permitido", False))
                accion_id = item.get("accion_id") # Capturamos el ID real de la acción
                
                # Resolvemos el modulo
                mod_key = self._resolve_module_key(raw_mod)

                if mod_key not in real_backend_matrix:
                    real_backend_matrix[mod_key] = {
                        "VIEW": False, "CREATE": False, "EDIT": False, 
                        "DELETE": False, "APPROVE": False, "EXPORT": False
                    }
                    action_ids[mod_key] = {
                        "VIEW": None, "CREATE": None, "EDIT": None, 
                        "DELETE": None, "APPROVE": None, "EXPORT": None
                    }

                # Usamos el detector de acciones 'humanizado'
                action = self._detect_action(acc_code)
                if action:
                    col_key = action.upper()
                    # SOLO marcamos como permitido si el backend lo dice explícitamente
                    real_backend_matrix[mod_key][col_key] = is_allowed
                    # SIEMPRE guardamos el accion_id si viene, para poder hacer PATCH luego
                    action_ids[mod_key][col_key] = accion_id

        perfiles = [self._normalize_text(p) for p in payload.get("perfiles", [])]
        privileges = payload.get("privileges", [])

        normalized_privileges = []
        for code in privileges:
            norm_code = self._normalize_text(code)
            name = privilege_name_by_code.get(code, "")
            normalized_privileges.append(f"{norm_code} {self._normalize_text(name)}")

        matrix = {}
        for _, module_key in self.modules:
            aliases = self.module_aliases.get(module_key, [])
            module_enabled = any(
                alias in profile
                for profile in perfiles
                for alias in aliases
            )

            view_access = False
            create_access = False
            edit_access = False
            delete_access = False

            for priv_text in normalized_privileges:
                if not any(alias in priv_text for alias in aliases):
                    continue

                action = self._detect_action(priv_text)
                if action == "view":
                    view_access = True
                elif action == "create":
                    create_access = True
                elif action == "edit":
                    edit_access = True
                elif action == "delete":
                    delete_access = True
                elif action == "approve":
                    approve_access = True
                elif action == "export":
                    export_access = True
                else:
                    view_access = True

            if api_permisos:
                # Usar datos del backend real
                matrix[module_key] = (
                    real_backend_matrix.get(module_key, {}).get("VIEW", False),
                    real_backend_matrix.get(module_key, {}).get("CREATE", False),
                    real_backend_matrix.get(module_key, {}).get("EDIT", False),
                    real_backend_matrix.get(module_key, {}).get("DELETE", False),
                    real_backend_matrix.get(module_key, {}).get("APPROVE", False),
                    real_backend_matrix.get(module_key, {}).get("EXPORT", False),
                )
            elif not module_enabled:
                matrix[module_key] = (False, False, False, False, False, False)
            else:
                matrix[module_key] = (
                    view_access,
                    create_access,
                    edit_access,
                    delete_access,
                    False,
                    False,
                )

        return {"matrix": matrix, "action_ids": action_ids}

    def _map_master_actions(self, master_data):
        """Procesa el JSON de /admin/modulos/con-acciones para crear el mapa de IDs maestro."""
        master_map = {}
        if not isinstance(master_data, list):
            return master_map

        for item in master_data:
            mod_code = item.get("codigo", "").upper()
            mod_key = self._resolve_module_key(mod_code)
            
            if mod_key not in master_map:
                master_map[mod_key] = {
                    "VIEW": None, "CREATE": None, "EDIT": None, 
                    "DELETE": None, "APPROVE": None, "EXPORT": None
                }
            
            # Procesamos la lista de acciones anidada
            acciones = item.get("acciones", [])
            for acc in acciones:
                acc_code = acc.get("codigo", "").upper()
                acc_id = acc.get("id")
                
                action = self._detect_action(acc_code)
                if action:
                    col_key = action.upper()
                    master_map[mod_key][col_key] = acc_id
                    
        return master_map

    @staticmethod
    def _normalize_text(value):
        return str(value or "").strip().lower()

    def _detect_action(self, text):
        # Normalizamos el texto para buscar tokens sin importar mayúsculas
        text = text.lower()
        view_tokens = ["view", "ver", "read", "leer", "list", "listar", "get", "consulta", "consultar"]
        create_tokens = ["create", "crear", "new", "nuevo", "alta", "insert", "registrar"]
        edit_tokens = ["edit", "editar", "update", "actualizar", "modificar", "modifica", "write", "escribir"]
        delete_tokens = ["delete", "eliminar", "remove", "borrar", "quitar"]
        approve_tokens = ["approve", "aprobar", "autorizar", "validar", "firma", "firmar"]
        export_tokens = ["export", "exportar", "download", "descargar", "csv", "excel", "pdf"]

        if any(token in text for token in delete_tokens): return "delete"
        if any(token in text for token in create_tokens): return "create"
        if any(token in text for token in edit_tokens): return "edit"
        if any(token in text for token in view_tokens): return "view"
        if any(token in text for token in approve_tokens): return "approve"
        if any(token in text for token in export_tokens): return "export"
        return None

    def _resolve_module_key(self, code):
        """Resuelve el código de módulo interno basado en el código recibido de la API o alias."""
        code = code.upper()
        # Coincidencia directa (ej: 'EIPD' == 'EIPD')
        for _, key in self.modules:
            if key == code:
                return key
        
        # Coincidencia por alias (ej: 'ACTIVO' -> 'INVENTARIO')
        code_lower = code.lower()
        for key, aliases in self.module_aliases.items():
            if any(alias in code_lower for alias in aliases):
                return key
        return code

    def _populate_user_list(self):
        search_term = self.search.text().strip().lower() if hasattr(self, "search") else ""
        self.users_list.clear()

        if not self.users_data:
            return

        selected_item = None
        first_item = None

        for index, user in enumerate(self.users_data):
            blob = f"{user['name']} {user['email']} {user['id']}".lower()
            if search_term and search_term not in blob:
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, index)
            card_widget = self._user_card_widget(
                user,
                index == self.current_user_index,
                index,
            )
            item.setSizeHint(card_widget.sizeHint())
            self.users_list.addItem(item)
            self.users_list.setItemWidget(item, card_widget)

            if first_item is None:
                first_item = item
            if index == self.current_user_index:
                selected_item = item

        if selected_item is None and first_item is not None:
            selected_item = first_item
            self.current_user_index = selected_item.data(Qt.UserRole)

        if selected_item is not None:
            self.users_list.setCurrentItem(selected_item)

    def _user_card_widget(self, user, is_selected, user_index):
        card = QFrame()
        card.setObjectName("userCardSelected" if is_selected else "userCard")

        name = QLabel(user["name"])
        name.setObjectName("userNameSelected" if is_selected else "userName")
        email = QLabel(user["email"])
        email.setObjectName("userTextSelected" if is_selected else "userText")
        user_id = QLabel(user["id"])
        user_id.setObjectName("userTextSelected" if is_selected else "userText")

        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(name)
        left.addWidget(email)
        left.addWidget(user_id)

        status = QPushButton(user["status"])
        status.setCursor(Qt.PointingHandCursor if self.api.is_admin else Qt.ArrowCursor)
        status.setEnabled(self.api.is_admin and bool(user.get("backend_id")))
        status_name = user["status"].lower()
        status.setObjectName(
            "statusBadgeInactive" if "inactivo" in status_name else "statusBadgeActive"
        )
        status.clicked.connect(
            lambda _checked=False, idx=user_index: self._on_toggle_user_status(idx)
        )

        packs_count = int(user.get("packs", 0) or 0)
        packs = QLabel("" if packs_count <= 0 else f"{packs_count} pack(s)")
        packs.setObjectName("userTextSelected" if is_selected else "userText")
        packs.setAlignment(Qt.AlignRight)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignTop | Qt.AlignRight)
        right.addWidget(status, alignment=Qt.AlignRight)
        right.addStretch()
        right.addWidget(packs, alignment=Qt.AlignRight)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addLayout(left)
        layout.addStretch()
        layout.addLayout(right)
        return card

    def _on_toggle_user_status(self, user_index):
        if not self.api.is_admin:
            return
        if user_index < 0 or user_index >= len(self.users_data):
            return

        user = self.users_data[user_index]
        backend_id = user.get("backend_id")
        if not backend_id:
            return

        next_active = user.get("status", "Inactivo") != "Activo"
        self.loading_overlay.show_loading()

        def do_toggle():
            return self.user_service.update_estado(backend_id, next_active)

        self.status_toggle_worker = ApiWorker(do_toggle)
        self.status_toggle_worker.finished.connect(
            lambda result, idx=user_index: self._on_toggle_user_status_success(idx, result)
        )
        self.status_toggle_worker.error.connect(self._on_toggle_user_status_error)
        self.status_toggle_worker.start()

    def _on_toggle_user_status_success(self, user_index, result):
        self.loading_overlay.hide_loading()
        is_active = bool(result.get("is_active", False))

        if 0 <= user_index < len(self.users_data):
            self.users_data[user_index]["status"] = "Activo" if is_active else "Inactivo"
            self.current_user_index = user_index
            self._populate_user_list()
            self._update_matrix_for_user(user_index)

    def _on_toggle_user_status_error(self, error):
        self.loading_overlay.hide_loading()
        QMessageBox.warning(
            self,
            "Usuarios / Roles",
            f"No fue posible actualizar el estado del usuario.\n\nDetalle: {error}",
        )

    def _on_user_selected(self, item):
        user_index = item.data(Qt.UserRole)
        if user_index is None:
            return
        
        # Cambiamos el índice y refrescamos visualmente la lista
        self.current_user_index = user_index
        self._populate_user_list()
        
        # Gatillamos la carga de datos frescos desde la API específicamente para este usuario
        self._refresh_user_matrix_from_api(user_index)

    def _on_search_changed(self, _text):
        self._populate_user_list()
        if self.current_user_index >= 0:
            self._update_matrix_for_user(self.current_user_index)

    def _refresh_user_matrix_from_api(self, user_index):
        """Consulta la API para obtener los permisos más recientes del usuario seleccionado."""
        if user_index < 0 or user_index >= len(self.users_data):
            return

        user = self.users_data[user_index]
        backend_id = user.get("backend_id")
        
        # Si no hay ID de backend, solo actualizamos con lo que tenemos
        if not backend_id:
            self._update_matrix_for_user(user_index)
            return

        def fetch_fresh_perms():
            return self.user_service.get_permissions(backend_id)

        def on_fresh_data_ready(perms_payload):
            # 1. Cargamos primero los datos frescos desde la API
            api_results = self._map_permissions_to_modules(
                perms_payload, 
                self.privilege_name_by_code
            )
            
            # 2. Establecemos los permisos de la API como base (separando matriz de IDs)
            user["permissions"] = api_results.get("matrix", {})
            user["action_ids"] = api_results.get("action_ids", {})
            
            # 3. Mezclamos inteligentemente: La API es ley para los módulos que reporta,
            # pero si un módulo NO viene en la API (permisos vacíos), dejamos actuar a la cache local
            api_modules = set(item.get("modulo_codigo", "").upper() for item in perms_payload.get("permisos", []))
            # Resolvemos esos códigos a nuestras keys internas
            api_keys = set(self._resolve_module_key(m) for m in api_modules)
            
            # Aplicamos la cache local solo para lo que el backend NO conoce aún
            self._apply_selective_override(user, exclude_keys=api_keys)
            
            # 4. Si el usuario sigue seleccionado, actualizamos la tabla en pantalla
            if self.current_user_index == user_index:
                self._update_matrix_for_user(user_index)

        # Guardamos la referencia en la instancia de la clase para evitar que se destruya prematuramente
        self.refresh_worker = ApiWorker(fetch_fresh_perms)
        self.refresh_worker.finished.connect(on_fresh_data_ready)
        self.refresh_worker.start()

    def _update_matrix_for_user(self, user_index):
        if not self.users_data:
            return

        user = self.users_data[user_index]
        self.selected_user_hint.setText(f"Usuario seleccionado: {user['name']} ({user['id']})")

        for row, (_, module_key) in enumerate(self.modules):
            (
                view_access,
                create_access,
                edit_access,
                delete_access,
                approve_access,
                export_access,
            ) = user["permissions"].get(
                module_key, (False, False, False, False, False, False)
            )
            self._set_permission_value(row, 1, view_access)
            self._set_permission_value(row, 2, create_access)
            self._set_permission_value(row, 3, edit_access)
            self._set_permission_value(row, 4, delete_access)
            self._set_permission_value(row, 5, approve_access)
            self._set_permission_value(row, 6, export_access)

        self._update_edit_hint()

    def _set_permission_value(self, row, col, enabled):
        item = QTableWidgetItem("✓" if enabled else "-")
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setForeground(Qt.GlobalColor.darkGreen if enabled else Qt.GlobalColor.gray)
        self.table.setItem(row, col, item)

    def _on_permission_cell_clicked(self, row, col):
        if col == 0:
            return
        if not self.users_data:
            return
        if self.current_user_index < 0 or self.current_user_index >= len(self.users_data):
            return

        user = self.users_data[self.current_user_index]
        module_key = self.modules[row][1]
        
        # Obtenemos los 6 permisos actuales
        current_permissions = list(
            user["permissions"].get(module_key, (False, False, False, False, False, False))
        )
        
        perm_idx = col - 1
        if perm_idx < 0 or perm_idx >= len(current_permissions):
            return

        # Calculamos el nuevo estado
        next_state = not current_permissions[perm_idx]
        
        # Identificamos el accion_id para la API real
        action_names = ["VIEW", "CREATE", "EDIT", "DELETE", "APPROVE", "EXPORT"]
        action_name = action_names[perm_idx]
        
        # 1. Intentamos obtener el ID específico del usuario (si ya tenía el permiso)
        accion_id = user.get("action_ids", {}).get(module_key, {}).get(action_name)
        
        # 2. Si no lo tiene, lo buscamos en el CATÁLOGO MAESTRO (de /admin/modulos/con-acciones)
        if not accion_id:
            accion_id = self.master_action_ids.get(module_key, {}).get(action_name)

        backend_user_id = user.get("backend_id")

        # Si tenemos los datos necesarios, enviamos a la API
        if accion_id and backend_user_id:
            # Imprimimos en consola para seguimiento interno (puedes verlo en el terminal)
            print(f"Enviando PATCH para Usuario: {backend_user_id}, Accion: {accion_id}, Estado: {next_state}")
            
            self.loading_overlay.show_loading()
            
            def do_patch():
                return self.user_service.update_permiso(backend_user_id, accion_id, next_state)
            
            def on_patch_done(result):
                self.loading_overlay.hide_loading()
                # Actualizamos la UI solo si la API respondió OK
                current_permissions[perm_idx] = next_state
                user["permissions"][module_key] = tuple(current_permissions)
                self._set_permission_value(row, col, next_state)
                self._persist_user_permissions_override(user)
                
            def on_patch_error(err):
                self.loading_overlay.hide_loading()
                QMessageBox.warning(self, "Error", f"No se pudo actualizar el permiso en el servidor:\n{err}")

            self.perm_update_worker = ApiWorker(do_patch)
            self.active_workers.append(self.perm_update_worker) # Mantenemos referencia viva
            
            def on_finished():
                if self.perm_update_worker in self.active_workers:
                    self.active_workers.remove(self.perm_update_worker)

            self.perm_update_worker.finished.connect(lambda _: on_finished())
            self.perm_update_worker.finished.connect(on_patch_done)
            self.perm_update_worker.error.connect(on_patch_error)
            self.perm_update_worker.start()
        else:
            # Si es modo mockup (sin ID real), solo actualizamos localmente
            current_permissions[perm_idx] = next_state
            user["permissions"][module_key] = tuple(current_permissions)
            self._set_permission_value(row, col, next_state)
            self._persist_user_permissions_override(user)

    def _update_edit_hint(self):
        self.matrix_edit_hint.setText(
            "Haz clic en una celda para activar/desactivar permisos. "
            "Los cambios se guardan automáticamente en el servidor."
        )

    def _load_permissions_overrides(self):
        cached = self.cache_manager.get(self.permissions_cache_key)
        return cached if isinstance(cached, dict) else {}

    def _persist_user_permissions_override(self, user):
        user_cache_id = self._user_cache_id(user)
        if not user_cache_id:
            return

        permissions = user.get("permissions", {})
        serialized = {}
        for module_key, value in permissions.items():
            bools = list(value)
            # Aseguramos que siempre haya 6 elementos para la cache
            while len(bools) < 6:
                bools.append(False)
            serialized[module_key] = [bool(v) for v in bools[:6]]

        self.permissions_overrides[user_cache_id] = serialized
        self.cache_manager.set(self.permissions_cache_key, self.permissions_overrides)

    def _apply_permissions_override(self, user):
        user_cache_id = self._user_cache_id(user)
        if not user_cache_id:
            return

        override = self.permissions_overrides.get(user_cache_id)
        if not isinstance(override, dict):
            return

        for module_key, values in override.items():
            if not isinstance(values, list):
                continue
            # Cargamos los 6 booleanos desde la cache
            bools = [bool(v) for v in values[:6]]
            while len(bools) < 6:
                bools.append(False)
            user["permissions"][module_key] = tuple(bools)

    @staticmethod
    def _user_cache_id(user):
        return str(user.get("backend_id") or user.get("id") or "")

    def resizeEvent(self, event):
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.resize(self.size())
        super().resizeEvent(event)
    def _apply_selective_override(self, user, exclude_keys):
        """Aplica overrides solo para los módulos que no están en la lista de exclusión (API records)."""
        user_cache_id = self._user_cache_id(user)
        if not user_cache_id: return
        override = self.permissions_overrides.get(user_cache_id)
        if not isinstance(override, dict): return

        for module_key, values in override.items():
            if module_key in exclude_keys: continue
            bools = [bool(v) for v in values[:6]]
            while len(bools) < 6: bools.append(False)
            user["permissions"][module_key] = tuple(bools)
