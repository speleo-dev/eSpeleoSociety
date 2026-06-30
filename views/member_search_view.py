# views/member_search_view.py
from typing import List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog
from PyQt5.QtCore import Qt, QTimer # Pridaný import QTimer
import db
from dialogs.member_management_dialog import MemberManagementDialog # Import pre dialóg
from model import Member, Club # Import modelov
from member_search_filter import member_matches_fast_search
from utils import get_state_pixmap, get_table_header_stylesheet, show_warning_message # Pridaný import pre ikony stavu


MAX_RENDERED_ROWS = 300


class MemberSearchView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_members: List[Member] = []
        self.visible_members: List[Member] = []
        self.clubs_by_id = {}
        self.members_loaded = False
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True) # Chceme, aby sa spustil len raz po uplynutí času
        self.search_timer.timeout.connect(self.apply_fast_filter) # Metóda, ktorá sa zavolá po timeout-e
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("Member Search"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Fast search by first or last name..."))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search_text_changed) # Prepojíme signál
        layout.addWidget(self.search_edit)

        self.status_label = QLabel(self.tr("Loading members when this view opens..."))
        layout.addWidget(self.status_label)
        
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

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_members_loaded()

    def ensure_members_loaded(self):
        if self.members_loaded:
            return
        self.status_label.setText(self.tr("Loading members..."))
        try:
            self.clubs_by_id = {club.club_id: club for club in db.db_manager.fetch_clubs()}
            self.all_members = db.db_manager.fetch_member_search_directory()
            self.members_loaded = True
            self.apply_fast_filter()
        except Exception as exc:
            self.table.setRowCount(0)
            self.status_label.setText(self.tr("Failed to load members."))
            show_warning_message(self.tr(f"Failed to load members: {exc}"))

    def reload_members(self):
        self.members_loaded = False
        self.all_members = []
        self.visible_members = []
        self.ensure_members_loaded()

    def on_search_text_changed(self, text: str):
        if not self.members_loaded:
            self.ensure_members_loaded()
            return
        self.search_timer.start(120) # Spustíme/reštartujeme časovač na 120ms

    def trigger_search(self):
        """Metóda volaná časovačom na spustenie samotného vyhľadávania."""
        self.apply_fast_filter()

    def apply_fast_filter(self):
        if not self.members_loaded:
            return
        search_input_string = self.search_edit.text().strip()
        if search_input_string:
            found_members = [
                member for member in self.all_members
                if member_matches_fast_search(member, search_input_string)
            ]
        else:
            found_members = list(self.all_members)
        self.render_members(found_members, search_input_string)

    def perform_search(self, search_input_string: str):
        self.render_members(
            [
                member for member in self.all_members
                if member_matches_fast_search(member, search_input_string)
            ],
            search_input_string,
        )

    def render_members(self, found_members: List[Member], search_input_string: str = ""):
        self.visible_members = found_members[:MAX_RENDERED_ROWS]
        if not found_members:
            self.table.setRowCount(0)
            if search_input_string:
                self.status_label.setText(self.tr(f"No members found for term: '{search_input_string}'."))
            else:
                self.status_label.setText(self.tr("No members found."))
            return

        if len(found_members) > len(self.visible_members):
            self.status_label.setText(
                self.tr(f"Showing {len(self.visible_members)} of {len(found_members)} members. Type more letters to narrow the list.")
            )
        else:
            self.status_label.setText(self.tr(f"Showing {len(self.visible_members)} of {len(self.all_members)} members."))

        self.table.setRowCount(0)
        self.table.setRowCount(len(self.visible_members))
        for row, member_obj in enumerate(self.visible_members):
            # Získanie primárneho klubu člena
            primary_club_obj: Club = None
            if member_obj.primary_club_id: # Use translated attribute
                primary_club_obj = self.clubs_by_id.get(member_obj.primary_club_id) # Use translated attribute

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
            club_name = primary_club_obj.name if primary_club_obj else (member_obj.primary_club_name or self.tr("Unassigned"))
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
            self.reload_members()
