# dialogs/ecp_issuance_dialog.py
import os, hashlib, uuid, secrets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QHBoxLayout, 
    QListWidget, QInputDialog, QMessageBox, QCheckBox
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QIODevice, QBuffer, Qt # Qt added to imports from QtCore
from model import Ecp, Member # Import Member model
import db
from utils import get_icon, upload_photo_to_bucket, create_check_hash, send_to_google_wallet, show_error_message, show_warning_message, show_success_message
import utils # Pre prístup k utils.create_check_hash

class ECPIssuanceDialog(QDialog):
    def __init__(self, member: Member, parent=None):
        super().__init__(parent)
        self.member = member
        self.is_issuable = True # Predpokladáme, že je možné vydať, kým sa neskontrolujú podmienky

        if not self.member or not self.member.email:
            QMessageBox.information(self, self.tr("Error"),
                                      self.tr("Member does not have an email address, eCP or eCard cannot be issued."))
            self.reject()
            self.is_issuable = False # Nastavíme flag, aby sa UI neinicializovalo zbytočne
            return 
        
        self.setWindowTitle(self.tr("Issue eCP"))
        self.resize(640, 480)

        self.setWindowIcon(get_icon("logo.ico"))

        layout = QVBoxLayout(self)
        # Assuming translated attributes for member
        member_full_name = f"{self.member.title_prefix or ''} {self.member.first_name or ''} {self.member.last_name or ''} {self.member.title_suffix or ''}".strip()
        header_label = QLabel(member_full_name)
        header_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(header_label)
        email_label = QLabel(f"{self.tr('Email')}: {member.email}")
        layout.addWidget(email_label)
        self.photo_label = QLabel(self.tr("Photo (fit to 225x300px frame):"))
        layout.addWidget(self.photo_label)

        self.photo_viewer = QLabel() # Replaced PhotoViewer with QLabel
        self.photo_viewer.setFixedSize(225, 300)
        self.photo_viewer.setStyleSheet("border: 1px solid black;")
        self.photo_viewer.setAlignment(Qt.AlignCenter) # Centering the image in QLabel
        self.photo_viewer.setScaledContents(True) # To scale the image to QLabel size
        self.photo_viewer.setPixmap(QPixmap()) # Initialize with an empty pixmap to prevent NoneType error
        layout.addWidget(self.photo_viewer)

        # Checkboxy pre eCP options
        self.chk_gdpr_consent = QCheckBox(self.tr("GDPR Consent for eCP"))
        self.chk_notifications = QCheckBox(self.tr("Enable Notifications"))
        
        checkbox_layout = QVBoxLayout()
        checkbox_layout.addWidget(self.chk_gdpr_consent)
        checkbox_layout.addWidget(self.chk_notifications)
        layout.addLayout(checkbox_layout)

        btn_load_photo = QPushButton(self.tr("Load Photo"))
        btn_load_photo.clicked.connect(self.load_photo)
        layout.addWidget(btn_load_photo)
        # Prepojíme signály checkboxov a načítania fotky s aktualizáciou stavu tlačidla
        self.chk_gdpr_consent.stateChanged.connect(self.update_issue_button_state)
        
        cert_label = QLabel(self.tr("Certificates:"))
        layout.addWidget(cert_label)
        cert_layout = QHBoxLayout()
        self.cert_list = QListWidget()
        cert_layout.addWidget(self.cert_list)
        btns_layout = QVBoxLayout()
        self.btn_add_cert = QPushButton(self.tr("➕ Add Skill/Certificate"))
        self.btn_add_cert.clicked.connect(self.add_certificate)
        btns_layout.addWidget(self.btn_add_cert)
        self.btn_remove_cert = QPushButton(self.tr("➖ Remove Certificate"))
        self.btn_remove_cert.clicked.connect(self.remove_certificate)
        btns_layout.addWidget(self.btn_remove_cert)
        cert_layout.addLayout(btns_layout)
        layout.addLayout(cert_layout)

        btn_layout = QHBoxLayout()
        btn_issue = QPushButton(self.tr("Issue eCP"))
        btn_issue.clicked.connect(self.issue_ecp)
        self.btn_issue = btn_issue # Uchováme referenciu na tlačidlo
        btn_layout.addWidget(btn_issue)
        btn_cancel = QPushButton(self.tr("Cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.update_issue_button_state() # Nastavíme počiatočný stav tlačidla

    def load_photo(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select Photo"), "", self.tr("Images (*.png *.jpg *.jpeg)"))
        if filename:
            pixmap = QPixmap(filename)
            if not pixmap.isNull():
                # QLabel uses setPixmap, and we can scale it if necessary,
                # but setScaledContents(True) should handle it automatically.
                self.photo_viewer.setPixmap(pixmap)
        self.update_issue_button_state() # Aktualizujeme stav tlačidla po načítaní fotky

    def update_issue_button_state(self):
        photo_loaded = not self.photo_viewer.pixmap().isNull()
        gdpr_consented = self.chk_gdpr_consent.isChecked()
        self.btn_issue.setEnabled(photo_loaded and gdpr_consented)

    def add_certificate(self):
        cert, ok = QInputDialog.getText(self, self.tr("Certificate"), self.tr("Enter certificate (name, year):"))
        if ok and cert:
            if self.cert_list.count() < 5:
                self.cert_list.addItem(cert)
            else:
                QMessageBox.warning(self, self.tr("Limit Reached"), self.tr("Maximum of 5 certificates allowed."))

    def remove_certificate(self):
        current_item = self.cert_list.currentItem()
        if not current_item:
            QMessageBox.information(self, self.tr("Info"), self.tr("No certificate selected for removal."))
            return
        row = self.cert_list.row(current_item)
        self.cert_list.takeItem(row)

    def issue_ecp(self):
        if not self.member or not self.member.member_id:
             show_error_message(self.tr("Cannot issue eCP: Member data is missing."))
             return

        # Get pixmap directly from QLabel
        current_pixmap = self.photo_viewer.pixmap()
        if not current_pixmap or current_pixmap.isNull():
            show_warning_message(self.tr("No photo loaded."))
            return
        visible_pixmap = self.photo_viewer.grab() # QLabel.grab()
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        visible_pixmap.save(buffer, "PNG")
        image_data = buffer.data()
        buffer.close()
        photo_hash_val = hashlib.sha256(uuid.uuid4().bytes).hexdigest() # Renamed for clarity
        upload_photo_to_bucket(photo_hash_val, image_data)
        self.member.ecp_hash = secrets.token_hex(32) # Assuming translated attribute
        check_hash_val = utils.create_check_hash()
        # Assuming Ecp constructor uses translated attribute names
        ecp_obj = Ecp(ecp_hash=self.member.ecp_hash, gdpr_consent=True, notifications_enabled=True,
                      photo_hash=photo_hash_val, is_ecp_active=True, 
                      check_hash=check_hash_val, member_id=self.member.member_id)
        db.db_manager.insert_ecp(ecp_obj) # Example: inserting ECP record
        db.db_manager.update_member_ecp_hash(self.member.member_id, self.member.ecp_hash)
        QMessageBox.information(self, self.tr("eCP Issued"), self.tr("eCP has been issued and photo saved."))
        self.accept()
