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
from PySide6.QtCore import Qt, QTimer

from src.components.loading_overlay import LoadingOverlay
from src.core.api_client import ApiClient
from src.services.cache_manager import CacheManager
from src.services.user_service import UserService
from src.workers.api_worker import ApiWorker
from src.services.permission_service import PermissionService
from src.components.alert_dialog import AlertDialog


class UsuariosView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)
        self.is_loading = False
        self.api = ApiClient()
        self.user_service = UserService()
        self.cache_manager = CacheManager()
        self.permissions_cache_key = "usuarios_permissions_v2"
        self.permissions_overrides = {}
        self.permission_service = PermissionService()
        self.perm_module = "USUARIOS"

        self.current_page = 1
        self.page_size = 10
        self.has_next = False
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(500)
        self.search_timer.timeout.connect(self._on_search_timeout)

        self.current_user_index = 0
        self.status_toggle_worker = None
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
            ("Seguimiento de Riesgos", "SEGUIMIENTO"),
            ("Reportes", "REPORTES"),
            ("Auditoría", "AUDITORIA"),
        ]

        self.module_aliases = {
            "INVENTARIO": ["inventario", "activo", "activos"],
            "EIPD": ["eipd", "pia"],
            "USUARIOS": ["usuario", "usuarios", "rol", "roles"],
            "RAT": ["rat"],
            "TRAZABILIDAD": ["trazabilidad", "trace"],
            "SEGUIMIENTO": ["seguimiento", "riesgos", "followup"],
            "REPORTES": ["reportes", "dashboard", "reporte"],
            "AUDITORIA": ["auditoria", "log", "audit", "historial", "admin"],
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

        # 🛡️ Control de Acceso del Módulo
        if not self.permission_service.has_module_access(self.perm_module):
            self._show_permission_block()
        else:
            self._load_backend_data()

    def refresh(self):
        """Actualizar los datos al navegar al módulo"""
        if self.permission_service.has_module_access(self.perm_module):
            self._load_backend_data(force_refresh=False)


    def _convert_local_perms_to_payload(self, local_perms: dict):
        """Convierte la matriz de memoria de PermissionService al formato que espera el mapeador."""
        api_format = []
        # local_perms es Dict[str, Dict[str, bool]] como {'INVENTARIO': {'VER': True, ...}}
        for mod_key, actions in local_perms.items():
            for action_key, allowed in actions.items():
                if allowed: # Solo incluimos los permitidos para mayor claridad
                    api_format.append({
                        "modulo_codigo": mod_key,
                        "accion_codigo": action_key,
                        "permitido": True
                    })
        return {"permisos": api_format}

    def _show_permission_block(self):
        """Muestra un mensaje de bloqueo cuando el usuario no tiene permiso VER."""
        overlay = QFrame(self)
        overlay.setObjectName("permissionBlockOverlay")
        overlay.setStyleSheet("""
            QFrame#permissionBlockOverlay {
                background-color: transparent;
            }
            QLabel {
                color: #64748b;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        l = QVBoxLayout(overlay)
        l.setAlignment(Qt.AlignCenter)
        
        from utils import icon
        icon_label = QLabel()
        icon_label.setPixmap(icon("src/resources/icons/lock.svg").pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        
        msg_label = QLabel("No tiene permisos para el módulo de Usuarios / Roles.")
        msg_label.setAlignment(Qt.AlignCenter)
        
        contact_label = QLabel("Este módulo está restringido a administradores o personal autorizado.")
        contact_label.setStyleSheet("font-size: 12px; font-weight: normal; margin-top: 8px;")
        contact_label.setAlignment(Qt.AlignCenter)
        
        l.addWidget(icon_label)
        l.addWidget(msg_label)
        l.addWidget(contact_label)
        overlay.show()
        
        # Superponer al layout principal
        self.layout().addWidget(overlay)
        # Ocultar el resto del contenido si es necesario o el overlay lo tapará

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
        self.search.textChanged.connect(self._on_search_text_changed)
        self.search.setFixedWidth(360)

        self.users_list = QListWidget()
        self.users_list.setObjectName("userListModern")
        self.users_list.setFrameShape(QFrame.NoFrame)
        self.users_list.setSpacing(10)
        self.users_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.users_list.itemClicked.connect(self._on_user_selected)

        self.btn_prev = QPushButton("( Anterior")
        self.btn_prev.setObjectName("secondaryButton")
        self.btn_prev.clicked.connect(self._on_prev_page)
        self.btn_prev.setEnabled(False)

        self.lbl_page = QLabel("Página 1 de 1")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setObjectName("pageSubtitle")

        self.btn_next = QPushButton("Siguiente )")
        self.btn_next.setObjectName("secondaryButton")
        self.btn_next.clicked.connect(self._on_next_page)
        self.btn_next.setEnabled(False)
        
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()

        layout = QVBoxLayout(card)
        layout.addLayout(top_titles)
        layout.addWidget(self.search, alignment=Qt.AlignLeft)
        layout.addSpacing(8)
        layout.addWidget(self.users_list)
        layout.addLayout(pagination_layout)

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

    def _load_backend_data(self, force_refresh=False):
        if self.is_loading:
            return
            
        self.is_loading = True
        self.loading_overlay.show_loading()
        
        current_page_val = self.current_page
        current_size_val = self.page_size
        current_search_val = self.search.text().strip()

        def fetch_data():
            result = {
                "users": [],
                "list_users_api_available": True,
                "permissions_update_api_available": False,
                "privilege_name_by_code": {},
                "has_next": False,
                "total": 0,
            }

            me = self.user_service.get_me()
            
            # Intentamos obtener permisos propios, si falla (403) asumimos permisos vacíos.
            try:
                me_permissions = self.user_service.get_permissions(str(me.get("id")))
            except Exception as e:
                print(f"No se pudieron cargar permisos propios de la nube (Caso usuario no-admin): {e}")
                # FALLBACK CRÍTICO: Usamos lo que PermissionService ya sabe que tiene el usuario por su sesión
                local_perms = self.permission_service._user_permissions
                me_permissions = self._convert_local_perms_to_payload(local_perms)


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

            users_list = []
            # Cargamos la lista de usuarios si tiene permiso VER el módulo
            if self.permission_service.has_module_access(self.perm_module):
                try:
                    search_nombre = None
                    search_rut = None
                    search_email = None

                    if current_search_val:
                        if "@" in current_search_val:
                            search_email = current_search_val
                        # Identificamos si el término contiene dígitos para inferir que es un RUT
                        elif any(char.isdigit() for char in current_search_val):
                            search_rut = current_search_val
                        else:
                            search_nombre = current_search_val

                    paged_response = None
                    cache_key = f"usuarios_list_p{current_page_val}_s{current_size_val}_q{current_search_val}"
                    if not force_refresh:
                        paged_response = self.cache_manager.get(cache_key)
                    
                    if not paged_response:
                        paged_response = self.user_service.list_users(
                            page=current_page_val,
                            size=current_size_val,
                            nombre=search_nombre,
                            rut=search_rut,
                            email=search_email
                        )
                        self.cache_manager.set(cache_key, paged_response)
                        
                    users_list = paged_response.get("items", [])
                    result["has_next"] = paged_response.get("has_next", False)
                    result["total"] = paged_response.get("total", 0)
                except Exception as e:
                    print(f"Error cargando usuarios: {e}")
                    result["list_users_api_available"] = False

            if not users_list:
                users_list = [me]

            for user in users_list:
                user_id = str(user.get("id", ""))
                perms_payload = me_permissions if user_id == str(me.get("id")) else None
                is_loaded = perms_payload is not None
                
                if perms_payload is None:
                    perms_payload = {
                        "permisos": []
                    }

                user_dict = self._build_user_from_api(
                    user,
                    perms_payload,
                    result["privilege_name_by_code"],
                )
                user_dict["permissions_loaded"] = is_loaded
                result["users"].append(user_dict)

            return result

        self.worker = ApiWorker(fetch_data)
        self.worker.finished.connect(self._on_data_loaded)
        self.worker.error.connect(self._on_data_error)
        self.worker.start()

    def _on_data_loaded(self, data):
        self.is_loading = False
        self.loading_overlay.hide_loading()
        self.users_data = data.get("users", [])
        self.has_next = data.get("has_next", False)
        self.list_users_api_available = data.get("list_users_api_available", True)
        self.permissions_update_api_available = data.get(
            "permissions_update_api_available", False
        )
        self.privilege_name_by_code = data.get("privilege_name_by_code", {})
        self.master_action_ids = data.get("master_action_ids", {})
        self.permissions_overrides = self._load_permissions_overrides()
        
        # Ordenar usuarios por RUT ascendente (desde el 1er dígito)
        self.users_data.sort(key=self._rut_sort_key, reverse=False)
        
        total = data.get("total", 0)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)

        if hasattr(self, "btn_prev"):
            self.btn_prev.setEnabled(self.current_page > 1)
        if hasattr(self, "btn_next"):
            self.btn_next.setEnabled(self.has_next)
        if hasattr(self, "lbl_page"):
            self.lbl_page.setText(f"Página {self.current_page} de {total_pages}")

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
                    "permissions_loaded": True
                }
            ]
        else:
            for user in self.users_data:
                # Solo aplicamos el mockup (overrides) si el usuario NO tiene permisos reales del backend
                # Si el usuario ya tiene permisos (vienen del API), esos mandan sobre la cache.
                if user.get("permissions_loaded", False):
                    has_real_perms = any(any(v) for v in user["permissions"].values())
                    if not has_real_perms:
                        self._apply_permissions_override(user)

        self.current_user_index = 0
        self._populate_user_list()
        
        if self.users_data and not self.users_data[self.current_user_index].get("permissions_loaded", False):
            self._load_user_permissions(self.current_user_index)
        else:
            self._update_matrix_for_user(self.current_user_index)

    def _on_data_error(self, error):
        self.is_loading = False
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
            "rol_ris": user.get("rol_ris"),
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
            approve_access = False
            export_access = False

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

            # 🛡️ COMBINACIÓN INTELIGENTE (Bug Fix):
            # Priorizamos permisos reales del backend, pero si no existen (False),
            # tratamos de ver si tiene acceso por perfil heredado.
            # Excepto si el módulo está explícitamente reportado por API (entonces la API manda).
            
            is_in_api = module_key in real_backend_matrix
            
            if is_in_api:
                # La API tiene registros para este módulo
                m = real_backend_matrix[module_key]
                view_val = m.get("VIEW", False)
                
                # 🛡️ REGLA DE ORO: Si tiene cualquier permiso (CREAR, EDITAR, etc), debe tener VER.
                any_perm_action = any([
                    m.get("CREATE", False),
                    m.get("EDIT", False),
                    m.get("DELETE", False),
                    m.get("APPROVE", False),
                    m.get("EXPORT", False)
                ])
                
                matrix[module_key] = (
                    view_val or any_perm_action, # VER implícito
                    m.get("CREATE", False),
                    m.get("EDIT", False),
                    m.get("DELETE", False),
                    m.get("APPROVE", False),
                    m.get("EXPORT", False),
                )
            else:
                # No hay registro granular en API, usamos permisos por perfil/privilegios
                # Nota: Si el perfil dice que SI (module_enabled), habilitamos VER
                any_granular_action = any([create_access, edit_access, delete_access, approve_access, export_access])
                matrix[module_key] = (
                    view_access or module_enabled or any_granular_action,
                    create_access,
                    edit_access,
                    delete_access,
                    approve_access,
                    export_access,
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
        self.users_list.clear()

        if not self.users_data:
            return

        selected_item = None
        first_item = None

        for index, user in enumerate(self.users_data):
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

        # 🔒 BLOQUEO ESTRICTO DE BOTONES: Solo el ADMINISTRADOR GLOBAL puede modificar estados
        is_global_admin = hasattr(self.permission_service, "_is_admin") and self.permission_service._is_admin
        can_edit = is_global_admin
        can_delete = is_global_admin

        status = QPushButton(user["status"])
        status.setObjectName(
            "statusBadgeInactive" if "inactivo" in user["status"].lower() else "statusBadgeActive"
        )
        if not can_edit:
            status.setAttribute(Qt.WA_TransparentForMouseEvents)
            status.setCursor(Qt.ArrowCursor)
        else:
            status.setCursor(Qt.PointingHandCursor)
            status.clicked.connect(
                lambda _checked=False, idx=user_index: self._on_toggle_user_status(idx)
            )

        packs_count = int(user.get("packs", 0) or 0)
        packs = QLabel("" if packs_count <= 0 else f"{packs_count} pack(s)")
        packs.setObjectName("userTextSelected" if is_selected else "userText")
        packs.setAlignment(Qt.AlignRight)

        badges_layout = QHBoxLayout()
        badges_layout.setAlignment(Qt.AlignRight)
        badges_layout.setSpacing(8)

        if user.get("rol_ris") == "PENDIENTE_CONFIGURACION":
            btn_add = QPushButton("Registrar")
            btn_add.setObjectName("statusBadgePending")
            if not can_edit:
                btn_add.setAttribute(Qt.WA_TransparentForMouseEvents)
                btn_add.setCursor(Qt.ArrowCursor)
            else:
                btn_add.setCursor(Qt.PointingHandCursor)
                btn_add.clicked.connect(
                    lambda _checked=False, idx=user_index: self._on_registrar_clicked(idx)
                )
            badges_layout.addWidget(btn_add)

        badges_layout.addWidget(status)

        btn_delete = QPushButton("Eliminar")
        btn_delete.setObjectName("statusBadgeDanger")
        if not can_delete:
            btn_delete.setAttribute(Qt.WA_TransparentForMouseEvents)
            btn_delete.setCursor(Qt.ArrowCursor)
        else:
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.clicked.connect(
                lambda _checked=False, idx=user_index: self._on_delete_user_clicked(idx)
            )
        badges_layout.addWidget(btn_delete)

        right = QVBoxLayout()
        right.setSpacing(4) # Espaciado más ajustado entre botones
        right.setAlignment(Qt.AlignTop | Qt.AlignRight)
        right.addLayout(badges_layout)
        
        if packs_count > 0:
            right.addStretch()
            right.addWidget(packs, alignment=Qt.AlignRight)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addLayout(left)
        layout.addStretch()
        layout.addLayout(right)
        return card

    def _on_registrar_clicked(self, user_index):
        # 🔒 SEGURIDAD: Solo ADMIN
        if not hasattr(self.permission_service, "_is_admin") or not self.permission_service._is_admin:
            return
        if user_index < 0 or user_index >= len(self.users_data):
            return

        user = self.users_data[user_index]
        
        from pathlib import Path
        from src.components.generic_form_dialog import GenericFormDialog
        
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        config_path = base_dir / "src" / "config" / "formularios" / "usuarios_registro.json"
        
        # Instanciamos el diálogo base utilizando la ruta absoluta al JSON
        dialog = GenericFormDialog(str(config_path), parent=self)
        
        # Pre-cargamos los identificadores únicos y dejamos nombre y correo vacíos
        dialog.asset_data = {
            "rut": user.get("id", ""),
            "nombre": "",
            "email": "",
            "backend_id": user.get("backend_id")
        }
        dialog._try_set_values()
        
        # Ocultar o simular carga si es necesario, pero aquí solo se muestra el form
        if dialog.exec():
            # Si el modal se guardó con éxito (HTTP 200), refrescar la lista para remover el status PENDIENTE
            # 🛡️ REGLA SINGDAP: Activar VER en USUARIOS automáticamente al registrar
            try:
                backend_id = dialog.asset_data.get("backend_id")
                usuarios_view_acc_id = self.master_action_ids.get("USUARIOS", {}).get("VIEW")
                if backend_id and usuarios_view_acc_id:
                    print(f"[REGISTRO] Forzando permiso VER en USUARIOS para {backend_id}...")
                    self.user_service.update_permiso(backend_id, usuarios_view_acc_id, True)
            except Exception as e:
                print(f"Error forzando permiso post-registro: {e}")

            self.cache_manager.remove_prefix("usuarios_list_")
            self._load_backend_data(force_refresh=True)

    def _on_toggle_user_status(self, user_index):
        # 🔒 SEGURIDAD: Solo ADMIN
        if not hasattr(self.permission_service, "_is_admin") or not self.permission_service._is_admin:
            return
        if user_index < 0 or user_index >= len(self.users_data):
            return

        user = self.users_data[user_index]
        backend_id = user.get("backend_id")
        if not backend_id:
            return

        is_currently_active = user.get("status", "Inactivo") == "Activo"
        next_active = not is_currently_active

        accion_str = "activación" if next_active else "desactivación"
        titulo_str = "Confirmar Activación" if next_active else "Confirmar Desactivación"
        
        msg = f"Confirmar {accion_str} de NOMBRE : {user.get('name', 'N/A')}, RUT : {user.get('id', 'N/A')}"
        dialog = AlertDialog(
            title=titulo_str,
            message=msg,
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Confirmar",
            cancel_text="Cancelar",
            parent=self
        )
        if not dialog.exec():
            return

        self.loading_overlay.show_loading()

        def do_toggle():
            return self.user_service.update_estado(backend_id, next_active)

        self.status_toggle_worker = ApiWorker(do_toggle)
        self.status_toggle_worker.finished.connect(
            lambda result, idx=user_index: self._on_toggle_user_status_success(idx, result)
        )
        self.status_toggle_worker.error.connect(self._on_toggle_user_status_error)
        self.status_toggle_worker.start()

    def _on_delete_user_clicked(self, user_index):
        # 🔒 SEGURIDAD: Solo ADMIN
        if not hasattr(self.permission_service, "_is_admin") or not self.permission_service._is_admin:
            return
        if user_index < 0 or user_index >= len(self.users_data):
            return

        user = self.users_data[user_index]
        backend_id = user.get("backend_id")
        if not backend_id:
            # Si no hay backend_id (ej: usuario mockup o no registrado), solo borramos localmente
            msg = f"¿Está seguro de eliminar este registro local?\n\nNombre: {user.get('name')}\nRUT: {user.get('id')}"
            dialog = AlertDialog(
                title="Confirmar Eliminación",
                message=msg,
                icon_path="src/resources/icons/alert_warning.svg",
                confirm_text="Eliminar",
                cancel_text="Cancelar",
                parent=self
            )
            if dialog.exec():
                self.users_data.pop(user_index)
                self.current_user_index = 0
                self._populate_user_list()
            return

        msg = f"¿Está seguro de eliminar definitivamente a este usuario?\n\nNombre: {user.get('name')}\nRUT: {user.get('id')}\n\nEsta acción NO se puede deshacer."
        dialog = AlertDialog(
            title="Confirmar Eliminación Definitiva",
            message=msg,
            icon_path="src/resources/icons/alert_warning.svg",
            confirm_text="Eliminar Permanentemente",
            cancel_text="Cancelar",
            parent=self
        )
        if not dialog.exec():
            return

        self.loading_overlay.show_loading()

        def do_delete():
            return self.user_service.delete_user(backend_id)

        worker = ApiWorker(do_delete)
        self.active_workers.append(worker)
        worker.finished.connect(lambda _, idx=user_index: self._on_delete_user_success(idx))
        worker.error.connect(self._on_delete_user_error)
        worker.start()

    def _on_delete_user_success(self, user_index):
        self.loading_overlay.hide_loading()
        if 0 <= user_index < len(self.users_data):
            self.users_data.pop(user_index)
            self.current_user_index = 0
            self._populate_user_list()
            if self.users_data:
                self._update_matrix_for_user(0)
            
            # Limpiar cache local de este usuario
            user_cache_id = self._user_cache_id({"backend_id": None, "id": None}) # Dummy call to get logic
            # En realidad mejor recargar todo y limpiar la caché completa de la lista
            self.cache_manager.remove_prefix("usuarios_list_")
            self._load_backend_data(force_refresh=True)

    def _on_delete_user_error(self, error):
        self.loading_overlay.hide_loading()
        QMessageBox.warning(
            self,
            "Error",
            f"No fue posible eliminar el usuario.\n\nDetalle: {error}",
        )

    def _on_toggle_user_status_success(self, user_index, result):
        self.loading_overlay.hide_loading()
        is_active = bool(result.get("is_active", False))

        if 0 <= user_index < len(self.users_data):
            self.users_data[user_index]["status"] = "Activo" if is_active else "Inactivo"
            self.current_user_index = user_index
            self._populate_user_list()
            self._update_matrix_for_user(user_index)
            self.cache_manager.remove_prefix("usuarios_list_")
            
            # 🛡️ REGLA SINGDAP: Al activar un usuario, asegurar VER en USUARIOS
            if is_active:
                try:
                    backend_id = self.users_data[user_index].get("backend_id")
                    usuarios_view_acc_id = self.master_action_ids.get("USUARIOS", {}).get("VIEW")
                    if backend_id and usuarios_view_acc_id:
                        print(f"[ACTIVACIÓN] Asegurando VER en USUARIOS para {backend_id}...")
                        self.user_service.update_permiso(backend_id, usuarios_view_acc_id, True)
                except Exception as e:
                    print(f"Error asegurando permiso en activación: {e}")

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
        
        user = self.users_data[user_index]
        if not user.get("permissions_loaded", False):
            self._load_user_permissions(user_index)
        else:
            # Volvemos al comportamiento original: solo actualizamos la vista con los datos ya cargados/modificados en memoria
            self._update_matrix_for_user(user_index)

    def _load_user_permissions(self, user_index):
        if user_index < 0 or user_index >= len(self.users_data):
            return
            
        user = self.users_data[user_index]
        user_id = user.get("backend_id")
        
        self.loading_overlay.show_loading()
        
        def fetch_perms():
            try:
                return self.user_service.get_permissions(user_id)
            except Exception:
                return {"permisos": []}

        def on_loaded(perms_payload):
            self.loading_overlay.hide_loading()
            
            # Validamos que el usuario siga existiendo (pudo haber cambiado de página)
            if user_index >= len(self.users_data) or self.users_data[user_index].get("backend_id") != user_id:
                return
                
            permissions = self._map_permissions_to_modules(
                perms_payload,
                self.privilege_name_by_code,
            )
            
            user["packs"] = len((perms_payload or {}).get("packs", []))
            user["permissions"] = permissions.get("matrix", {})
            user["action_ids"] = permissions.get("action_ids", {})
            user["permissions_loaded"] = True
            
            has_real_perms = any(any(v) for v in user["permissions"].values())
            if not has_real_perms:
                self._apply_permissions_override(user)
                
            self._populate_user_list()
            # Actualizamos la matriz si el usuario sigue seleccionado
            if self.current_user_index == user_index:
                self._update_matrix_for_user(user_index)
            
        def on_error(err):
            self.loading_overlay.hide_loading()
            if self.current_user_index == user_index:
                self._update_matrix_for_user(user_index)

        worker = ApiWorker(fetch_perms)
        self.active_workers.append(worker)
        
        def on_finished():
            if worker in self.active_workers:
                self.active_workers.remove(worker)
                
        worker.finished.connect(lambda _: on_finished())
        worker.finished.connect(on_loaded)
        worker.error.connect(on_error)
        worker.start()

    def _on_search_text_changed(self, _text):
        self.search_timer.start()

    def _on_search_timeout(self):
        self.current_page = 1
        self._load_backend_data(force_refresh=True)

    def _on_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._load_backend_data(force_refresh=False)

    def _on_next_page(self):
        if self.has_next:
            self.current_page += 1
            self._load_backend_data(force_refresh=False)

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
        # 🔒 BLOQUEO ESTRICTO: Solo un ADMINISTRADOR GLOBAL real puede modificar la matriz
        if not hasattr(self.permission_service, "_is_admin") or not self.permission_service._is_admin:
            return
            
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

        # 🛡️ REGLA SINGDAP: El permiso VER de USUARIOS es obligatorio para que funcionen las tareas de segundo plano
        if module_key == "USUARIOS" and perm_idx == 0 and current_permissions[perm_idx]:
            # Evitar desmarcar VER en USUARIOS
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
                print(f"DEBUG PERMS: PATCH exitoso -> {result}")
                
                # Sincronización inmediata de permisos locales
                current_permissions[perm_idx] = next_state
                user["permissions"][module_key] = tuple(current_permissions)
                self._set_permission_value(row, col, next_state)
                
                # Persistencia en cache local para que al volver siga ahí
                self._persist_user_permissions_override(user)
                
                # Actualizamos la visualización general si el usuario sigue seleccionado
                try:
                    current_idx = self.users_data.index(user)
                    if self.current_user_index == current_idx:
                        self._update_edit_hint()
                except ValueError:
                    pass

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

            # 🛡️ REGLA SINGDAP: Si se modifica CUALQUIER cosa de este usuario, asegurar que tenga VER en USUARIOS
            # para que no fallen las tareas de segundo plano.
            is_usuarios_view = (module_key == "USUARIOS" and perm_idx == 0)
            has_usuarios_view = user["permissions"].get("USUARIOS", (False,))[0]
            
            if not is_usuarios_view and not has_usuarios_view:
                usuarios_view_acc_id = self.master_action_ids.get("USUARIOS", {}).get("VIEW")
                if usuarios_view_acc_id:
                    print(f"[MATRIZ] Asegurando VER en USUARIOS por modificación colateral...")
                    # Llamada silenciosa al servicio
                    try:
                        self.user_service.update_permiso(user['backend_id'], usuarios_view_acc_id, True)
                    except: pass
                    # Actualizar localmente para que se vea el cambio tras el siguiente refresh o carga
                    perms = list(user["permissions"].get("USUARIOS", (False, False, False, False, False, False)))
                    perms[0] = True
                    user["permissions"]["USUARIOS"] = tuple(perms)
        else:
            print(f"DEBUG PERMS: No se pudo enviar PATCH. backend_user_id={backend_user_id}, accion_id={accion_id}, action_name={action_name}, module_key={module_key}")
            if not accion_id:
                QMessageBox.warning(self, "Acción no enviada", f"No se pudo guardar el permiso de '{action_name}' en BD porque faltan los IDs de maestro. Solo se guardó en caché.")
            # Si es modo mockup (sin ID real), solo actualizamos localmente
            current_permissions[perm_idx] = next_state
            user["permissions"][module_key] = tuple(current_permissions)
            self._set_permission_value(row, col, next_state)
            self._persist_user_permissions_override(user)

    def _update_edit_hint(self):
        # Solo el ADMIN GLOBAL puede modificar
        is_admin = hasattr(self.permission_service, "_is_admin") and self.permission_service._is_admin
        if not is_admin:
            self.matrix_edit_hint.setText(
                "Modo de solo lectura: Estos son sus permisos actuales y no pueden ser modificados."
            )
            # Desactivamos el cursor de puntero (mano) en la tabla para que se sienta fija
            self.table.setCursor(Qt.ArrowCursor)
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.matrix_edit_hint.setText(
                "Haz clic en una celda para activar/desactivar permisos. "
                "Los cambios se guardan automáticamente en el servidor."
            )
            self.table.setCursor(Qt.PointingHandCursor)


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

    def _rut_sort_key(self, user):
        """Retorna el RUT como string para ordenamiento ascendente por primer dígito."""
        rut = str(user.get("id", "")).strip().lower()
        if not rut or rut == "-":
            return "zzzzzz" # Enviar vacíos al final
        # Si es admin, lo dejamos al final o al principio según se prefiera, 
        # pero usualmente los RUTs numéricos van primero.
        return rut

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
