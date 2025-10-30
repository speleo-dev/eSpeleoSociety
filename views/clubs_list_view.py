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
        self.table.setColumnCount(10) # Zvýšený počet stĺpcov o 1 pre Krajinu
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
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Email
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # Phone
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) # President
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # Member Count
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents) # Actions
        header.setStretchLastSection(False) # Posledný stĺpec vyplní zvyšok

        
        # Nastavenie tmavého štýlu pre hlavičku tabuľky
        self.table.horizontalHeader().setStyleSheet(get_table_header_stylesheet())
        self.table.setAlternatingRowColors(True)

        for row, club in enumerate(clubs):
            self.table.setItem(row, 0, QTableWidgetItem(club.name))
            self.table.setItem(row, 1, QTableWidgetItem(club.street))
            self.table.setItem(row, 2, QTableWidgetItem(club.city))
            self.table.setItem(row, 3, QTableWidgetItem(club.zip_code))
            self.table.setItem(row, 4, QTableWidgetItem(club.country))
            self.table.setItem(row, 5, QTableWidgetItem(club.email))
            self.table.setItem(row, 6, QTableWidgetItem(club.phone))
            self.table.setItem(row, 7, QTableWidgetItem(club.president_name))
            self.table.setItem(row, 8, QTableWidgetItem(str(club.member_count)))
            btn_view = QPushButton(self.tr("View"))
            # Uistite sa, že lambda správne viaže aktuálnu hodnotu club['id']
            btn_view.clicked.connect(lambda checked, cid=club.club_id: self.show_members_list(cid))
            self.table.setCellWidget(row, 9, btn_view)
            
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