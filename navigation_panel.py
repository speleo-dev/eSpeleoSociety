from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap

class NavigationPanel(QWidget):
    show_clubs_list_signal = pyqtSignal() # Renamed for clarity and convention
    show_member_search_signal = pyqtSignal()
    show_ecp_requests_signal = pyqtSignal()
    show_notifications_signal = pyqtSignal()
    show_sepa_import_signal = pyqtSignal()
    show_settings_signal = pyqtSignal() # New signal for settings
    show_reporting_signal = pyqtSignal() # New signal for reporting

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        # Button for Clubs List
        self.btn_show_clubs = QPushButton(self.tr("Clubs List"))
        self.btn_show_clubs.clicked.connect(self.show_clubs_list_signal.emit)
        layout.addWidget(self.btn_show_clubs)

        # Button for Find Member
        self.btn_member_search = QPushButton(self.tr("Find Member"))
        self.btn_member_search.clicked.connect(self.show_member_search_signal.emit)
        layout.addWidget(self.btn_member_search)

        # Button for eCP Requests
        self.btn_ecp_requests = QPushButton(self.tr("eCP Requests"))
        self.btn_ecp_requests.clicked.connect(self.show_ecp_requests_signal.emit)
        layout.addWidget(self.btn_ecp_requests)

        # Button for Messages
        self.btn_notifications = QPushButton(self.tr("Messages"))
        self.btn_notifications.clicked.connect(self.show_notifications_signal.emit)
        layout.addWidget(self.btn_notifications)

        # Button for Import SEPA
        self.btn_sepa_import = QPushButton(self.tr("Import SEPA"))
        self.btn_sepa_import.clicked.connect(self.show_sepa_import_signal.emit)
        layout.addWidget(self.btn_sepa_import)

        # Button for Reporting
        self.btn_reporting = QPushButton(self.tr("Reporting"))
        self.btn_reporting.clicked.connect(self.show_reporting_signal.emit)
        layout.addWidget(self.btn_reporting)

        # Button for Settings
        self.btn_settings = QPushButton(self.tr("Settings"))
        self.btn_settings.clicked.connect(self.show_settings_signal.emit)
        layout.addWidget(self.btn_settings)

        # Fill the space at the bottom
        layout.addStretch()
        # Add space for the logo at the bottom
        layout.addWidget(self.logo_label)

    def set_logo(self, logo_pixmap: QPixmap):
        # Set the logo, possibly scaling it as required
        self.logo_label.setPixmap(logo_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
