# dialogs/club_management_dialog.py
import os, copy, uuid
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDateEdit, QComboBox,
                             QPushButton, QHBoxLayout, QMessageBox, QLabel, QFileDialog, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QBuffer, QIODevice
from PyQt5.QtGui import QIcon, QPixmap
import db, utils
from utils import show_success_message, show_warning_message, show_error_message, show_info_message # Added imports
from model import Club, Membership, Member
from utils import get_icon, load_image_from_url, upload_to_bucket, delete_object_from_bucket_by_url
from config import secret_manager

MAX_LOGO_PREVIEW_DIMENSION = 250

class ClubManagementDialog(QDialog):
    def __init__(self, club=None, is_new=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Club Management"))
        self.resize(500, 300)
        self.setWindowIcon(get_icon("logo.ico"))
        self.is_new = is_new
        self.club = club # club_id, name, address, email, phone, president_id, president_name, foundation_date, member_count, logo_url
        self.setMinimumWidth(600) # Allow dialog to be wider for larger logo
        if self.is_new:
            # club_id, name, street, city, zip_code, email, phone, president_id, foundation_date, logo_url
            self.club = Club(None, "", "", "", "", "", "", None, "", None, 0, None)
        self.original_club_data = copy.copy(self.club) # Renamed for consistency
        self.edit_mode = is_new
        self.selected_logo_path = None
        self.logo_pixmap = None
        self.init_ui()
        self.load_club_logo_preview()
        if self.is_new: # Adjust size after UI is built and initial logo (or placeholder) is set
            self.adjustSize()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Club Details
        self.le_name = QLineEdit(self.club.name)
        self.le_street = QLineEdit(self.club.street)
        self.le_city = QLineEdit(self.club.city)
        self.le_zip_code = QLineEdit(self.club.zip_code)
        
        self.cb_country = QComboBox()
        countries_data = utils.get_world_countries() # Loads countries according to the preferred language
        for country_name, country_code in countries_data:
            self.cb_country.addItem(country_name, country_code)
        
        country_to_select = self.club.country if self.club.country else utils.get_preferred_country_code()
        idx = self.cb_country.findData(country_to_select)
        self.cb_country.setCurrentIndex(idx if idx >=0 else 0)

        self.de_foundation_date = QDateEdit()
        self.de_foundation_date.setCalendarPopup(True)
        date_val = self.club.foundation_date
        if date_val:
            if isinstance(date_val, str):
                qdate = QDate.fromString(date_val, "yyyy-MM-dd")
            else:
                qdate = QDate(date_val.year, date_val.month, date_val.day)
            self.de_foundation_date.setDate(qdate)
        else:
            self.de_foundation_date.setDate(QDate.currentDate())
        self.le_phone = QLineEdit(self.club.phone)
        self.le_email = QLineEdit(self.club.email)

        self.cb_president = QComboBox()
        self.cb_president.addItem("", None)
        memberships = db.db_manager.fetch_memberships_by_club(club_id=self.club.club_id) if self.club and self.club.club_id else []
        members = db.db_manager.fetch_members(self.club.club_id) if self.club else []
        membership_ids = {m.member_id for m in memberships}
        self.members = [member for member in members if member.member_id in membership_ids]
        for m in self.members:
            full_name = f"{m.first_name} {m.last_name}"
            self.cb_president.addItem(full_name, m.member_id)
        if self.club.president_id:
            index = self.cb_president.findData(self.club.president_id)
            if index >= 0:
                self.cb_president.setCurrentIndex(index)

        form_layout.addRow(self.tr("Club Name:"), self.le_name)
        form_layout.addRow(self.tr("Street:"), self.le_street)
        form_layout.addRow(self.tr("City:"), self.le_city)
        form_layout.addRow(self.tr("ZIP Code:"), self.le_zip_code)
        form_layout.addRow(self.tr("Country:"), self.cb_country)
        form_layout.addRow(self.tr("Foundation Date:"), self.de_foundation_date)
        form_layout.addRow(self.tr("Phone:"), self.le_phone)
        form_layout.addRow(self.tr("Email:"), self.le_email)
        form_layout.addRow(self.tr("Club President:"), self.cb_president)

        # Logo Section
        self.lbl_logo_preview = QLabel() # Initial text/size set by load_club_logo_preview
        self.lbl_logo_preview.setAlignment(Qt.AlignCenter)
        self.lbl_logo_preview.setMinimumSize(100,100) # Minimum size for the placeholder text
        self.lbl_logo_preview.setStyleSheet("border: 1px solid #B0B0B0; background-color: #FFFFFF;")
        self.lbl_logo_preview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        form_layout.addRow(self.tr("Logo:"), self.lbl_logo_preview)

        logo_buttons_layout = QHBoxLayout()
        self.btn_upload_logo = QPushButton(self.tr("Upload New Logo"))
        self.btn_upload_logo.clicked.connect(self.upload_logo_action)
        logo_buttons_layout.addWidget(self.btn_upload_logo)
        
        logo_buttons_layout.addStretch() # Optional: to push buttons to one side

        # Add the QHBoxLayout containing the logo buttons to the form layout
        # The empty string for the label part of addRow means the buttons will span the field column
        form_layout.addRow("", logo_buttons_layout)
        
        layout.addLayout(form_layout)

        self.btn_edit = QPushButton(self.tr("Edit"))
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        self.btn_save = QPushButton(self.tr("Save"))
        self.btn_save.clicked.connect(self.save_changes)
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.clicked.connect(self.cancel_changes)

        if self.is_new:
            self.btn_edit.setVisible(False)
            self.btn_save.setVisible(True)
            self.btn_cancel.setVisible(True)
        else:
            self.btn_edit.setVisible(True)
            self.btn_save.setVisible(False)
            self.btn_cancel.setVisible(False)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        if not self.is_new:
            self.lock_fields()
        else:
            self.unlock_fields()

    def upload_logo_action(self):
        # This method handles uploading a NEW logo from local disk
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Logo Image"), "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        )
        if file_path:
            self.selected_logo_path = file_path
            new_pixmap = QPixmap(file_path)
            if not new_pixmap.isNull():
                # Scale the pixmap for preview, maintaining aspect ratio
                scaled_pixmap = new_pixmap.scaled(MAX_LOGO_PREVIEW_DIMENSION, MAX_LOGO_PREVIEW_DIMENSION, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_pixmap = scaled_pixmap # This is what's displayed
                self.lbl_logo_preview.setPixmap(self.logo_pixmap)
                self.lbl_logo_preview.setFixedSize(self.logo_pixmap.size()) # Label takes size of scaled pixmap
                self.lbl_logo_preview.setText("") # Clear text
                show_info_message(self.tr("New logo selected for preview."))
            else:
                self.selected_logo_path = None # Failed to load
                show_warning_message(self.tr("Could not load image."))
                self.lbl_logo_preview.setText(self.tr("Error loading image"))
                self.lbl_logo_preview.setPixmap(QPixmap()) # Clear pixmap
                self.lbl_logo_preview.setFixedSize(MAX_LOGO_PREVIEW_DIMENSION, 100) # Placeholder size
                self.lbl_logo_preview.setAlignment(Qt.AlignCenter)

            self.adjustSize()

    def load_club_logo_preview(self):
        self.logo_pixmap = None 
        self.lbl_logo_preview.setPixmap(QPixmap()) # Clear previous
        if self.club and self.club.logo_url:
            self.lbl_logo_preview.setText(self.tr("Loading logo..."))
            # Load image, scaled to fit within MAX_LOGO_PREVIEW_DIMENSION
            pixmap = load_image_from_url(self.club.logo_url, max_size=(MAX_LOGO_PREVIEW_DIMENSION, MAX_LOGO_PREVIEW_DIMENSION))
            if pixmap:
                self.logo_pixmap = pixmap
                self.lbl_logo_preview.setPixmap(self.logo_pixmap)
                self.lbl_logo_preview.setFixedSize(self.logo_pixmap.size()) # Label takes size of scaled pixmap
                self.lbl_logo_preview.setText("") # Clear text
            else:
                self.lbl_logo_preview.setText(self.tr("Logo not found"))
                self.lbl_logo_preview.setFixedSize(MAX_LOGO_PREVIEW_DIMENSION, 100) # Placeholder size
                self.lbl_logo_preview.setAlignment(Qt.AlignCenter)
        else:
            self.lbl_logo_preview.setText(self.tr("No logo"))
            self.lbl_logo_preview.setFixedSize(MAX_LOGO_PREVIEW_DIMENSION, 100) # Placeholder size
            self.lbl_logo_preview.setAlignment(Qt.AlignCenter)
        self.adjustSize()

    def lock_fields(self):
        self.le_name.setReadOnly(True)
        self.le_name.setStyleSheet("background-color: #E8E8E8;")
        self.le_street.setReadOnly(True)
        self.le_street.setStyleSheet("background-color: #E8E8E8;")
        self.le_city.setReadOnly(True)
        self.le_city.setStyleSheet("background-color: #E8E8E8;")
        self.le_zip_code.setReadOnly(True)
        self.le_zip_code.setStyleSheet("background-color: #E8E8E8;")
        self.cb_country.setEnabled(False)
        self.cb_country.setStyleSheet("background-color: #E8E8E8;")
        self.de_foundation_date.setReadOnly(True)
        self.de_foundation_date.setStyleSheet("background-color: #E8E8E8;")
        self.le_phone.setReadOnly(True)
        self.le_phone.setStyleSheet("background-color: #E8E8E8;")
        self.le_email.setReadOnly(True)
        self.le_email.setStyleSheet("background-color: #E8E8E8;")
        self.cb_president.setEnabled(False)
        self.btn_upload_logo.setEnabled(False)
        self.btn_edit.setVisible(True)
        self.btn_save.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.edit_mode = False

    def unlock_fields(self):
        self.le_name.setReadOnly(False)
        self.le_name.setStyleSheet("background-color: #E8D888;")
        self.le_street.setReadOnly(False)
        self.le_street.setStyleSheet("")
        self.le_city.setReadOnly(False)
        self.le_city.setStyleSheet("background-color: #E8D888;")
        self.le_zip_code.setReadOnly(False)
        self.le_zip_code.setStyleSheet("background-color: #E8D888;")
        self.cb_country.setEnabled(True)
        self.cb_country.setStyleSheet("") # Alebo iná farba pre editáciu
        self.de_foundation_date.setReadOnly(False)
        self.de_foundation_date.setStyleSheet("background-color: #E8D888;")
        self.le_phone.setReadOnly(False)
        self.le_phone.setStyleSheet("")
        self.le_email.setReadOnly(False)
        self.le_email.setStyleSheet("background-color: #E8D888;")
        self.cb_president.setEnabled(True)
        self.btn_upload_logo.setEnabled(True)
        self.edit_mode = True

    def toggle_edit_mode(self):
        if not self.edit_mode:
            self.unlock_fields()
            self.btn_edit.setVisible(False)
            self.btn_save.setVisible(True)
            self.btn_cancel.setVisible(True)
        else:
            self.cancel_changes()

    def save_changes(self):
        if not self.le_name.text().strip():
            show_warning_message(self.tr("Please fill in the club name."))
            return
        if not self.le_street.text().strip():
            show_warning_message(self.tr("Please fill in the street."))
            return
        if not self.le_city.text().strip():
            show_warning_message(self.tr("Please fill in the city."))
            return
        if not self.le_zip_code.text().strip():
            show_warning_message(self.tr("Please fill in the ZIP code."))
            return
        if not self.cb_country.currentData(): # Check if a valid country (code) is selected
            show_warning_message(self.tr("Please select a country."))
            return
        if not self.le_email.text().strip():
            show_warning_message(self.tr("Please fill in the email."))
            return
        
        date_val = self.de_foundation_date.date().toString("yyyy-MM-dd")
        self.club.name = self.le_name.text()
        self.club.street = self.le_street.text()
        self.club.city = self.le_city.text()
        self.club.zip_code = self.le_zip_code.text()
        self.club.country = self.cb_country.currentData() # Uložíme kód krajiny
        self.club.foundation_date = date_val
        self.club.phone = self.le_phone.text()
        self.club.email = self.le_email.text()
        self.club.president_id = self.cb_president.currentData() # This can be None if the empty item is selected

        if self.club.president_id is not None:
            # Try to find the selected president in the list of club members (self.members)
            president_name_found = False
            for member_obj in self.members: # self.members contains Member objects
                if member_obj.member_id == self.club.president_id:
                    self.club.president_name = f"{member_obj.first_name} {member_obj.last_name}"
                    president_name_found = True
                    break
            if not president_name_found:
                # This case implies president_id was set, but the corresponding member
                # was not found in self.members. This is unexpected if cb_president
                # is populated correctly from self.members.
                self.club.president_name = None # Fallback
                print(f"Warning: President with ID {self.club.president_id} not found in self.members for club {self.club.name}. President name set to None.")
        else:
            # No president was selected (president_id is None)
            self.club.president_name = None


        # Handle logo upload
        if self.selected_logo_path:
            try:
                pixmap_to_upload = QPixmap(self.selected_logo_path)
                if pixmap_to_upload.isNull():
                    show_warning_message(self.tr("Could not load the selected logo image."))
                    self.selected_logo_path = None # Reset
                    # If we wanted to return the original logo, the logic would be here
                    # self.club.logo_url = self.original_club_data.logo_url
                    return # Ukončíme, ak sa logo nenačítalo

                MAX_UPLOAD_WIDTH = 500
                MAX_UPLOAD_HEIGHT = 150

                if pixmap_to_upload.width() > MAX_UPLOAD_WIDTH or pixmap_to_upload.height() > MAX_UPLOAD_HEIGHT:
                    pixmap_to_upload = pixmap_to_upload.scaled(MAX_UPLOAD_WIDTH, MAX_UPLOAD_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                buffer = QBuffer()
                buffer.open(QIODevice.WriteOnly)

                original_file_name = os.path.basename(self.selected_logo_path)
                file_extension = os.path.splitext(original_file_name)[1].lower()

                qt_save_format = "PNG"
                gcs_content_type = "image/png"
                final_blob_extension = ".png"

                if file_extension in ['.jpg', '.jpeg']:
                    qt_save_format = "JPG"
                    gcs_content_type = "image/jpeg"
                    final_blob_extension = ".jpg"
                
                if not pixmap_to_upload.save(buffer, qt_save_format):
                    show_warning_message(self.tr("Could not convert logo to the target format."))
                    self.selected_logo_path = None
                    buffer.close()
                    return
                
                logo_data = buffer.data().data() # Get bytes from QBuffer
                buffer.close()

                old_logo_url_to_delete = None
                if self.original_club_data and self.original_club_data.logo_url:
                    bucket_name = secret_manager.get_secret("bucket_name")
                    if self.original_club_data.logo_url.startswith(f"https://storage.googleapis.com/{bucket_name}/club_logos/"):
                        old_logo_url_to_delete = self.original_club_data.logo_url

                new_logo_blob_name = f"club_logos/{uuid.uuid4().hex}{final_blob_extension}"
                new_logo_url = upload_to_bucket(new_logo_blob_name, logo_data, gcs_content_type)

                if new_logo_url:
                    self.club.logo_url = new_logo_url
                    if old_logo_url_to_delete and old_logo_url_to_delete != new_logo_url:
                        delete_object_from_bucket_by_url(old_logo_url_to_delete)
                else:
                    show_warning_message(self.tr("Could not upload the new logo. The previous logo (if any) will be kept or no logo will be set if this is a new club."))
                    self.club.logo_url = self.original_club_data.logo_url # Revert
                self.selected_logo_path = None # Reset
            except Exception as e:
                show_error_message(self.tr("Failed to process logo: ") + str(e))
                self.club.logo_url = self.original_club_data.logo_url # Revert for safety
                self.selected_logo_path = None

        if self.is_new:
            new_id = db.db_manager.insert_club(self.club)
            if new_id:
                self.club.club_id = new_id # Update club object with new ID
                show_success_message(self.tr("New club has been created."))
                self.original_club_data = copy.copy(self.club) 
                self.is_new = False # No longer a new club
                self.lock_fields()
                self.accept()
            else:
                show_error_message(self.tr("Failed to create new club in database."))
                # Do not close dialog, allow user to retry or cancel
        else:
            db.db_manager.update_club(self.club)
            show_success_message(self.tr("Club data has been updated."))
            self.original_club_data = copy.copy(self.club) # Update original_club_data
            self.lock_fields()
            self.accept() # Signal acceptance and allow dialog to close

    def cancel_changes(self):
        if self.is_new:
            self.reject()
            return
        self.le_name.setText(self.original_club_data.name)
        self.le_street.setText(self.original_club_data.street)
        self.le_city.setText(self.original_club_data.city)
        self.le_zip_code.setText(self.original_club_data.zip_code)
        # Setting the ComboBox for the country
        idx = self.cb_country.findData(self.original_club_data.country)
        self.cb_country.setCurrentIndex(idx if idx >=0 else 0)
        date_val = self.original_club_data.foundation_date
        self.de_foundation_date.setDate(QDate.fromString(str(date_val), "yyyy-MM-dd") if date_val else None)
        self.le_phone.setText(self.original_club_data.phone)
        self.le_email.setText(self.original_club_data.email)
        if self.original_club_data.president_id:
            index = self.cb_president.findData(self.original_club_data.president_id)
            if index >= 0:
                self.cb_president.setCurrentIndex(index)
        else:
            self.cb_president.setCurrentIndex(0)
        
        self.selected_logo_path = None # Clear any pending new logo
        self.club.logo_url = self.original_club_data.logo_url
        self.load_club_logo_preview()
        # self.adjustSize() # Called by load_club_logo_previe
        self.lock_fields()
