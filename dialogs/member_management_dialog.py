# dialogs/member_management_dialog.py
import os, copy, datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFormLayout,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QPushButton,
    QMessageBox, QInputDialog, QDateEdit
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap, QIcon
import db
from model import Club, Member
from utils import get_state_pixmap,get_icon, show_warning_message, show_info_message, show_success_message, show_error_message
import utils # Zmenený import

class MemberManagementDialog(QDialog):
    def __init__(self, club:Club, member:Member=None, is_new=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Member Management"))
        self.setModal(True)
        self.resize(600, 400)
        
        self.setWindowIcon(get_icon("logo.ico"))

        self.club = club
        self.member = member
        if is_new:
            self.member = Member(
                status=None,  # Assuming 'status' is the translated attribute for 'stav'
                title_prefix="",
                first_name="",
                last_name="",
                title_suffix="",
                phone="",
                email="",
                encrypted_birth_date=None, # Assuming this is the correct param for encrypted date
                street="",
                city="",
                zip_code="", # Kód krajiny bude prednastavený nižšie
                country="",
                primary_club_id=club.club_id, # Assuming club.club_id is correct
                # Ensure all required non-optional parameters for Member are provided
                # or have defaults in the Member class __init__
            )
        # Make a deep copy if Member object contains mutable types like lists, or if it's modified in place
        self.original_member = copy.deepcopy(self.member) if self.member else None
        self.is_new = is_new
        self.edit_mode = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.lbl_state = QLabel()
        self.lbl_state.setPixmap(get_state_pixmap(self.member, self.club))
        # self.lbl_state.setPixmap(QPixmap("caver_black.png").scaled(20,20,Qt.KeepAspectRatio)) # Example for new member icon
        form_layout.addRow(self.tr("Status:"), self.lbl_state)

        self.le_title_prefix = QLineEdit(self.member.title_prefix)
        self.le_first_name = QLineEdit(self.member.first_name)
        self.le_last_name = QLineEdit(self.member.last_name)
        self.le_title_suffix = QLineEdit(self.member.title_suffix)

        self.de_birth_date = QDateEdit()
        self.de_birth_date.setCalendarPopup(True)
        birth_date_val = self.member.birth_date # Assuming translated attribute
        if birth_date_val:
            if isinstance(birth_date_val, str): # Should ideally be date object from model
                qdate = QDate.fromString(birth_date_val, "yyyy-MM-dd")
            else:
                qdate = QDate(birth_date_val.year, birth_date_val.month, birth_date_val.day)
            self.de_birth_date.setDate(qdate)
        else:
            self.de_birth_date.setDate(QDate.currentDate()) # Or handle None appropriately
        self.le_street = QLineEdit(self.member.street)
        self.le_city = QLineEdit(self.member.city)
        self.le_zip_code = QLineEdit(self.member.zip_code)

        self.cb_country = QComboBox()
        countries_data = utils.get_world_countries() # Načíta krajiny podľa preferovaného jazyka
        for country_name, country_code in countries_data:
            self.cb_country.addItem(country_name, country_code)
        
        country_to_select = self.member.country if self.member.country else utils.get_preferred_country_code()
        idx = self.cb_country.findData(country_to_select)
        self.cb_country.setCurrentIndex(idx if idx >=0 else 0)
        self.le_phone = QLineEdit(self.member.phone)
        self.le_email = QLineEdit(self.member.email)
        form_layout.addRow(self.tr("Title (Prefix):"), self.le_title_prefix)
        form_layout.addRow(self.tr("First Name:"), self.le_first_name)
        form_layout.addRow(self.tr("Last Name:"), self.le_last_name)
        form_layout.addRow(self.tr("Title (Suffix):"), self.le_title_suffix)
        form_layout.addRow(self.tr("Birth Date:"), self.de_birth_date)
        form_layout.addRow(self.tr("Street:"), self.le_street)
        form_layout.addRow(self.tr("City:"), self.le_city)
        form_layout.addRow(self.tr("ZIP Code:"), self.le_zip_code)
        form_layout.addRow(self.tr("Country:"), self.cb_country)
        form_layout.addRow(self.tr("Phone:"), self.le_phone)
        form_layout.addRow(self.tr("Email:"), self.le_email)

        self.cb_status = QComboBox()
        # This order will be reflected in the ComboBox dropdown.
        self.member_statuses = ["applicant", "active", "inactive", "blocked"]
        
        self.cb_status.addItem(self.tr("Applicant"), "applicant")
        self.cb_status.addItem(self.tr("Active"), "active")
        self.cb_status.addItem(self.tr("Inactive"), "inactive")
        self.cb_status.addItem(self.tr("Blocked"), "blocked")

        status_to_select = self.member.status if self.member.status and self.member.status in self.member_statuses else "applicant"
        index = self.cb_status.findData(status_to_select) # Use findData for internal value
        if self.is_new:
            index = 1
        self.cb_status.setCurrentIndex(index if index >= 0 else 0) # Default to first item if not found
        form_layout.addRow(self.tr("Membership Status:"), self.cb_status)

        self.chk_fee_paid = QCheckBox(self.tr("Membership Fee Paid"))
        self.chk_discounted = QCheckBox(self.tr("Discounted Membership"))
        self.chk_is_president = QCheckBox(self.tr("President"))
        self.chk_fee_paid.setChecked(self.member.has_paid_fee()) # Assuming translated method
        self.chk_discounted.setChecked(self.member.discounted_membership) # Assuming translated attribute
        if not self.is_new:
            self.chk_is_president.setChecked(self.member.member_id == self.club.president_id) # Assuming translated attribute
        form_layout.addRow("", self.chk_fee_paid)
        form_layout.addRow("", self.chk_discounted)
        form_layout.addRow("", self.chk_is_president) # President checkbox
        self.chk_is_president.setEnabled(False) # President status is usually managed via club dialog or specific logic
        layout.addLayout(form_layout)

        # Section for club memberships
        if not self.is_new and self.member.member_id is not None:
            self.memberships = db.db_manager.fetch_memberships_by_member(self.member.member_id)
        else:
            self.memberships = []
        clubs_section_layout = QHBoxLayout() # Renamed for clarity
        self.list_member_clubs = QListWidget() # Renamed for clarity
        clubs_section_layout.addWidget(self.list_member_clubs)
        btns_layout = QVBoxLayout()
        self.btn_add_club_membership = QPushButton(self.tr("➕ Add Club Membership"))
        self.btn_add_club_membership.clicked.connect(self.add_club_membership)
        btns_layout.addWidget(self.btn_add_club_membership)
        self.btn_remove_club_membership = QPushButton(self.tr("➖ Remove Club Membership"))
        self.btn_remove_club_membership.clicked.connect(self.remove_selected_club)
        btns_layout.addWidget(self.btn_remove_club_membership)
        self.btn_set_primary_club = QPushButton(self.tr("⭐ Set as Primary Club"))
        self.btn_set_primary_club.clicked.connect(self.set_selected_primary_club)
        btns_layout.addWidget(self.btn_set_primary_club)
        clubs_section_layout.addLayout(btns_layout)
        layout.addLayout(clubs_section_layout)
        self.update_member_clubs_list()
        btn_layout = QHBoxLayout()
        self.btn_edit = QPushButton(self.tr("Edit"))
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        btn_layout.addWidget(self.btn_edit)
        self.btn_save = QPushButton(self.tr("Save"))
        self.btn_save.clicked.connect(self.save_changes)
        self.btn_save.setVisible(False)
        btn_layout.addWidget(self.btn_save)
        self.btn_issue_ecp = QPushButton(self.tr("Issue eCP & eCard")) # Renamed and translated
        if self.is_new:
            self.btn_issue_ecp.setEnabled(False)
        elif self.member.ecp_hash is not None: # Assuming translated attribute
            self.btn_issue_ecp.setEnabled(False)
            self.btn_issue_ecp.setToolTip(self.tr("eCP is already activated or an eCP issuance request has been submitted."))
        elif self.member.email == "":
            self.btn_issue_ecp.setEnabled(False)
            self.btn_issue_ecp.setToolTip(self.tr("Member must have an email address specified."))
        from dialogs.ecp_issuance_dialog import ECPIssuanceDialog
        self.btn_issue_ecp.clicked.connect(self.issue_ecp_action) # Renamed method
        btn_layout.addWidget(self.btn_issue_ecp)

        if not self.is_new:
            self.btn_delete = QPushButton(self.tr("Delete Member"))
            self.btn_delete.clicked.connect(self.delete_member)
            btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)
        if self.is_new:
            self.unlock_fields()
            self.btn_edit.hide()
            self.btn_save.show()
        else:
            self.lock_fields()

    def update_member_clubs_list(self):
        self.list_member_clubs.clear()
        for membership in self.memberships:
            text = membership.club_name # Assuming translated attribute
            if bool(membership.is_primary_club): # Assuming translated attribute
                text += " ★"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, membership.club_id)
            self.list_member_clubs.addItem(item)

    def add_club_membership(self):
        if not self.member.member_id:
            show_warning_message(self.tr("Please save member data first."))
            return
        all_clubs = db.db_manager.fetch_clubs()
        existing_ids = {self.list_member_clubs.item(i).data(Qt.UserRole) for i in range(self.list_member_clubs.count())}
        available_clubs = [club for club in all_clubs if club.club_id not in existing_ids]
        if not available_clubs:
            show_info_message(self.tr("All clubs are already assigned."))
            return
        club_names = [club.name for club in available_clubs] # Assuming translated attribute club.name
        selected, ok = QInputDialog.getItem(self, self.tr("Add Club Membership"), self.tr("Select club:"), club_names, 0, False)
        if ok and selected:
            club = next((club_obj for club_obj in available_clubs if club_obj.name == selected), None) # Renamed var
            if club is not None:
                db.db_manager.insert_memberships(self.member.member_id, club.club_id, primary_club=False) # Pass club_id
                self.memberships = db.db_manager.fetch_memberships_by_member(member_id=self.member.member_id)
                self.update_member_clubs_list()
                show_success_message(self.tr(f"Club '{selected}' has been added to memberships."))

    def remove_selected_club(self):
        selected_item = self.list_member_clubs.currentItem()
        if not selected_item:
            show_info_message(self.tr("No club selected."))
            return
        club_id = selected_item.data(Qt.UserRole)
        for membership in self.memberships:
            if membership.club_id == club_id and bool(membership.is_primary_club): # Assuming translated attribute
                show_warning_message(self.tr("Cannot remove primary club. Please change the primary club first."))
                return
        db.db_manager.delete_memberships(self.member.member_id, club_id)
        self.memberships = db.db_manager.fetch_memberships_by_member(member_id=self.member.member_id)
        self.update_member_clubs_list()
        show_success_message(self.tr("Club has been removed from memberships."))

    def set_selected_primary_club(self):
        selected_item = self.list_member_clubs.currentItem()
        if not selected_item:
            show_info_message(self.tr("No club selected."))
            return
        club_id = selected_item.data(Qt.UserRole)
        db.db_manager.set_primary_memberships(self.member.member_id, club_id)
        self.memberships = db.db_manager.fetch_memberships_by_member(member_id=self.member.member_id)
        self.update_member_clubs_list()
        show_success_message(self.tr("Primary club has been changed."))

    def lock_fields(self):
        self.le_title_prefix.setReadOnly(True)
        self.le_title_prefix.setStyleSheet("background-color: #E8E8E8;")
        self.le_first_name.setReadOnly(True)
        self.le_first_name.setStyleSheet("background-color: #E8E8E8;")
        self.le_last_name.setReadOnly(True)
        self.le_last_name.setStyleSheet("background-color: #E8E8E8;")
        self.le_title_suffix.setReadOnly(True)
        self.le_title_suffix.setStyleSheet("background-color: #E8E8E8;")
        self.de_birth_date.setReadOnly(True)
        self.de_birth_date.setStyleSheet("background-color: #E8E8E8;")
        self.le_street.setReadOnly(True)
        self.le_street.setStyleSheet("background-color: #E8E8E8;")
        self.le_city.setReadOnly(True)
        self.le_city.setStyleSheet("background-color: #E8E8E8;")
        self.le_zip_code.setReadOnly(True)
        self.le_zip_code.setStyleSheet("background-color: #E8E8E8;")
        self.cb_country.setEnabled(False)
        self.cb_country.setStyleSheet("background-color: #E8E8E8;")
        self.le_phone.setReadOnly(True)
        self.le_phone.setStyleSheet("background-color: #E8E8E8;")
        self.le_email.setReadOnly(True)
        self.le_email.setStyleSheet("background-color: #E8E8E8;")
        self.cb_status.setEnabled(False)
        self.btn_add_club_membership.setVisible(False)
        self.btn_remove_club_membership.setVisible(False)
        self.btn_set_primary_club.setVisible(False)
        self.chk_fee_paid.setEnabled(False)
        self.chk_discounted.setEnabled(False)
        self.chk_is_president.setEnabled(False)
        self.btn_edit.setVisible(True)
        self.btn_save.setVisible(False)
        self.edit_mode = False

    def unlock_fields(self):
        self.le_title_prefix.setReadOnly(False)
        self.le_title_prefix.setStyleSheet("")
        self.le_first_name.setReadOnly(False)
        self.le_first_name.setStyleSheet("background-color: #E8D888;")
        self.le_last_name.setReadOnly(False)
        self.le_last_name.setStyleSheet("background-color: #E8D888;")
        self.le_title_suffix.setReadOnly(False)
        self.le_title_suffix.setStyleSheet("")
        self.de_birth_date.setReadOnly(False)
        self.de_birth_date.setStyleSheet("background-color: #E8D888;")
        self.le_street.setReadOnly(False)
        self.le_street.setStyleSheet("")
        self.le_city.setReadOnly(False)
        self.le_city.setStyleSheet("")
        self.le_zip_code.setReadOnly(False)
        self.le_zip_code.setStyleSheet("")
        self.cb_country.setEnabled(True)
        self.cb_country.setStyleSheet("")
        self.le_phone.setReadOnly(False)
        self.le_phone.setStyleSheet("")
        self.le_email.setReadOnly(False)
        self.le_email.setStyleSheet("background-color: #E8D888;")
        self.cb_status.setEnabled(True)
        self.btn_add_club_membership.setVisible(True)
        self.btn_remove_club_membership.setVisible(True)
        self.btn_set_primary_club.setVisible(True)
        self.chk_fee_paid.setEnabled(True)
        self.chk_discounted.setEnabled(True)
        self.chk_is_president.setEnabled(False)
        self.edit_mode = True

    def toggle_edit_mode(self):
        if not self.edit_mode:
            self.unlock_fields()
            self.btn_edit.setVisible(False)
            self.btn_save.setVisible(True)
            self.edit_mode = True
        else:
            self.cancel_changes()

    def save_changes(self):
        # Update member object with data from fields
        self.member.status = self.cb_status.currentData() # Get internal value
        self.member.title_prefix = self.le_title_prefix.text()
        self.member.first_name = self.le_first_name.text()
        self.member.last_name = self.le_last_name.text()
        self.member.title_suffix = self.le_title_suffix.text()
        # Convert QDate to Python date object for the model
        q_date = self.de_birth_date.date()
        self.member.birth_date = datetime.date(q_date.year(), q_date.month(), q_date.day()) if q_date.isValid() else None
        self.member.street = self.le_street.text()
        self.member.city = self.le_city.text()
        self.member.zip_code = self.le_zip_code.text()
        self.member.country = self.cb_country.currentData() # Uložíme kód krajiny
        self.member.phone = self.le_phone.text()
        self.member.email = self.le_email.text()
        self.member.discounted_membership = self.chk_discounted.isChecked()
        # is_president is derived, not directly set here usually

        if not self.member.member_id:
            # Ensure primary_club_id is set for new member
            self.member.primary_club_id = self.club.club_id
            self.member.member_id = db.db_manager.insert_member(self.member)
            if self.member.member_id: # Check if insert was successful
                db.db_manager.insert_memberships(member_id=self.member.member_id, club_id=self.club.club_id, primary_club=True)
            else:
                show_error_message(self.tr("Failed to save new member."))
                return
        else: # Existing member
            db.db_manager.update_member(self.member)

        if self.chk_fee_paid.isChecked():
            # Use set_paid_fee which handles logic and DB insert
            self.member.set_paid_fee(year=datetime.datetime.now().year)
        
        self.original_member = copy.deepcopy(self.member) # Update original with new state
        show_success_message(self.tr("Changes have been saved."))
        self.lock_fields() # Lock fields after saving for existing member, or after first save for new
        self.accept()

    def cancel_changes(self):
        if self.is_new:
            self.reject()
            return
        # Restore from original_member
        self.member = copy.deepcopy(self.original_member) # Restore member state
        self.le_title_prefix.setText(self.original_member.title_prefix)
        self.le_first_name.setText(self.original_member.first_name)
        self.le_last_name.setText(self.original_member.last_name)
        self.le_title_suffix.setText(self.original_member.title_suffix)
        # Example for birth_date:
        birth_date_val = self.original_member.birth_date
        self.de_birth_date.setDate(QDate(birth_date_val.year, birth_date_val.month, birth_date_val.day) if birth_date_val else QDate.currentDate())
        self.le_street.setText(self.original_member.street)
        self.le_city.setText(self.original_member.city)
        self.le_zip_code.setText(self.original_member.zip_code)
        # Nastavenie ComboBoxu pre krajinu
        idx = self.cb_country.findData(self.original_member.country)
        self.cb_country.setCurrentIndex(idx if idx >=0 else 0)
        self.le_phone.setText(self.original_member.phone)
        self.le_email.setText(self.original_member.email) # Corrected from self.member.email to self.original_member.email

        # Restore status from original_member, defaulting to "ziadatel"
        status_to_restore = self.original_member.status if self.original_member.status and self.original_member.status in self.member_statuses else "applicant"
        index_to_restore = self.cb_status.findData(status_to_restore) # Use findData for internal value
        self.cb_status.setCurrentIndex(index_to_restore if index_to_restore >= 0 else 0)

        self.chk_fee_paid.setChecked(self.original_member.has_paid_fee())
        self.chk_discounted.setChecked(self.original_member.discounted_membership)
        self.chk_is_president.setChecked(self.original_member.member_id == self.club.president_id)
        self.lock_fields()
        # self.accept() # Usually cancel doesn't auto-close, but depends on desired UX

    def delete_member(self):
        if self.chk_is_president.isChecked():
            show_error_message(self.tr("Cannot delete the club president. Please change their status first."))
            return
        reply = QMessageBox.question(self, self.tr("Confirm Deletion"),
                                     self.tr("Deleting a member will remove all their data. Do you want to continue?"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            db.db_manager.delete_member(self.member.member_id)
            show_success_message(self.tr(f"Member {self.member.first_name} {self.member.last_name} has been deleted."))
            self.accept()

    def issue_ecp_action(self): # Renamed method
        from dialogs.ecp_issuance_dialog import ECPIssuanceDialog
        dlg = ECPIssuanceDialog(self.member, self)
        dlg.exec_()
        # Potentially refresh eCP status related UI elements if dialog was accepted
        if dlg.result() == QDialog.Accepted:
            self.member = db.db_manager.fetch_member_by_id(self.member.member_id) # Re-fetch member to get updated ecp_hash
            self.btn_issue_ecp.setEnabled(self.member.ecp_hash is None and bool(self.member.email))
            if self.member.ecp_hash:
                 self.btn_issue_ecp.setToolTip(self.tr("eCP is already activated or an eCP issuance request has been submitted."))
            elif not self.member.email:
                 self.btn_issue_ecp.setToolTip(self.tr("Member must have an email address specified."))
            else:
                 self.btn_issue_ecp.setToolTip("")
