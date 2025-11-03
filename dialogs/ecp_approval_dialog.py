# dialogs/ecp_approval_dialog.py
import os, secrets # Added secrets import
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from model import EcpRequest
import db
from utils import get_icon, load_image_from_url, send_to_google_wallet, delete_photo_from_bucket, show_success_message, show_error_message
from config import secret_manager # For access to bucket name

class ECPApprovalDialog(QDialog):
    def __init__(self, req_details, parent=None):
        super().__init__(parent)
        self.req_details = req_details
        self.member = db.db_manager.fetch_member_by_id(req_details.member_id)
        # We load the ecp_record using the photo_hash from the request
        self.ecp_record = db.db_manager.fetch_ecp_record_by_photo_hash(req_details.photo_hash) 

        self.setWindowTitle(self.tr("eCP Request Approval"))
        self.setWindowIcon(get_icon("logo.ico"))

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.info_label = QLabel("")
        self.layout.addWidget(self.info_label)
        # Assuming translated attributes for member and req_details
        applicant_name = f"{self.member.title_prefix or ''} {self.member.first_name or ''} {self.member.last_name or ''} {self.member.title_suffix or ''}".strip()
        request_date_str = self.req_details.request_date.strftime("%Y-%m-%d") if self.req_details.request_date else self.tr("N/A")
        info_text = (
            f"{self.tr('Applicant')}: {applicant_name}\n"
            f"{self.tr('Request Date')}: {request_date_str}\n"
        )
        self.info_label.setText(info_text)

        self.image_label = QLabel("")
        self.layout.addWidget(self.image_label)
        
        if self.ecp_record and self.ecp_record.photo_hash:
            bucket_name = secret_manager.get_secret("bucket_name")
            photo_url = f"https://storage.googleapis.com/{bucket_name}/{self.ecp_record.photo_hash}.png"
            img = load_image_from_url(photo_url)
            if img:
                self.image_label.setPixmap(img)
            else:
                self.image_label.setText(self.tr("Photo not available or failed to load."))
        else:
            self.image_label.setText(self.tr("Photo information missing in eCP record."))

        buttons_layout = QHBoxLayout()
        self.btn_approve = QPushButton(self.tr("Approve"))
        self.btn_approve.clicked.connect(self.approve)
        buttons_layout.addWidget(self.btn_approve)
        self.btn_reject = QPushButton(self.tr("Reject"))
        self.btn_reject.clicked.connect(self.reject_request)
        buttons_layout.addWidget(self.btn_reject)
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(buttons_layout)

    def approve(self):
        if not self.ecp_record or not self.ecp_record.photo_hash:
            show_error_message(self.tr("Cannot approve: eCP record or photo hash is missing."))
            return

        new_generated_ecp_hash = secrets.token_hex(32)

        db.db_manager.update_ecp_record_on_approval(self.ecp_record.photo_hash, new_generated_ecp_hash)
        db.db_manager.update_member_ecp_hash(self.member.member_id, new_generated_ecp_hash)
        db.db_manager.update_ecp_request_status(self.req_details.request_id, "approved")
        
        # The ecp_hash attribute in self.req_details is the photo_hash and should not be changed to the final ECP hash.
        # self.req_details.approved_ecp_hash = new_generated_ecp_hash # This attribute no longer exists in the EcpRequest model
        self.req_details.status = "approved"

        send_to_google_wallet(self.req_details) # Placeholder
        show_success_message(self.tr("The request has been approved."))
        self.accept() # Zatvorí dialóg

    def reject_request(self):
        if not self.ecp_record or not self.ecp_record.photo_hash:
            show_error_message(self.tr("Cannot reject: eCP record or photo hash is missing."))
            return

        db.db_manager.update_ecp_request_status(self.req_details.request_id, "rejected")
        db.db_manager.delete_ecp_record_by_photo_hash(self.ecp_record.photo_hash)
        delete_photo_from_bucket(self.ecp_record.photo_hash)
        
        # If the member previously had an ecp_hash that now becomes invalid by rejecting this request,
        # it might be appropriate to nullify it here. But if this is a new request, the member's ecp_hash should already be null.
        # To be safe, if the portal logic were different:
        # if self.member.ecp_hash == self.ecp_record.ecp_hash: # If ecp_hash was temporarily set
        #     db.db_manager.update_member_ecp_hash(self.member.member_id, None)

        show_success_message(self.tr("The request has been rejected."))
        self.accept() # Zatvorí dialóg
