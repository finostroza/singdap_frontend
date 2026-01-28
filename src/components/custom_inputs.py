from PySide6.QtWidgets import QComboBox, QStyledItemDelegate
from PySide6.QtGui import QStandardItem, QStandardItemModel, QPalette, QBrush, QColor
from PySide6.QtCore import Qt, Signal, QEvent

class CheckableComboBox(QComboBox):
    # Custom signal if needed, though usually model signal is enough
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        
        # Use a custom palette for the lineEdit to make it look like a normal combo label
        palette = self.lineEdit().palette()
        palette.setBrush(QPalette.Base, QBrush(Qt.transparent))
        self.lineEdit().setPalette(palette)
        
        self.setModel(QStandardItemModel(self))
        self.view().viewport().installEventFilter(self)
        self.model().dataChanged.connect(self.updateText)
        
        # Placeholder
        self._placeholder_text = "Seleccione..."
        self.lineEdit().setPlaceholderText(self._placeholder_text)

    def addItem(self, text, userData=None):
        item = QStandardItem(text)
        item.setData(userData, Qt.UserRole)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)
            
    def currentData(self):
        # Return list of selected IDs
        res = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                res.append(item.data(Qt.UserRole))
        return res

    def setCurrentData(self, data_list):
        # Data list should be a list of IDs
        if not isinstance(data_list, list):
            data_list = [data_list]
            
        data_set = set(str(d) for d in data_list) # Compare strings to be safe
        
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            val = str(item.data(Qt.UserRole))
            if val in data_set:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
        self.updateText()

    def updateText(self):
        selected_items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                selected_items.append(item.text())
                
        text = ", ".join(selected_items)
        self.lineEdit().setText(text)
        self.selectionChanged.emit()

    def eventFilter(self, widget, event):
        # Prevent popup closing when clicking an item
        if widget == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().itemFromIndex(index)
                if item.flags() & Qt.ItemIsUserCheckable:
                    if item.checkState() == Qt.Checked:
                        item.setCheckState(Qt.Unchecked)
                    else:
                        item.setCheckState(Qt.Checked)
                return True
        return super().eventFilter(widget, event)

    def showPopup(self):
        super().showPopup()
        # Ensure correct text is displayed
        self.updateText()

    def hidePopup(self):
        super().hidePopup()
        self.updateText()
