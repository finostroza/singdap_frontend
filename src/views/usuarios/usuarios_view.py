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
from src.services.user_service import UserService
from src.workers.api_worker import ApiWorker


class UsuariosView(QWidget):
    def __init__(self):
        super().__init__()
        self.loading_overlay = LoadingOverlay(self)
        self.api = ApiClient()
        self.user_service = UserService()

        self.current_user_index = 0
        self.status_toggle_worker = None
        self.users_data = []
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

        self.table = QTableWidget(len(self.modules), 6)
        self.table.setObjectName("permissionTable")
        self.table.setHorizontalHeaderLabels(
            ["Modulo", "VER", "CREAR", "EDITAR", "APROBAR", "EXPORTAR"]
        )
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setMinimumWidth(0)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 82)
        self.table.setColumnWidth(2, 82)
        self.table.setColumnWidth(3, 82)
        self.table.setColumnWidth(4, 92)
        self.table.setColumnWidth(5, 92)
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
            except Exception:
                result["privilege_name_by_code"] = {}

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
                            "packs": [],
                            "perfiles": [],
                            "roles": [],
                            "privileges": [],
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

        if not self.users_data:
            self.users_data = [
                {
                    "name": "Sin datos",
                    "email": "",
                    "id": "-",
                    "status": "Inactivo",
                    "packs": 0,
                    "permissions": {
                        module_key: (False, False, False, False, False)
                        for _, module_key in self.modules
                    },
                }
            ]

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
            "permissions": permissions,
        }

    def _map_permissions_to_modules(self, payload, privilege_name_by_code):
        payload = payload or {}
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
                else:
                    view_access = True

            if not module_enabled:
                matrix[module_key] = (False, False, False, False, False)
            else:
                matrix[module_key] = (
                    view_access,
                    create_access,
                    edit_access,
                    False,
                    False,
                )

        return matrix

    @staticmethod
    def _normalize_text(value):
        return str(value or "").strip().lower()

    def _detect_action(self, text):
        view_tokens = ["view", "ver", "read", "leer", "list", "listar", "get", "consulta", "consultar"]
        create_tokens = ["create", "crear", "new", "nuevo", "alta", "insert", "registrar"]
        edit_tokens = ["edit", "editar", "update", "actualizar", "modificar", "modifica", "write", "escribir", "delete", "eliminar"]

        if any(token in text for token in create_tokens):
            return "create"
        if any(token in text for token in edit_tokens):
            return "edit"
        if any(token in text for token in view_tokens):
            return "view"
        return None

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
        self.current_user_index = user_index
        self._populate_user_list()
        self._update_matrix_for_user(user_index)

    def _on_search_changed(self, _text):
        self._populate_user_list()
        self._update_matrix_for_user(self.current_user_index)

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
                approve_access,
                export_access,
            ) = user["permissions"].get(
                module_key, (False, False, False, False, False)
            )
            self._set_permission_value(row, 1, view_access)
            self._set_permission_value(row, 2, create_access)
            self._set_permission_value(row, 3, edit_access)
            self._set_permission_value(row, 4, approve_access)
            self._set_permission_value(row, 5, export_access)

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
        if not self.api.is_admin:
            return
        if not self.permissions_update_api_available:
            if not self.warned_missing_update_api:
                self.warned_missing_update_api = True
                QMessageBox.information(
                    self,
                    "Usuarios / Roles",
                    "No existe API backend para actualizar permisos por usuario/pantalla.\n"
                    "Se requiere endpoint para activar/desactivar VER, CREAR y EDITAR.",
                )
            return

        current = self.table.item(row, col)
        enabled = bool(current and current.text() == "✓")
        self._set_permission_value(row, col, not enabled)

    def _update_edit_hint(self):
        if not self.api.is_admin:
            self.matrix_edit_hint.setText("Solo administradores pueden modificar permisos.")
            return

        if not self.list_users_api_available:
            self.matrix_edit_hint.setText(
                "API de listado de usuarios no disponible: se muestra solo el usuario autenticado."
            )
            return

        if not self.permissions_update_api_available:
            self.matrix_edit_hint.setText(
                "Edicion deshabilitada: falta endpoint backend para actualizar permisos por usuario."
            )
            return

        self.matrix_edit_hint.setText("Haz clic en una celda para activar/desactivar permisos.")

    def resizeEvent(self, event):
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.resize(self.size())
        super().resizeEvent(event)
