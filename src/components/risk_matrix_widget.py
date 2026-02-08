from PySide6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QTextEdit,
    QVBoxLayout
)
from PySide6.QtCore import Qt


class RiskMatrixWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(9, 7, self)
        self.table.setHorizontalHeaderLabels([
            "Ámbito",
            "Descripción",
            "Nivel desarrollo",
            "Riesgo transversal",
            "Probabilidad",
            "Impacto",
            "Nivel de riesgo"
        ])

        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

    # --------------------------------------------------
    # Precargar los 9 ámbitos (desde EIPD)
    # --------------------------------------------------
    def preload_ambitos(self, ambitos: list[str]):
        self.table.setRowCount(len(ambitos))

        for row, ambito in enumerate(ambitos):
            item = QTableWidgetItem(ambito)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, item)

            # Descripción
            self.table.setCellWidget(row, 1, QTextEdit())

            # Nivel desarrollo (por ahora combo simple)
            nivel_combo = QComboBox()
            nivel_combo.addItems(["Inicial", "Intermedio", "Avanzado"])
            self.table.setCellWidget(row, 2, nivel_combo)

            # Riesgo transversal
            self.table.setCellWidget(row, 3, QTextEdit())

            # Probabilidad
            prob_combo = QComboBox()
            prob_combo.addItems([
                "Despreciable",
                "Limitado",
                "Significativo",
                "Máximo"
            ])
            self.table.setCellWidget(row, 4, prob_combo)

            # Impacto
            impact_combo = QComboBox()
            impact_combo.addItems([
                "Despreciable",
                "Limitado",
                "Significativo",
                "Máximo"
            ])
            self.table.setCellWidget(row, 5, impact_combo)

            # Nivel de riesgo (solo lectura por ahora)
            nivel_item = QTableWidgetItem("-")
            nivel_item.setFlags(nivel_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, nivel_item)

    # --------------------------------------------------
    # Obtener data (para POST más adelante)
    # --------------------------------------------------
    def get_data(self):
        data = []

        for row in range(self.table.rowCount()):
            row_data = {
                "ambito": self.table.item(row, 0).text() if self.table.item(row, 0) else None,
                "descripcion": self._get_text(row, 1),
                "nivel_desarrollo": self._get_combo(row, 2),
                "riesgo_transversal": self._get_text(row, 3),
                "probabilidad": self._get_combo(row, 4),
                "impacto": self._get_combo(row, 5),
                "nivel_riesgo": self.table.item(row, 6).text() if self.table.item(row, 6) else None,
            }
            data.append(row_data)

        return data

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def _get_text(self, row, col):
        widget = self.table.cellWidget(row, col)
        if isinstance(widget, QTextEdit):
            return widget.toPlainText()
        return None

    def _get_combo(self, row, col):
        widget = self.table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return None
