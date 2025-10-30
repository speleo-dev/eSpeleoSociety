import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QDateTimeEdit, QComboBox, QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from utils import get_table_header_stylesheet, show_warning_message, show_success_message # Pridaný import
from PyQt5.QtCore import Qt
import db

class NotificationsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_notifications()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("Notification Messages to SSS Members"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # Formulár pre pridanie správy
        self.message_input = QTextEdit()
        self.message_input.setFixedHeight(50)
        layout.addWidget(self.message_input)

        datetime_layout = QHBoxLayout()
        self.datetime_input = QDateTimeEdit(datetime.datetime.now())
        self.datetime_input.setCalendarPopup(True)
        self.validity_combo = QComboBox()
        self.validity_combo.addItems(["1", "2", "3", "4", "5", "6", "7", "10", "14", "21", "30", "60", "120", "180"])
        datetime_layout.addWidget(self.datetime_input)
        datetime_layout.addWidget(self.validity_combo)
        layout.addLayout(datetime_layout)

        btn_layout = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add Message"))
        self.add_button.clicked.connect(self.add_notification)
        btn_layout.addWidget(self.add_button)
        layout.addLayout(btn_layout)

        # Tabuľka na zobrazenie notifikácií
        self.table = QTableWidget()
        self.table.setColumnCount(5) # Creation Date, Message, Issued, Expired, Actions
        self.table.setHorizontalHeaderLabels([self.tr("Creation Date"), self.tr("Message"), self.tr("Issued"), self.tr("Expired"), self.tr("Actions")])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Creation Date
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Message
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Actions
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Issued
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Expired
        header.setStretchLastSection(False)
        header.setStyleSheet(get_table_header_stylesheet())
        layout.addWidget(self.table)

    def load_notifications(self):
        notifications = db.db_manager.fetch_notifications()
        self.table.setRowCount(len(notifications))
        for row, notif in enumerate(notifications):
            notification_id = notif['notification_id']
            dt = notif['created_at']
            valid_from = notif['valid_from']
            valid_to = notif['valid_to']

            self.table.setItem(row, 0, QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 1, QTableWidgetItem(notif['text']))
            self.table.setItem(row, 2, QTableWidgetItem(valid_from.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 3, QTableWidgetItem(valid_to.strftime("%Y-%m-%d %H:%M")))

            # Pridanie tlačidla Akcie
            btn_delete = QPushButton(self.tr("Delete"))
            # Použijeme lambda funkciu na odovzdanie ID notifikácie
            btn_delete.clicked.connect(lambda checked, notif_id=notification_id: self.delete_notification(notif_id))
            self.table.setCellWidget(row, 4, btn_delete)

        self.table.resizeRowsToContents() # Prispôsobenie výšky riadkov obsahu

    def add_notification(self):
        text = self.message_input.toPlainText().strip()
        valid_from = self.datetime_input.dateTime().toPyDateTime()
        validity_days = int(self.validity_combo.currentText())
        valid_to = valid_from + datetime.timedelta(days=validity_days)
        if not text:
            show_warning_message(self.tr("Please enter the message text."))
            return
        db.db_manager.insert_notification(text, valid_from, valid_to)
        show_success_message(self.tr("The message has been added."))
        self.load_notifications()

    def delete_notification(self, notification_id: int):
        db.db_manager.delete_notification(notification_id)
        show_success_message(self.tr("The message has been deleted."))
        self.load_notifications() # Obnovenie tabuľky po vymazaní
