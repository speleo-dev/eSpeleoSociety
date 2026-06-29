from PyQt5.QtWidgets import ( 
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox, QAbstractItemView,
    QDialog
)
from PyQt5.QtGui import QShowEvent # Added import for QShowEvent
from PyQt5.QtCore import pyqtSignal
import db
from dialogs.club_management_dialog import ClubManagementDialog
from utils import get_table_header_stylesheet # Pridaný import

class ClubsListView(QWidget):
    navigateToMembers = pyqtSignal(int) # Signal to emit club_id - presunuté na úroveň triedy

    def __init__(self, parent=None):
        super().__init__(parent)
        # Atribút navigateToMembers je teraz dedený z triedy
        self.init_ui()

    def init_ui(self):
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header = QLabel(self.tr("List of SSS Clubs"))
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(header)
        header_layout.addStretch()  # posunie tlačidlo doprava
        btn_new_club = QPushButton(self.tr("➕ Create New Club"))
        btn_new_club.clicked.connect(self.request_new_club_creation)
        header_layout.addWidget(btn_new_club)
        layout = QVBoxLayout(self)
        layout.addWidget(header_widget)

        # Označenie reťazca pre preklad
        #header = QLabel(self.tr("Zoznam klubov"))
        #layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        layout.addWidget(self.table)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Zakázanie editácie

        self.load_data()

    def load_data(self):
        clubs = db.db_manager.fetch_clubs()
        self.table.setRowCount(len(clubs))
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setWordWrap(False)
        self.table.setStyleSheet("QTableWidget { font-size: 10pt; }")

        self.table.setHorizontalHeaderLabels([
            self.tr("Club Name"),
            self.tr("Street"),
            self.tr("City"),
            self.tr("ZIP Code"),
            self.tr("Country"),
            self.tr("Email"),
            self.tr("Phone"),
            self.tr("Webpage"),
            self.tr("President"),
            self.tr("Member Count"),
            self.tr("Actions"),
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Club Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Street
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # City
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # ZIP Code
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Country
        header.setSectionResizeMode(5, QHeaderView.Interactive) # Email
        header.setSectionResizeMode(6, QHeaderView.Interactive) # Phone
        header.setSectionResizeMode(7, QHeaderView.Interactive) # Webpage
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # President
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents) # Member Count
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Actions
        self.table.setColumnWidth(5, 230)
        self.table.setColumnWidth(6, 170)
        self.table.setColumnWidth(7, 230)
        header.setStretchLastSection(False) # Posledný stĺpec vyplní zvyšok

        
        # Nastavenie tmavého štýlu pre hlavičku tabuľky
        self.table.horizontalHeader().setStyleSheet(get_table_header_stylesheet())
        self.table.setAlternatingRowColors(True)

        for row, club in enumerate(clubs):
            self._set_text_item(row, 0, club.name)
            self._set_text_item(row, 1, club.street)
            self._set_text_item(row, 2, club.city)
            self._set_text_item(row, 3, club.zip_code)
            self._set_text_item(row, 4, club.country)
            self._set_text_item(row, 5, club.email)
            self._set_text_item(row, 6, club.phone)
            self._set_text_item(row, 7, club.webpage)
            self._set_text_item(row, 8, club.president_name)
            self._set_text_item(row, 9, str(club.member_count))
            btn_view = QPushButton(self.tr("View"))
            # Uistite sa, že lambda správne viaže aktuálnu hodnotu club['id']
            btn_view.clicked.connect(lambda checked, cid=club.club_id: self.show_members_list(cid))
            self.table.setCellWidget(row, 10, btn_view)

    def _set_text_item(self, row: int, column: int, value):
        text = "" if value is None else str(value)
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        self.table.setItem(row, column, item)
            
    def show_members_list(self, club_id: int):
        self.navigateToMembers.emit(club_id)

    def request_new_club_creation(self):
        """Otvorí dialóg pre vytvorenie nového klubu."""
        # ClubManagementDialog s is_new=True a club=None sa postará o logiku nového klubu
        dlg = ClubManagementDialog(club=None, is_new=True, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            # Ak bol nový klub úspešne pridaný a uložený (dialóg vrátil Accepted),
            # obnovíme zoznam klubov, aby sa zobrazil nový klub.
            self.load_data()
