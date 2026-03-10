from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, 
    QStackedWidget, QMessageBox, QScrollArea
)
from src.services.permission_service import PermissionService
from src.viewmodels.seguimiento_viewmodel import SeguimientoViewModel
from src.views.seguimiento.seguimiento_listado_grid import SeguimientoListadoGrid
from src.views.seguimiento.seguimiento_edicion_grid import SeguimientoEdicionGrid
from src.views.seguimiento.riesgo_edicion_form import RiesgoEdicionForm
from src.components.loading_overlay import LoadingOverlay

class SeguimientoRiesgosView(QWidget):
    def __init__(self, viewmodel: SeguimientoViewModel = None):
        super().__init__()
        self.viewmodel = viewmodel or SeguimientoViewModel()
        self.permission_service = PermissionService()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Overlay de carga
        self.loading_overlay = LoadingOverlay(self)
        
        # Stack de vistas para alternar entre listado y edición
        self.stack = QStackedWidget()
        
        self.listado_grid = SeguimientoListadoGrid()
        self.listado_grid.action_triggered.connect(self._on_listado_action)
        
        self.edicion_grid = SeguimientoEdicionGrid()
        self.edicion_grid.back_requested.connect(self._on_back_requested)
        self.edicion_grid.expand_requested.connect(self._on_expand_requested)
        
        self.stack.addWidget(self.listado_grid)
        self.stack.addWidget(self.edicion_grid)
        
        self.layout.addWidget(self.stack, 1)
        
        # Conexiones ViewModel
        self.viewmodel.on_loading.connect(self._set_loading)
        self.viewmodel.on_error.connect(self._show_error)
        self.viewmodel.on_listado_ready.connect(self.listado_grid._populate_table if hasattr(self.listado_grid, '_populate_table') else lambda x: None)
        self.viewmodel.on_detalle_ready.connect(self._on_detalle_ready)
        self.viewmodel.on_actualizacion_exitosa.connect(self._on_update_success)
        
        # Map to track which row has which form widget
        self.active_forms = {} # map row -> form_widget

        # ... (rest of init)
        if self.permission_service.has_module_access("SEGUIMIENTO"):
            # GenericGridView handles its own load
            pass
        else:
            self._show_permission_block()

    def _on_listado_action(self, action_id, record_id, tipo):
        if action_id == "editar_grilla":
            self._on_edit_requested(tipo, record_id)

    def _set_loading(self, loading):
        if loading:
            self.loading_overlay.show_loading()
        else:
            self.loading_overlay.hide_loading()

    def _show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def _on_edit_requested(self, tipo, item_id):
        self._current_tipo = tipo
        self._current_id = item_id
        self.viewmodel.cargar_detalle(tipo, item_id)
        self.stack.setCurrentIndex(1)

    def _on_detalle_ready(self, data):
        self.active_forms.clear()
        self.edicion_grid.populate(data)

    def _on_back_requested(self):
        self.stack.setCurrentIndex(0)
        self.active_forms.clear()
        self.listado_grid._reload_all()

    def _on_expand_requested(self, row, data, is_expanded):
        # We need to find the correct insertion point.
        # If we have multiple forms, the row index shifts.
        # But edicion_grid.table.insertRow will handle the UI shift.
        # However, 'row' passed here is the original index from the data list.
        # We should probably map original_row to current_table_row.
        
        # Simple fix: Close any other open form before opening new one
        # to avoid index mess and satisfy "toggle (+/-)" without multiple forms
        if is_expanded:
            # Collapse others first
            for r in list(self.active_forms.keys()):
                if r != row:
                    # Logic to trigger toggle off in edicion_grid?
                    # For now just remove from table.
                    pass
            
            # Find the row in the table that matches the button clicked
            # Since buttons are in col 2, we can find it.
            # But let's assume one at a time for simplicity and stability.
            self._collapse_all_forms(exclude_original_row=row)
            
            # Now insert. Since all are closed, next_row is just row + 1
            next_row = row + 1
            self.edicion_grid.table.insertRow(next_row)
            self.edicion_grid.table.setRowHeight(next_row, 360) # Slightly more height
            
            form = RiesgoEdicionForm(data)
            form.save_requested.connect(lambda p, d=data, r=next_row: self._save_riesgo(d, p, r))
            
            self.edicion_grid.table.setSpan(next_row, 0, 1, 3)
            self.edicion_grid.table.setCellWidget(next_row, 0, form)
            self.active_forms[row] = form
        else:
            self._collapse_all_forms()

    def _collapse_all_forms(self, exclude_original_row=None):
        # Scan table for cells containing RiesgoEdicionForm and remove them
        for r in range(self.edicion_grid.table.rowCount() -1, -1, -1):
            widget = self.edicion_grid.table.cellWidget(r, 0)
            if isinstance(widget, RiesgoEdicionForm):
                self.edicion_grid.table.removeRow(r)
        self.active_forms.clear()
        # Also sync buttons in edicion_grid
        self.edicion_grid.reset_all_buttons(exclude_row=exclude_original_row)

    def _save_riesgo(self, original_data, payload, form_row):
        riesgo_id = original_data["_id_internal"]
        # Collapse before save to avoid visual glitche on reload
        self._collapse_all_forms()
        self.viewmodel.actualizar_riesgo(self._current_tipo, riesgo_id, payload)

    def _on_update_success(self, message):
        QMessageBox.information(self, "Éxito", message)
        self.viewmodel.cargar_detalle(self._current_tipo, self._current_id)

    def _show_permission_block(self):
        overlay = QFrame(self)
        overlay.setObjectName("permissionBlockOverlay")
        overlay.setStyleSheet("background-color: rgba(255, 255, 255, 200);")
        
        l = QVBoxLayout(overlay)
        l.setAlignment(Qt.AlignCenter)
        
        from utils import icon
        icon_label = QLabel()
        icon_label.setPixmap(icon("src/resources/icons/lock.svg").pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        
        msg_label = QLabel("Acceso denegado a Seguimiento de Riesgos.")
        msg_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #64748b;")
        msg_label.setAlignment(Qt.AlignCenter)
        
        l.addWidget(icon_label)
        l.addWidget(msg_label)
        
        self.layout.addWidget(overlay)
        overlay.show()

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            self.loading_overlay.resize(event.size())
        super().resizeEvent(event)
