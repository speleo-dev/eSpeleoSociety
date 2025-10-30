# views/reporting_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class ReportingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("Reporting")) # Použijeme self.tr pre budúce preklady
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        # Sem neskôr pridáš obsah pre reporting