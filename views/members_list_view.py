# views/members_list_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QPushButton, QHBoxLayout, QMessageBox, QDialog, QGridLayout
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
from PyQt5.QtCore import Qt
from typing import List
import db
from dialogs.club_management_dialog import ClubManagementDialog
from model import Member, Club
from dialogs.member_management_dialog import MemberManagementDialog 
from inline_editing import parse_address_text, parse_full_name, parse_optional_date
from utils import get_state_pixmap, _get_scaled_pixmap_from_cache, load_image_from_url, get_table_header_stylesheet, show_warning_message, show_info_message, show_success_message, show_error_message # Added import
from views.editing_delegates import ComboBoxDelegate

MAX_MEMBERS_LIST_LOGO_WIDTH = 400
MAX_MEMBERS_LIST_LOGO_HEIGHT = 100
MEMBER_STATUSES = ["applicant", "active", "inactive", "blocked"]
MEMBER_ROLES = ["member", "president"]
MEMBER_EDITABLE_COLUMNS = set(range(0, 9))

class MembersListView(QWidget):
    def __init__(self, parent_window=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.current_club: Club = None
        self.members: List[Member] = []
        self._loading = False
        #self.table = QTableWidget() # We define the table as a class attribute
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # === New header (club information + legend) ===
        self.club_header_widget = QWidget()
        club_header_layout = QHBoxLayout(self.club_header_widget)

        # Left side: club information and "Manage Club" button
        left_section_layout = QVBoxLayout() # We use QVBoxLayout for better arrangement
        
        self.club_details_label = QLabel(self.tr("Loading club information..."))
        self.club_details_label.setStyleSheet("font-size: 14px; margin-bottom: 5px;") # Adjusted style
        self.club_details_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        left_section_layout.addWidget(self.club_details_label)
        self.btn_manage_club = QPushButton(self.tr("Manage Club"))
        self.btn_manage_club.clicked.connect(self.manage_current_club)
        self.btn_manage_club.setEnabled(False) # Initially inactive
        left_section_layout.addWidget(self.btn_manage_club, alignment=Qt.AlignLeft) # Button alignment
        
        # Middle part: Club Logo
        self.club_logo_preview_label = QLabel(self.tr("No Logo"))
        self.club_logo_preview_label.setAlignment(Qt.AlignCenter)
        self.club_logo_preview_label.setFixedSize(MAX_MEMBERS_LIST_LOGO_WIDTH, MAX_MEMBERS_LIST_LOGO_HEIGHT) # Default size
        #self.club_logo_preview_label.setStyleSheet("border: 1px solid #B0B0B0; background-color: #FFFFFF;")

        club_header_layout.addLayout(left_section_layout)
        club_header_layout.addStretch(1) 
        club_header_layout.addWidget(self.club_logo_preview_label) # logo
        club_header_layout.addStretch(1) 
        
        # Right side: legend
        legend_widget = QWidget()
        legend_layout = QGridLayout(legend_widget)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(2)
        legend_layout.setHorizontalSpacing(20)
        
        IMG_SIZE = 18 # Veľkosť ikoniek v legende
        FIX_SIZE = 18 # Fixed size of QLabel for the icon

        legend_items = [
            ("caver_green.png", self.tr("Active")), ("caver_gray_inv.png", self.tr("Inactive")),
            ("caver_baned.png", self.tr("Blocked")), ("caver_gray_dark.png", self.tr("Applicant")),
            ("caver_yellow.png", self.tr("Guest")), ("caver_gold.png", self.tr("President")),
            ("star_icon.png", self.tr("Discounted Membership")), ("wallet-icon_72.png", self.tr("eCP Issued")),
            ("exclamation_icon.png", self.tr("Unpaid Fee"))
        ]

        for i, (icon_filename, text) in enumerate(legend_items):
            hbox = QHBoxLayout()
            hbox.setContentsMargins(0,0,3,0)
            hbox.setSpacing(2)
            icon_label = QLabel() # Renamed for clarity
            if icon_filename:
                pixmap = _get_scaled_pixmap_from_cache(icon_filename, IMG_SIZE) # Renamed for clarity
                if pixmap:
                    icon_label.setPixmap(pixmap)
            
            icon_label.setFixedSize(FIX_SIZE + 10, FIX_SIZE)
            icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # icon_label.setContentsMargins(0,0,10,0)
            hbox.addWidget(icon_label)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("font-size: 10pt;")
            text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            hbox.addWidget(text_label)

            legend_layout.addLayout(hbox, i // 2, i % 2) # Arrangement in 2 columns

        
        club_header_layout.addWidget(legend_widget)
        layout.addWidget(self.club_header_widget)
        # === End of new header ===

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            self.tr("Status"), self.tr("Role"), self.tr("Title"), self.tr("Full Name"),
            "", self.tr("Birth Date"), self.tr("Address"), 
            self.tr("Phone"), self.tr("Email"), self.tr("Actions")
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Status
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Role
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Title
        header.setSectionResizeMode(3, QHeaderView.Stretch) # Full Name
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # "" (Title Suffix)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Birth Date
        header.setSectionResizeMode(6, QHeaderView.Stretch) # Address
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) # Phone
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # Email
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents) # Actions
        header.setStretchLastSection(False)

        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setWordWrap(False)
        header.setStyleSheet(get_table_header_stylesheet())
        self.table.setStyleSheet("QTableWidget { font-size: 8pt; }")
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setItemDelegateForColumn(0, ComboBoxDelegate(MEMBER_STATUSES, self.table))
        self.table.setItemDelegateForColumn(1, ComboBoxDelegate(MEMBER_ROLES, self.table))
        self.table.itemChanged.connect(self._handle_item_changed)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Buttons below the table
        button_layout = QHBoxLayout()
        # Pridanie tlačidla "Mass Fee Update"
        btn_mass_fee_update = QPushButton(self.tr("Mass Fee Update"))
        btn_mass_fee_update.clicked.connect(self.mass_fee_update_members)
        button_layout.addWidget(btn_mass_fee_update)
        button_layout.addStretch()
        btn_add_member = QPushButton(self.tr("➕ Add Member"))
        btn_add_member.clicked.connect(self.add_new_member)
        button_layout.addWidget(btn_add_member)
        layout.addLayout(button_layout)

    def manage_current_club(self):
        if self.parent_window and self.current_club:
            self.open_club_management(self.current_club)
        elif not self.current_club:
            show_warning_message(self.tr("No club selected."))
        elif not self.parent_window:
            show_warning_message(self.tr("Missing reference to the main window."))

    def load_data_for_club(self, club: Club):
        self._loading = True
        self.current_club = club
        if not club:
            self.club_details_label.setText(self.tr("No club selected."))
            self.table.setRowCount(0)
            self.btn_manage_club.setEnabled(False)
            self._loading = False
            return

        header_text = (
            f"<b>{self.tr('Club')}: {club.name}</b><br>"
            f"{self.tr('Street')}: {club.street}<br>"
            f"{self.tr('City')}: {club.city}<br>"
            f"{self.tr('ZIP Code')}: {club.zip_code}<br>"
            f"{self.tr('Country')}: {club.country}<br>"
            f"{self.tr('Email')}: {club.email}<br>"
            f"{self.tr('Phone')}: {club.phone}<br>"
            f"{self.tr('Webpage')}: {club.webpage}<br>"
            f"{self.tr('President')}: {club.president_name if club.president_name else 'N/A'}"
        )
        self.club_details_label.setText(header_text)
        self.club_details_label.setStyleSheet("QTableWidget { font-size: 12pt; }")
        self.btn_manage_club.setEnabled(True)

        # Load and display the club logo
        self.club_logo_preview_label.setPixmap(QPixmap()) # Clear previous logo
        if club.logo_url:
            self.club_logo_preview_label.setText(self.tr("Loading logo..."))
            pixmap = load_image_from_url(club.logo_url, max_size=(MAX_MEMBERS_LIST_LOGO_WIDTH, MAX_MEMBERS_LIST_LOGO_HEIGHT))
            if pixmap:
                self.club_logo_preview_label.setPixmap(pixmap)
                self.club_logo_preview_label.setFixedSize(pixmap.size()) # Adjust QLabel size to the image
                self.club_logo_preview_label.setText("")
            else:
                self.club_logo_preview_label.setText(self.tr("Logo not found"))
                self.club_logo_preview_label.setFixedSize(MAX_MEMBERS_LIST_LOGO_WIDTH, MAX_MEMBERS_LIST_LOGO_HEIGHT) # Reset to placeholder
        else:
            self.club_logo_preview_label.setText(self.tr("No Logo"))
            self.club_logo_preview_label.setFixedSize(MAX_MEMBERS_LIST_LOGO_WIDTH, MAX_MEMBERS_LIST_LOGO_HEIGHT) # Reset na placeholder

        self.members: List[Member] = db.db_manager.fetch_members(club.club_id)
        self.table.setRowCount(len(self.members))

        for row, member_obj in enumerate(self.members):
            try:
                pixmap = get_state_pixmap(member_obj, self.current_club)
                self._set_text_item(row, 0, member_obj.status or "", icon=QIcon(pixmap))
            except Exception as e:
                print(f"Error loading state pixmap for member {member_obj.first_name}: {e}") # Use translated attribute
                self._set_text_item(row, 0, member_obj.status or "") # Use translated attribute

            role_text = "president" if member_obj.is_president else "member"
            self._set_text_item(row, 1, role_text)
            self._set_text_item(row, 2, member_obj.title_prefix or "")
            self._set_text_item(row, 3, f"{member_obj.first_name} {member_obj.last_name}")
            self._set_text_item(row, 4, member_obj.title_suffix or "")
            self._set_text_item(row, 5, str(member_obj.birth_date) if member_obj.birth_date else "") # Uses property
            address_parts = [
                member_obj.street,
                member_obj.city,
                member_obj.zip_code,
                member_obj.country
            ]
            full_address = ", ".join(part for part in address_parts if part and part.strip())
            self._set_text_item(row, 6, full_address)
            self._set_text_item(row, 7, member_obj.phone or "")
            self._set_text_item(row, 8, member_obj.email or "")
            
            btn_manage = QPushButton(self.tr("Manage"))
            btn_manage.clicked.connect(lambda checked, m=member_obj: self.open_member_management_dialog(m))
            self.table.setCellWidget(row, 9, btn_manage)
        self._loading = False
        
        #self.table.resizeColumnsToContents()

    def _set_text_item(self, row: int, column: int, value, icon: QIcon = None):
        text = "" if value is None else str(value)
        item = QTableWidgetItem(icon, text) if icon else QTableWidgetItem(text)
        item.setToolTip(text)
        item.setData(Qt.UserRole, text)
        flags = item.flags()
        if column in MEMBER_EDITABLE_COLUMNS:
            item.setFlags(flags | Qt.ItemIsEditable)
        else:
            item.setFlags(flags & ~Qt.ItemIsEditable)
        self.table.setItem(row, column, item)

    def _handle_item_changed(self, item: QTableWidgetItem):
        if self._loading or item.column() not in MEMBER_EDITABLE_COLUMNS:
            return
        if item.row() >= len(self.members) or not self.current_club:
            return

        member = self.members[item.row()]
        old_value = item.data(Qt.UserRole) or ""
        new_value = item.text().strip()
        if new_value == old_value:
            return

        try:
            reload_after_save = self._apply_member_edit(member, item.column(), new_value)
            item.setData(Qt.UserRole, new_value)
            item.setToolTip(new_value)
            if item.column() == 0:
                item.setIcon(QIcon(get_state_pixmap(member, self.current_club)))
            if reload_after_save:
                updated_club = db.db_manager.fetch_club_by_id(self.current_club.club_id)
                self.load_data_for_club(updated_club or self.current_club)
        except Exception as exc:
            self._loading = True
            item.setText(old_value)
            self._loading = False
            show_error_message(self.tr("Failed to save member value: ") + str(exc))

    def _apply_member_edit(self, member: Member, column: int, value: str) -> bool:
        if column == 0:
            if value not in MEMBER_STATUSES:
                raise ValueError(self.tr("Unsupported member status."))
            member.status = value
            db.db_manager.update_member(member)
        elif column == 1:
            if value not in MEMBER_ROLES:
                raise ValueError(self.tr("Unsupported member role."))
            db.db_manager.set_club_member_role(self.current_club.club_id, member.member_id, value)
            return True
        elif column == 2:
            member.title_prefix = value
            db.db_manager.update_member(member)
        elif column == 3:
            member.first_name, member.last_name = parse_full_name(value)
            db.db_manager.update_member(member)
        elif column == 4:
            member.title_suffix = value
            db.db_manager.update_member(member)
        elif column == 5:
            member.birth_date = parse_optional_date(value)
            db.db_manager.update_member_birth_date(member.member_id, member.birth_date)
        elif column == 6:
            address = parse_address_text(value)
            member.street = address.street
            member.city = address.city
            member.zip_code = address.zip_code
            member.country = address.country
            db.db_manager.update_member(member)
        elif column == 7:
            member.phone = value
            db.db_manager.update_member(member)
        elif column == 8:
            member.email = value
            db.db_manager.update_member(member)
        return False

    def open_member_management_dialog(self, member: Member = None, is_new: bool = False):
        if not self.current_club:
            show_warning_message(self.tr("No club selected for member management."))
            return
        
        dlg = MemberManagementDialog(club=self.current_club, member=member, is_new=is_new, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_data_for_club(self.current_club) # Refresh the list

    def open_club_management(self, club:Club):
        dlg = ClubManagementDialog(club=club, parent=self)
        # We save the result of the dialog
        result = dlg.exec_()

        # If the dialog was accepted (e.g., the user clicked "Save")
        if result == QDialog.Accepted:
            # Skontrolujeme, či klub spravovaný v dialógu je ten istý,
            # ktorý je aktuálne zobrazený v tomto MembersListView.
            if self.current_club and self.current_club.club_id == club.club_id:
                # We load potentially updated club data from the database
                updated_club_data = db.db_manager.fetch_club_by_id(club.club_id)
                if updated_club_data:
                    # We reload the data for the club, which also updates the header
                    self.load_data_for_club(updated_club_data)
                    # After successfully updating this view, also refresh the main clubs list view
                    if self.parent_window and hasattr(self.parent_window, 'clubs_list_view'):
                        self.parent_window.clubs_list_view.load_data()
                else:
                    # This case can occur if the club was deleted in the meantime (less likely from the management dialog)
                    show_warning_message(self.tr(f"Failed to load updated data for club ID: {club.club_id}."))

    def add_new_member(self):
        self.open_member_management_dialog(member=None, is_new=True)

    def mass_fee_update_members(self):
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            show_info_message(self.tr("You have not selected any members."))
            return
        
        count = len(selected_indexes)
        current_year = db.datetime.datetime.now().year
        member_names = [f"{self.members[index.row()].first_name} {self.members[index.row()].last_name}" for index in selected_indexes]
        member_names_str = ", ".join(member_names)
        
        reply = QMessageBox.question(self, self.tr("Confirmation"),
                                    self.tr(f"You have selected {count} members ({member_names_str}).\nSet membership fee as paid for the year {current_year}?"),
                                    QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            for index in selected_indexes:
                member: Member = self.members[index.row()]
                member.set_paid_fee() # The set_paid_fee method already handles the current year and DB write
            show_success_message(self.tr("Fees have been set for the selected members."))
            self.load_data_for_club(self.current_club) # Refresh the list
