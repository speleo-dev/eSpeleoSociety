from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate


class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.values = list(values)

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.values)
        return editor

    def setEditorData(self, editor, index):
        value = index.data() or ""
        editor.setCurrentIndex(max(0, editor.findText(value)))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())
