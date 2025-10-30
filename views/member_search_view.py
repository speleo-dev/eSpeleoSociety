# views/member_search_view.py
from typing import List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog
from PyQt5.QtCore import Qt, QTimer # Pridaný import QTimer
import db
from dialogs.member_management_dialog import MemberManagementDialog # Import pre dialóg
from model import Member, Club # Import modelov
from utils import get_state_pixmap, get_table_header_stylesheet, show_info_message, show_warning_message # Pridaný import pre ikony stavu

class MemberSearchView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True) # Chceme, aby sa spustil len raz po uplynutí času
        self.search_timer.timeout.connect(self.trigger_search) # Metóda, ktorá sa zavolá po timeout-e
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("Member Search"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("First Name Last Name (min. 3 chars, space separated)"))
        self.search_edit.textChanged.connect(self.on_search_text_changed) # Prepojíme signál
        layout.addWidget(self.search_edit)
        
        # self.search_button = QPushButton("Hľadať") # Tlačidlo už nepotrebujeme
        # self.search_button.clicked.connect(self.search_member)
        # layout.addWidget(self.search_button)

        self.table = QTableWidget()
        self.table.setColumnCount(5) # Stav, Celé meno, Primárny klub, Email, Akcie
        self.table.setHorizontalHeaderLabels([self.tr("Status"), self.tr("Full Name"), self.tr("Primary Club"), self.tr("Email"), self.tr("Actions")])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Status
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Full Name
        header.setSectionResizeMode(2, QHeaderView.Stretch) # Primary Club
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Email
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Actions
        header.setStretchLastSection(False)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setWordWrap(False)
        header.setStyleSheet(get_table_header_stylesheet()) # Použitie funkcie z utils
        self.table.setStyleSheet("QTableWidget { font-size: 10pt; }")
        layout.addWidget(self.table)

    def on_search_text_changed(self, text: str):
        search_term = text.strip()
        # Vyhľadávanie sa spustí, len ak je celková dĺžka textu aspoň 3 znaky
        if len(search_term) < 3: 
            self.table.setRowCount(0) # Vyčistíme tabuľku, ak je text príliš krátky
            self.search_timer.stop() # Zastavíme časovač, ak je text krátky
            return
        self.search_timer.start(400) # Spustíme/reštartujeme časovač na 400ms

    def trigger_search(self):
        """Metóda volaná časovačom na spustenie samotného vyhľadávania."""
        search_input_string = self.search_edit.text().strip()
        if len(search_input_string) >= 3:
            self.perform_search(search_input_string)
        else:
            self.table.setRowCount(0)

    def perform_search(self, search_input_string: str):
        # Táto metóda teraz obsahuje logiku pôvodnej search_member
        # a je volaná z on_search_text_changed
        search_terms = [term for term in search_input_string.split(' ') if term] # Rozdelenie na slová a odstránenie prázdnych

        if not search_terms:
            self.table.setRowCount(0) # Vyčisti tabuľku, ak je vyhľadávací reťazec prázdny
            return
        found_members: List[Member] = db.db_manager.search_members_globally(search_terms)
        
        if not found_members:
            self.table.setRowCount(0)
            show_info_message(self.tr(f"No members found for term: '{search_input_string}'."))

        self.table.setRowCount(len(found_members))
        for row, member_obj in enumerate(found_members):
            # Získanie primárneho klubu člena
            primary_club_obj: Club = None
            if member_obj.primary_club_id: # Use translated attribute
                primary_club_obj = db.db_manager.fetch_club_by_id(member_obj.primary_club_id) # Use translated attribute

            # 1. Stĺpec: Stav (ikona)
            if primary_club_obj:
                pixmap = get_state_pixmap(member_obj, primary_club_obj)
                status_label = QLabel()
                status_label.setPixmap(pixmap)
                status_label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row, 0, status_label)
            else:
                self.table.setItem(row, 0, QTableWidgetItem("N/A")) # Ak klub nie je nájdený

            # 2. Stĺpec: Celé meno
            full_name = " ".join(filter(None, [member_obj.title_prefix, member_obj.first_name, member_obj.last_name, member_obj.title_suffix]))
            self.table.setItem(row, 1, QTableWidgetItem(full_name))

            # 3. Stĺpec: Primárny klub
            club_name = primary_club_obj.name if primary_club_obj else self.tr("Unassigned")
            self.table.setItem(row, 2, QTableWidgetItem(club_name))

            # 4. Stĺpec: Email
            self.table.setItem(row, 3, QTableWidgetItem(member_obj.email))

            # 5. Stĺpec: Akcie (tlačidlo Spravovať)
            btn_manage = QPushButton(self.tr("Manage"))
            btn_manage.clicked.connect(lambda checked, m=member_obj: self.open_member_management_dialog(m))
            self.table.setCellWidget(row, 4, btn_manage)
        self.table.resizeRowsToContents()

    def open_member_management_dialog(self, member: Member):
        if not member or not member.primary_club_id: # Use translated attribute
            show_warning_message(self.tr("Information about the member's primary club is missing or member not selected."))
            return
        
        primary_club_obj = db.db_manager.fetch_club_by_id(member.primary_club_id) # Use translated attribute
        if not primary_club_obj:
            show_warning_message(self.tr(f"Failed to load primary club (ID: {member.primary_club_id}) for member '{member.first_name} {member.last_name}'."))
            return
        
        # Prezeráme existujúceho člena, takže is_new=False
        dlg = MemberManagementDialog(club=primary_club_obj, member=member, is_new=False, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.trigger_search() 