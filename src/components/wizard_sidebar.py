from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Signal, Qt

class WizardStepWidget(QFrame):
    clicked = Signal(int)

    def __init__(self, index, title, required_text="0/0 requeridos", parent=None):
        super().__init__(parent)
        self.index = index
        self.is_active = False
        
        # Styles
        self.setObjectName("wizardStep")
        self.active_style = """
            #wizardStep {
                background-color: #006FB3; 
                border-radius: 8px;
                border: none;
            }
            QLabel { color: white; border: none; }
            #stepStatus { background-color: #002b4d; color: white; border-radius: 4px; padding: 2px 6px; font-weight: bold; border: none; }
        """
        self.inactive_style = """
            #wizardStep {
                background-color: transparent;
                border-radius: 8px;
                border: none;
            }
            QLabel { color: #333333; border: none; }
            #stepTitle { font-weight: bold; }
            #stepStatus { background-color: #E2E8F0; color: #64748B; border-radius: 4px; padding: 2px 6px; border: none; }
        """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16) 
        layout.setSpacing(6)

        # Row 1: Title + Status Badge
        row1 = QHBoxLayout()
        row1.setSpacing(4) # Reduced spacing to save horizontal pixels
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("stepTitle")
        self.title_lbl.setWordWrap(True)
        # Reduced font-size to 12px to prevent wrapping when bold
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 12px; border: none;") 
        
        self.status_badge = QLabel("Pendiente")
        self.status_badge.setObjectName("stepStatus")
        self.status_badge.setStyleSheet("font-size: 10px;")
        self.status_badge.setFixedHeight(22)
        
        row1.addWidget(self.title_lbl, 1) # Stretch title
        row1.addWidget(self.status_badge, 0) # Fixed badge
        
        # Row 2: Required text
        self.req_lbl = QLabel(required_text)
        self.req_lbl.setObjectName("stepRequired")
        self.req_lbl.setStyleSheet("font-size: 11px; color: #666; border: none;")
        
        layout.addLayout(row1)
        layout.addWidget(self.req_lbl)

        self.setCursor(Qt.PointingHandCursor)
        self.set_active(False)

    def set_active(self, active):
        self.is_active = active
        self.setStyleSheet(self.active_style if active else self.inactive_style)
        self.status_badge.setText("En edición" if active else "Pendiente")
        
        # Specific color overrides for active state (Qt stylesheet precedence can be tricky)
        if active:
             self.req_lbl.setStyleSheet("font-size: 11px; color: #ccc;")
        else:
             self.req_lbl.setStyleSheet("font-size: 11px; color: #666;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def update_required_count(self, filled, total):
        self.req_lbl.setText(f"{filled}/{total} requeridos")


class WizardSidebar(QWidget):
    step_changed = Signal(int)

    def __init__(self, steps_data, parent=None):
        super().__init__(parent)
        self.steps_data = steps_data
        self.step_widgets = []
        self.current_idx = 0
        
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: white; border-right: 1px solid #e0e0e0;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        
        # Title "Secciones"
        lbl = QLabel("Secciones")
        lbl.setStyleSheet("font-weight: bold; color: #64748B; margin-bottom: 8px;")
        layout.addWidget(lbl)

        # Scroll for steps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.steps_layout = QVBoxLayout(container)
        self.steps_layout.setContentsMargins(0,0,0,0)
        self.steps_layout.setSpacing(8)
        
        for i, step in enumerate(steps_data):
            w = WizardStepWidget(i, step["title"], "Campos requeridos")
            w.clicked.connect(self._on_step_clicked)
            self.steps_layout.addWidget(w)
            self.step_widgets.append(w)
            
        self.steps_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        self._update_ui()

    def _on_step_clicked(self, index):
        self.set_current_step(index)

    def set_current_step(self, index):
        if 0 <= index < len(self.step_widgets):
            self.current_idx = index
            self._update_ui()
            self.step_changed.emit(index)

    def _update_ui(self):
        for i, w in enumerate(self.step_widgets):
            w.set_active(i == self.current_idx)
            
    def next_step(self):
        if self.current_idx < len(self.step_widgets) - 1:
            self.set_current_step(self.current_idx + 1)
            
    def prev_step(self):
        if self.current_idx > 0:
            self.set_current_step(self.current_idx - 1)
