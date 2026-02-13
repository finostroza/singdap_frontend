from src.components.generic_form_dialog import GenericFormDialog
from PySide6.QtWidgets import QComboBox, QMessageBox, QApplication, QDateEdit, QLineEdit, QTextEdit, QCheckBox, QLabel
from PySide6.QtCore import Qt, QTimer, QDate
from pathlib import Path
import json

# Ajusta el import según tu estructura real
from src.core.api_client import ApiClient

class RatDialog(GenericFormDialog):
    RAT_CATALOGO_CACHE_KEY = "catalogo_rat_id"
    TIPO_IA_IDS = {"df15ad81-74f8-4f1d-8e4a-d92b5b7ece44"}
    TIPO_INSTITUCIONAL_IDS = {"53d1a722-5311-41d1-a2b6-9bbae7ea037b"}
    TIPO_SIMPLIFICADO_IDS = {
        "85dd61f7-ab43-462c-ae45-f046812d0695",
        "1f3e71b0-99d4-41e1-a855-ec65377a6321",
        "e295e4a8-6622-4c9a-ad47-78da7b36572c",
        "e42ae6e9-95d9-43e5-894a-ce6bb663bfa0",
        "8a06e8c5-8055-40ee-8855-5d7f3f693ca0",
    }

    def __init__(self, parent=None, rat_id=None, **kwargs):
        # 1. CONFIGURACIÓN DE RUTAS
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.config_ia_path = base_dir / "src" / "config" / "formularios" / "rat_ia.json"
        self.config_institucional_path = base_dir / "src" / "config" / "formularios" / "rat_institucional.json"
        self.config_simplificado_path = base_dir / "src" / "config" / "formularios" / "rat_simplificado.json"
        
        config_path = base_dir / "src" / "config" / "formularios" / "rat.json"
        
        target_id = rat_id
        if target_id is None: target_id = kwargs.get("id")
        if target_id is None: target_id = kwargs.get("record_id")
        
        self._current_extension = None
        self.client = ApiClient()
        self._is_admin_user = self.client.is_admin
        self._is_auditor_user = self.client.is_auditor
        
        self.rat_estado = "EN_EDICION"

        super().__init__(str(config_path), parent=parent, record_id=target_id)
        
        # 2. CONEXIÓN DE SEÑALES (SOLO CREAR)
        if "tipo_tratamiento" in self.inputs:
            combo = self.inputs["tipo_tratamiento"]
            if isinstance(combo, QComboBox):
                combo.currentIndexChanged.connect(self._check_type_transition)

    # =========================================================================
    #  LÓGICA DE EXPANSIÓN DINÁMICA (UI)
    # =========================================================================
  
    def _check_type_transition(self): 
        """Se ejecuta al cambiar el combo manualmente (Usuario)."""
        combo = self.inputs.get("tipo_tratamiento")
        if not combo: return
        val = combo.currentData()
        val_text = combo.currentText()
        # Aseguramos string para la comparación
        val_str = str(val) if val else None
        self._perform_expansion(val_str, tipo_text=val_text)

    def _resolve_extension(self, tipo_uuid=None, tipo_text=None, tipo_rat=None):
        if tipo_uuid in self.TIPO_IA_IDS:
            return "ia"
        if tipo_uuid in self.TIPO_INSTITUCIONAL_IDS:
            return "institucional"
        if tipo_uuid in self.TIPO_SIMPLIFICADO_IDS:
            return "simplificado"

        if tipo_rat:
            rat_up = str(tipo_rat).strip().upper()
            if rat_up == "IA":
                return "ia"
            if rat_up == "PROCESO":
                return "institucional"
            if rat_up == "SIMPLIFICADO":
                return "simplificado"

        text = (tipo_text or "").strip().lower()
        if "ia" in text:
            return "ia"
        if "proceso" in text or "institucional" in text:
            return "institucional"
        if "simplificado" in text:
            return "simplificado"

        return None

    def _perform_expansion(self, tipo_uuid, tipo_text=None, tipo_rat=None):
        """Carga/Descarga secciones según el UUID."""
        target_config = None
        target_name = None

        resolved = self._resolve_extension(tipo_uuid=tipo_uuid, tipo_text=tipo_text, tipo_rat=tipo_rat)
        if resolved == "ia":
            target_config = self.config_ia_path
            target_name = "ia"
        elif resolved == "institucional":
            target_config = self.config_institucional_path
            target_name = "institucional"
        elif resolved == "simplificado":
            target_config = self.config_simplificado_path
            target_name = "simplificado"
            
        if target_name != self._current_extension:
            if self._current_extension: self._shrink_form()
            if target_config:
                self._expand_form(target_config)
                self._current_extension = target_name
            else:
                self._current_extension = None

    def _expand_form(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                ext_config = json.load(f)
        except Exception:
            return

        sections = ext_config.get("sections", [])
        if not sections:
            return

        # 🚨 SIEMPRE saltar las 2 primeras
        new_sections = sections[2:]

        if not new_sections:
            return

        start_index = len(self.config["sections"])
        self.config["sections"].extend(new_sections)

        if self.is_edit:
            # Mantiene activo el re-aplicado de datos mientras cargan combos dinámicos.
            self._allow_asset_reapply = True

        for i, section in enumerate(new_sections):
            abs_index = start_index + i
            content_widget = self._build_section_form(section)
            self.sidebar.add_step(section["title"])

            page = self._wrap_step_content(
                content_widget,
                section["title"],
                section.get("description", ""),
                abs_index,
                len(self.config["sections"]),
            )
            self.stack.addWidget(page)
            self._load_new_combos(section)

        if start_index > 0:
            self._update_footer_to_next(start_index - 1)
        
        last_index = self.stack.count() - 1
        self._update_footer_to_save(last_index)

        self._validate_steps_progress()

    def _shrink_form(self):
        if len(self.config["sections"]) <= 2: return
        while len(self.config["sections"]) > 2:
            section = self.config["sections"].pop()
            for field in section.get("fields", []):
                key = field["key"]
                if key in self.inputs: del self.inputs[key]
                if key in self.dependencies: del self.dependencies[key]
                if key in self.dependency_configs: del self.dependency_configs[key]
            
            self.sidebar.remove_last_step()
            w = self.stack.widget(self.stack.count()-1)
            self.stack.removeWidget(w); w.deleteLater()
            
        self._update_footer_to_save(1)
        self._validate_steps_progress()

    def _iter_section_fields(self, fields):
        for field in fields or []:
            if field.get("type") == "group":
                yield from self._iter_section_fields(field.get("fields", []))
            else:
                yield field

    def _load_new_combos(self, section):
        for field in self._iter_section_fields(section.get("fields", [])):
            if field.get("type") == "combo" and field.get("source") and not field.get("depends_on"):
                key = field["key"]
                if key in self.inputs:
                    self.pending_loads += 1
                    self._start_combo_loader(
                        self.inputs[key],
                        field["source"],
                        field.get("cache_key"),
                        track_pending=True
                    )

    # --- Helpers Footer ---
    def _update_footer_to_next(self, idx): self._rebuild_footer(idx, False)
    def _update_footer_to_save(self, idx): self._rebuild_footer(idx, True)
    
    def _rebuild_footer(self, index, is_last):
        page = self.stack.widget(index)
        if not page:
            return

        layout = page.layout()
        if not layout:
            return

        item = layout.itemAt(layout.count() - 1)
        if not item:
            return

        footer_layout = item.layout()
        if not footer_layout:
            return

        self._clear_layout(footer_layout)

        from PySide6.QtWidgets import QPushButton

        # Botón Anterior
        if index > 0:
            btn_prev = QPushButton("Anterior")
            btn_prev.setObjectName("secondaryButton")
            btn_prev.clicked.connect(self.sidebar.prev_step)
            footer_layout.addWidget(btn_prev)

        footer_layout.addStretch()

        if not is_last:
            btn_next = QPushButton("Siguiente")
            btn_next.setObjectName("primaryButton")
            btn_next.clicked.connect(self.sidebar.next_step)
            footer_layout.addWidget(btn_next)
            return

        # ===============================
        # DECISIÓN DE BOTONES (AQUÍ ESTÁ TODO)
        # ===============================

        estado = self.rat_estado
        is_admin = self._is_admin_user

        if estado == "EN_EDICION":
            btn_guardar = QPushButton("Guardar")
            btn_guardar.setObjectName("primaryButton")
            btn_guardar.clicked.connect(self._submit)

            btn_enviar = QPushButton("Enviar")
            btn_enviar.setObjectName("dangerButton")
            btn_enviar.clicked.connect(self._submit_enviar)

            footer_layout.addWidget(btn_guardar)
            footer_layout.addWidget(btn_enviar)

        elif estado == "ENVIADO" and is_admin:
            btn_aprobar = QPushButton("Aprobar")
            btn_aprobar.setObjectName("successButton")
            btn_aprobar.clicked.connect(self._aprobar_rat)

            btn_rechazar = QPushButton("Rechazar")
            btn_rechazar.setObjectName("dangerButton")
            btn_rechazar.clicked.connect(self._mostrar_rechazo)

            footer_layout.addWidget(btn_aprobar)
            footer_layout.addWidget(btn_rechazar)

    # APROBADO / ENVIADO (no admin) / otros
    # → no se muestran botones

        
    
    def _submit_enviar(self):
        try:
            if not self.record_id:
                QMessageBox.warning(
                    self,
                    "No enviado",
                    "Debe guardar el RAT antes de enviarlo."
                )
                return

            missing = self._get_missing_required_labels_for_send()
            if missing:
                QMessageBox.warning(
                    self,
                    "Campos obligatorios pendientes",
                    "Complete los campos obligatorios antes de enviar:\n- "
                    + "\n- ".join(missing[:20])
                )
                return

            QApplication.setOverrideCursor(Qt.WaitCursor)

            # 🔒 SOLO cambiar estado
            self.client.put(
            f"/rat/{self.record_id}/estado",
            {"estado": "ENVIADO"}
)

            self._invalidate_rat_catalog_cache()

            QApplication.restoreOverrideCursor()

            QMessageBox.information(
                self,
                "RAT enviado",
                "El RAT fue enviado correctamente y ya no puede ser editado."
            )

            self.accept()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", str(e))
    
    def _aprobar_rat(self):
        self.client.put(
            f"/rat/{self.record_id}/estado",
            {"estado": "APROBADO"}
        )
        self._invalidate_rat_catalog_cache()
        QMessageBox.information(self, "RAT aprobado", "El RAT fue aprobado.")
        self.accept()
        
    def _mostrar_rechazo(self):
        from PySide6.QtWidgets import QInputDialog

        comentario, ok = QInputDialog.getMultiLineText(
            self,
            "Rechazar RAT",
            "Ingrese el motivo del rechazo:"
        )

        if ok and comentario.strip():
            self.client.put(
                f"/rat/{self.record_id}/estado",
                {
                    "estado": "RECHAZADO",
                    "comentario": comentario
                }
            )
            self._invalidate_rat_catalog_cache()
            QMessageBox.information(self, "RAT rechazado", "El RAT fue rechazado.")
            self.accept()


    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

   # =========================================================================
    #  CARGA DE DATOS (EDITAR) - SOLUCIÓN ROBUSTA SIN TRADUCCIONES
    # =========================================================================
    def _lock_form(self):
        for w in self.inputs.values():
            if hasattr(w, "set_read_only"):
                try:
                    w.set_read_only(True)
                except Exception:
                    pass
            w.setEnabled(False)

    def _on_record_data(self, data):
        
        self.rat_estado = data.get("estado", "EN_EDICION")

        if not data:
            self._check_finished()
            return

        # 🔁 MAPEO BACKEND → FORM
        key_map = {
            "subsecretaria_id": "subsecretaria",
            "division_id": "division",
            "responsable_tratamiento": "nombre_responsable",
            "encargado_tratamiento": "nombre_encargado",
        }

        for backend_key, form_key in key_map.items():
            if backend_key in data and form_key not in data:
                data[form_key] = data.get(backend_key)

        # Expandir secciones según tipo
        tid = data.get("tipo_tratamiento")
        tipo_rat = data.get("tipo_rat")
        if tid or tipo_rat:
            self._perform_expansion(str(tid) if tid else None, tipo_rat=tipo_rat)

        if self.rat_estado in ["ENVIADO", "APROBADO", "RECHAZADO"]:
            self._lock_form()
        
        last_index = self.stack.count() - 1
        self._rebuild_footer(last_index, True)
        print("ESTADO RAT:", self.rat_estado, "ADMIN:", self._is_admin_user)


        riesgos = data.get("riesgos_identificados")
        if not isinstance(riesgos, list):
            riesgos = []
        if not riesgos and (
            self._is_non_empty(data.get("nombre_riesgo"))
            or self._is_non_empty(data.get("descripcion_riesgo"))
        ):
            riesgos = [{
                "nombre_riesgo": data.get("nombre_riesgo"),
                "descripcion_riesgo": data.get("descripcion_riesgo"),
            }]
        data["riesgos_identificados"] = riesgos

        self.asset_data = data
        self._try_set_values()
        self._validate_steps_progress()
        self._check_finished()


        

    
    # =========================================================================
    #  GUARDADO (SUBMIT) - SOLUCIÓN AL ERROR 422
    # =========================================================================

    def _submit(self):
        if self.record_id and self.rat_estado != "EN_EDICION":
            QMessageBox.warning(
                self,
                "No editable",
                f"Este RAT no se puede editar en estado {self._estado_label(self.rat_estado)}."
            )
            return

        # 1. Obtenemos datos LIMPIOS (None si están vacíos)
        form_data = self._get_all_form_values()

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            if self.record_id:
                # MODO EDICIÓN
                self.client.put(f"/rat/{self.record_id}", form_data)
                self._save_sections_by_type(form_data)
            else:
                # MODO CREACIÓN
                subsecretaria_id = (
                    form_data.get("subsecretaria")
                    or self._first_combo_id("subsecretaria")
                    or self._first_id_from_endpoint("/setup/subsecretarias")
                )
                tipo_tratamiento = (
                    form_data.get("tipo_tratamiento")
                    or self._first_combo_id("tipo_tratamiento")
                    or self._first_id_from_endpoint("/catalogos/rat/tipo-tratamiento")
                )
                division_id = form_data.get("division") or self._first_combo_id("division")

                if not division_id and subsecretaria_id:
                    try:
                        divisiones = self.client.get(
                            f"/setup/divisiones?subsecretaria_id={subsecretaria_id}"
                        )
                        if isinstance(divisiones, list) and divisiones:
                            division_id = divisiones[0].get("id")
                    except Exception:
                        pass

                if self._current_extension == "ia":
                    tipo_rat = "IA"
                elif self._current_extension == "institucional":
                    tipo_rat = "PROCESO"
                elif self._current_extension == "simplificado":
                    tipo_rat = "SIMPLIFICADO"
                else:
                    tipo_rat = "IA"  # fallback seguro


                payload_create = {
                    "nombre_tratamiento": form_data.get("nombre_tratamiento") or "RAT sin nombre",
                    "tipo_tratamiento": tipo_tratamiento,
                    "subsecretaria_id": subsecretaria_id,
                    "division_id": division_id,
                    "departamento": form_data.get("departamento"),
                    "responsable_tratamiento": form_data.get("nombre_responsable"),
                    "cargo_responsable": form_data.get("cargo_responsable"),
                    "email_responsable": form_data.get("email_responsable"),
                    "telefono_responsable": form_data.get("telefono_responsable"),

                    "encargado_tratamiento": form_data.get("nombre_encargado"),
                    "cargo_encargado": form_data.get("cargo_encargado"),
                    "email_encargado": form_data.get("email_encargado"),
                    "telefono_encargado": form_data.get("telefono_encargado"),
                    "estado": "EN_EDICION",
                    "tipo_rat": tipo_rat,  # Tu backend probablemente exige esto
                    "tipo_tratamiento_otro": "N/A"
                    
                }
                
                
  
                
                # Imprimimos payload para debug si vuelve a fallar
                print(f"Enviando POST /rat: {payload_create}")

                res = self.client.post("/rat", payload_create)
                self.record_id = res.get("rat_id")
                
                if self.record_id:
                    self._save_sections_by_type(form_data)

            self._invalidate_rat_catalog_cache()
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Éxito", "Guardado correctamente.")
            self.accept()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            print(f"Error submit: {e}")
            # Mostrar mensaje amigable si es error de validación
            msg = str(e)
            if "422" in msg: msg = "Faltan campos obligatorios o el formato es incorrecto."
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{msg}")

    def _first_combo_id(self, key):
        widget = self.inputs.get(key)
        if isinstance(widget, QComboBox) and widget.count() > 0:
            return widget.itemData(0)
        return None

    def _first_id_from_endpoint(self, endpoint):
        try:
            items = self.client.get(endpoint)
            if isinstance(items, list) and items:
                first = items[0]
                if isinstance(first, dict):
                    return first.get("id")
        except Exception:
            return None
        return None

    def _invalidate_rat_catalog_cache(self):
        self.catalogo_service.invalidate_cache_key(self.RAT_CATALOGO_CACHE_KEY)

    def _is_non_empty(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _has_all(self, values):
        return all(self._is_non_empty(v) for v in values)

    def _to_bool_or_none(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw in ["si_corresponde", "si corresponde"]:
                return True
            if raw in ["no_requiere", "no requiere"]:
                return False
            if raw in ["si", "sí", "true", "1"]:
                return True
            if raw in ["no", "false", "0"]:
                return False
            return None
        return bool(value) if value is not None else None

    def _estado_label(self, estado):
        labels = {
            "EN_EDICION": "EN EDICIÓN",
        }
        return labels.get(estado, str(estado).replace("_", " ") if estado else "—")

    def _iter_required_fields(self, fields):
        for field in fields or []:
            if field.get("type") == "group":
                yield from self._iter_required_fields(field.get("fields", []))
            elif field.get("required", False):
                yield field

    def _get_missing_required_labels_for_send(self):
        missing = []
        for idx, section in enumerate(self.config.get("sections", [])):
            page_widget = self.stack.widget(idx) if idx < self.stack.count() else None
            for field in self._iter_required_fields(section.get("fields", [])):
                key = field.get("key")
                widget = self.inputs.get(key)
                if not widget:
                    continue
                if not page_widget or not widget.isVisibleTo(page_widget):
                    continue
                if not self._is_field_filled(widget, field):
                    missing.append(field.get("label", key))
        return missing

    # --- Helpers Guardado ---
    def _save_gobierno_datos(self, data):
        payload = {
            "fecha_elaboracion": data.get("fecha_elaboracion"),
            "responsable_informe": data.get("responsable_informe"),
            "equipo_entrevistados": data.get("equipo_entrevistados"),
            "equipo_validacion_contenidos": data.get("equipo_validacion"),
            "revision_aprobacion_final": data.get("revision_aprobacion")
        }
        self.client.put(f"/rat/{self.record_id}/gobierno-datos", payload)

    def _save_seccion_ia(self, data):
        base = f"/rat/{self.record_id}/ia"
        payload_finalidad = {
            "finalidad_principal_uso_ia": data.get("finalidad_principal_ia"),
            "tipo_tarea_ia": data.get("tipo_tarea_ia"),
            "alcance_impacto": data.get("alcance_impacto_ia"),
            "efectos_juridicos_significativos": data.get("efectos_juridicos_ia"),
        }
        self.client.put(f"{base}/finalidad", payload_finalidad)

        payload_flujo = {
            "descripcion_flujo_ia": data.get("descripcion_resumida_flujo_ia"),
            "puntos_intervencion_humana": data.get("puntos_intervencion_ia"),
            "sistemas_repositorios_involucrados": data.get("sistemas_repositorios_ia"),
        }
        self.client.put(f"{base}/flujo", payload_flujo)

        datos_sensibles = self._to_bool_or_none(data.get("datos_sensibles_entrenamiento_ia"))
        payload_entrenamiento = {
            "fuentes_datos_entrenamiento": data.get("fuente_datos_entrenamiento_ia"),
            "base_licitud": data.get("base_licitud_entrenamiento_ia"),
            "restricciones_uso": data.get("restricciones_uso_ia"),
            "categorias_datos_personales": data.get("categorias_datos_entrenamiento_ia"),
            "datos_sensibles": datos_sensibles,
            "volumen_y_periodo": data.get("volumen_periodo_ia"),
            "poblaciones_especiales": data.get("poblaciones_vulnerables_entrenamiento_ia"),
        }
        self.client.put(f"{base}/entrenamiento", payload_entrenamiento)

        payload_operacional = {
            "datos_entrada": data.get("datos_entrada_ia"),
            "datos_salida": data.get("datos_salida_ia"),
            "monitoreo_modelo": data.get("monitoreo_modelo_ia"),
        }
        self.client.put(f"{base}/operacional", payload_operacional)

        payload_modelo = {
            "tipo_modelo": data.get("tipo_modelo_ia"),
            "modalidad_entrenamiento": data.get("modalidad_entrenamiento_ia"),
            "infraestructura_ejecucion": data.get("infraestructura_ejecucion_ia"),
            "reentrenamiento": data.get("reentrenamiento_ia"),
            "controles_acceso": data.get("controles_acceso_ia"),
        }
        self.client.put(f"{base}/modelo", payload_modelo)

        payload_explicabilidad = {
            "campo": "general",
            "explicacion_logica_aplicada": data.get("explicacion_logica_ia"),
            "variables_relevantes": data.get("variables_relevantes_ia"),
            "intervencion_humana": data.get("intervencion_humana_ia"),
            "documentacion_explicabilidad_path": data.get("documentacion_explicabilidad_ia"),
        }
        self.client.put(f"{base}/explicabilidad", payload_explicabilidad)

    def _save_seccion_simplificado(self, data):
        # 1. Guardamos la parte principal (Simplificado)
        payload_simp = {
        # =========================
        # DESCRIPCIÓN DEL TRATAMIENTO
        # =========================
        "autorizacion_datos": data.get("autorizacion_datos_ris"),

        # ⚠️ NOMBRES QUE EXIGE EL BACKEND
        "descripcion": data.get("descripcion_alcance"),
        "operaciones": data.get("operaciones_realizadas"),
        "equipos_ejecutantes": data.get("equipos_involucrados"),

        "software": data.get("software_utilizado"),
        "repositorios": data.get("repositorios_utilizados"),
        "sistemas": data.get("sistemas_plataformas"),

        # =========================
        # MARCO HABILITANTE
        # =========================
        "mecanismo_habilitante": data.get("mecanismo_habilitante"),
        "mecanismo_habilitante_otro": data.get("mecanismo_habilitante_otro"),
        "nombre_mecanismo": data.get("nombre_mecanismo"),

        "consentimiento_titular": data.get("consentimiento_titular"),
        "finalidad_tratamiento": data.get("finalidad_tratamiento"),

        # =========================
        # ⚠️ ESTO FALTABA Y ROMPÍA TODO
        # =========================
        "categoria_destinatarios": data.get("categorias_destinatarios"),
        "categoria_destinatarios_otro": data.get("categoria_destinatarios_otro"),

        # =========================
        # VOLUMEN
        # =========================
        "volumen_datos": data.get("volumen_datos"),
        "cantidad_archivos": data.get("cantidad_archivos"),

        # =========================
        # BOOLEANOS
        # =========================
        "decisiones_automatizadas": (
            str(data.get("decisiones_automatizadas")).lower() in ["si", "true", "1"]
        ),
    
    }
        
        self.client.put(f"/rat/{self.record_id}/simplificado", payload_simp)
        self._upsert_adjunto_seccion(
            seccion="simplificado_descripcion",
            path_archivo=data.get("archivos_adjuntos"),
            descripcion="Adjunto descripción tratamiento simplificado",
        )
        
        # 2. Guardamos la sección de Titulares
        try:
            # Categorías de datos personales (MULTI)
            cat_datos = data.get("categorias_datos_personales", [])
            if isinstance(cat_datos, list):
                cat_datos = json.dumps(cat_datos)

            # Categorías de destinatarios (SINGLE)
            cat_destinatarios = data.get("categorias_destinatarios")

            # Poblaciones vulnerables (MULTI)
            pob_vulnerable = data.get("poblaciones_vulnerables", [])
            if isinstance(pob_vulnerable, list):
                pob_vulnerable = json.dumps(pob_vulnerable)

            payload_titulares = {
                # 🔹 DATOS PERSONALES
                "categoria_datos": cat_datos,

                # 🔹 DESTINATARIOS
                "categoria_datos_especificacion": data.get("categorias_destinatarios"),

                # 🔹 POBLACIONES
                "poblaciones_especiales": pob_vulnerable,
                "poblaciones_especiales_otro": data.get("poblaciones_vulnerables_otro"),

                # 🔹 OTROS
                "tipo_datos": data.get("tipos_datos"),
                "origen_datos": data.get("origen_datos"),
                "origen_datos_otro": data.get("origen_datos_otro"),
                "medio_recoleccion": data.get("medio_recoleccion"),

                "volumen_datos": data.get("volumen_datos"),
                "cantidad_archivos": data.get("cantidad_archivos"),

                "decisiones_automatizadas": (
                    str(data.get("decisiones_automatizadas")).lower() in ["si", "true", "1"]
                ),
            }
            self.client.put(f"/rat/{self.record_id}/titulares", payload_titulares)
            
        except Exception as e:
            print(f"Error guardando titulares: {e}")
            
    def _save_seccion_institucional(self, data):
        flujos_val = data.get("descripcion_flujos")
        flujos_descripcion = None
        flujos_archivo = None
        if isinstance(flujos_val, dict):
            txt = flujos_val.get("text")
            fpath = flujos_val.get("file")
            flujos_archivo = fpath
            flujos_descripcion = txt if self._is_non_empty(txt) else fpath
        else:
            flujos_descripcion = flujos_val

        # Mapeo de llaves del Formulario (Frontend) -> Esquema del Backend
        payload = {
            "descripcion": data.get("descripcion_alcance"),
            "operaciones": data.get("operaciones_realizadas"),
            "equipos_ejecutantes": data.get("equipos_involucrados"),
            "software": data.get("aplicaciones_software"),
            "repositorios": data.get("repositorios_utilizados"),
            "sistemas": data.get("sistemas_plataformas_desc"),
            
            "finalidad_tratamiento": data.get("finalidad_tratamiento_inst"),
            "resultado_esperado": data.get("resultados_esperados"),
            
            "mecanismo_habilitante": data.get("base_licitud_inst"),
            # --- AQUÍ ESTABA EL ERROR: Faltaba esta llave ---
            "mecanismo_habilitante_otro": data.get("mecanismo_habilitante_otro"), 
            "nombre_mecanismo": data.get("nombre_mecanismo"),
            
            # Origen y Ciclo de vida
            "fuente_datos": data.get("fuente_datos"),
            "medio_recoleccion": data.get("medio_recoleccion_origen"),
            "forma_recoleccion": data.get("forma_recoleccion"),
            "uso_tratamiento": data.get("uso_tratamiento"),
            "almacenamiento_conservacion": data.get("almacenamiento_conservacion"),
            "comunicacion_transferencia": data.get("comunicacion_transferencia"),
            "destinatario_fundamento_legal": data.get("destinatarios_fundamento"),
            "disposicion_final": data.get("eliminacion_disposicion"),
            
            # Flujos y Conclusión
            "flujos_descripcion": flujos_descripcion,
            "flujos_sistemas": data.get("sistemas_plataformas_flujos"),
            
            "documentos_respaldo": data.get("documentos_respaldo"),
        }
        # Llamada al endpoint específico de Institucional
        self.client.put(f"/rat/{self.record_id}/proceso", payload)
        self._upsert_adjunto_seccion(
            seccion="institucional_descripcion",
            path_archivo=data.get("adjuntos_descripcion"),
            descripcion="Adjunto descripción tratamiento institucional",
        )
        self._upsert_adjunto_seccion(
            seccion="institucional_flujos",
            path_archivo=flujos_archivo,
            descripcion="Adjunto flujos de información",
        )
        
         # Categorías de datos personales (MULTI)
        cat_datos = data.get("categorias_datos_inst", [])
        if isinstance(cat_datos, list):
            cat_datos = json.dumps(cat_datos)

            # Poblaciones vulnerables (MULTI)
        pob_vulnerable = data.get("poblaciones_vulnerables_inst", [])
        if isinstance(pob_vulnerable, list):
            pob_vulnerable = json.dumps(pob_vulnerable)
        
        payload_titulares = {
                # 🔹 DATOS PERSONALES
                "categoria_datos": cat_datos,
                # 🔹 POBLACIONES
                "poblaciones_especiales": pob_vulnerable,

                # 🔹 OTROS
                "tipo_datos": data.get("tipos_datos"),
                "origen_datos": data.get("origen_datos_titulares"),
                "medio_recoleccion": data.get("medio_recoleccion_titulares"),

                "volumen_datos": data.get("volumen_datos"),
                "cantidad_archivos": data.get("cantidad_archivos"),

                "decisiones_automatizadas": (
                    str(data.get("decisiones_automatizadas")).lower() in ["si", "true", "1"]
                ),
            }
        self.client.put(f"/rat/{self.record_id}/titulares", payload_titulares)
            

    def _save_riesgos(self, data):
        rows = data.get("riesgos_identificados") or []
        if not isinstance(rows, list):
            rows = []

        riesgos = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            nombre = row.get("nombre_riesgo")
            descripcion = row.get("descripcion_riesgo")
            if not self._is_non_empty(nombre) and not self._is_non_empty(descripcion):
                continue
            riesgos.append({
                "riesgo_id": row.get("riesgo_id"),
                "nombre_riesgo": nombre,
                "descripcion_riesgo": descripcion,
            })

        self.client.put(f"/rat/{self.record_id}/riesgos", {"riesgos": riesgos})

    def _upsert_adjunto_seccion(self, seccion, path_archivo, descripcion=None):
        if not self.record_id:
            return

        existing = self.client.get(f"/rat/{self.record_id}/adjuntos") or []
        for adj in existing:
            if not isinstance(adj, dict):
                continue
            if adj.get("seccion") == seccion and adj.get("adjunto_id"):
                self.client.delete(f"/rat/adjuntos/{adj.get('adjunto_id')}")

        if self._is_non_empty(path_archivo):
            payload = {
                "seccion": seccion,
                "path_archivo": path_archivo,
                "descripcion": descripcion,
            }
            self.client.post(f"/rat/{self.record_id}/adjuntos", payload)
        
    def _save_conclusion(self, data):
        corresponde_value = self._to_bool_or_none(data.get("corresponde_eipd"))

        payload = {
            "sintesis_analisis": data.get("sintesis_analisis"),
            "corresponde_eipd": corresponde_value,
            "justificacion": data.get("justificacion"),
        }

        self.client.put(f"/rat/{self.record_id}/conclusion", payload)

    def _get_all_form_values(self):
        """Recolector de datos BLINDADO contra 422."""
        vals = {}
        for k, w in self.inputs.items():
            if isinstance(w, QComboBox):
                # IMPORTANTE: Si es None, devolvemos None. NO el texto "Seleccione..."
                v = w.currentData()
                vals[k] = v 
            elif isinstance(w, QDateEdit): 
                vals[k] = w.date().toString("yyyy-MM-dd")
            elif hasattr(w, "text"): 
                t = w.text().strip()
                vals[k] = t if t else None
            elif hasattr(w, "toPlainText"): 
                t = w.toPlainText().strip()
                vals[k] = t if t else None
            elif hasattr(w, "get_data"):
                vals[k] = w.get_data()
            elif hasattr(w, "selectedFiles"):
                f = w.selectedFiles()
                vals[k] = f[0] if f else None
        return vals
    
    def _save_sections_by_type(self, form_data):
        # Sección común
        self._try_save_section("gobierno_datos", lambda: self._save_gobierno_datos(form_data))

        # Sección específica según tipo
        if self._current_extension == "ia":
            self._try_save_section("seccion_ia", lambda: self._save_seccion_ia(form_data))
        elif self._current_extension == "institucional":
            self._try_save_section("seccion_institucional", lambda: self._save_seccion_institucional(form_data))
        elif self._current_extension == "simplificado":
            self._try_save_section("seccion_simplificado", lambda: self._save_seccion_simplificado(form_data))

        # Secciones finales comunes
        self._try_save_section("riesgos", lambda: self._save_riesgos(form_data))
        self._try_save_section("conclusion", lambda: self._save_conclusion(form_data))

    def _try_save_section(self, section_name, fn):
        try:
            fn()
        except Exception as e:
            # Guardado tolerante por sección: no interrumpe el guardado global del RAT
            print(f"[RAT] Se omite guardado de sección '{section_name}': {e}")
