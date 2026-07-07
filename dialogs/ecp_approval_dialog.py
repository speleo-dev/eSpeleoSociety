# dialogs/ecp_approval_dialog.py
import os, secrets # Added secrets import
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QBuffer, QIODevice
from model import EcpRequest
import db
from email_notifications import EmailNotificationError, send_ecp_issued_email
from ecp_issuance import EcpQrUploadError, EcpSigningConfigError, issue_and_upload_ecp_delivery_bundle
from utils import get_icon, load_image_from_url, send_to_google_wallet, delete_photo_from_bucket, upload_to_bucket, show_success_message, show_error_message
from config import secret_manager # For access to bucket name

class ECPApprovalDialog(QDialog):
    def __init__(self, req_details, parent=None):
        super().__init__(parent)
        self.req_details = req_details
        self.member = db.db_manager.fetch_member_by_id(req_details.member_id)
        self.ecp_record = None
        if getattr(req_details, "ecp_record_id", None) is not None:
            self.ecp_record = db.db_manager.fetch_ecp_record_by_id(req_details.ecp_record_id)
        if self.ecp_record is None and req_details.photo_hash:
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
        if not self.ecp_record or not self.ecp_record.ecp_id or not self.ecp_record.photo_hash:
            show_error_message(self.tr("Cannot approve: eCP record or photo hash is missing."))
            return

        new_generated_ecp_hash = secrets.token_hex(32)
        photo_url = None
        if self.ecp_record and self.ecp_record.photo_hash:
            bucket_name = secret_manager.get_secret("bucket_name")
            photo_url = f"https://storage.googleapis.com/{bucket_name}/{self.ecp_record.photo_hash}.png" if bucket_name else None
        portrait_image = None
        current_pixmap = self.image_label.pixmap()
        if current_pixmap and not current_pixmap.isNull():
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            current_pixmap.save(buffer, "PNG")
            portrait_image = bytes(buffer.data())
            buffer.close()
        try:
            primary_club = db.db_manager.fetch_club_by_id(self.member.primary_club_id) if self.member.primary_club_id else None
            delivery_bundle = issue_and_upload_ecp_delivery_bundle(
                member=self.member,
                club=primary_club,
                ecp_hash=new_generated_ecp_hash,
                get_secret=secret_manager.get_secret,
                upload_blob=upload_to_bucket,
                portrait_image=portrait_image,
                portrait_url=photo_url,
            )
        except (EcpSigningConfigError, EcpQrUploadError, ValueError, TypeError) as exc:
            show_error_message(self.tr(f"Cannot approve signed eCP QR: {exc}"))
            return

        db.db_manager.update_ecp_record_issuance(
            ecp_record_id=self.ecp_record.ecp_id,
            ecp_hash=new_generated_ecp_hash,
            qr_url=delivery_bundle.qr_url,
            qr_key_id=delivery_bundle.issued_qr.key_id,
            qr_payload=delivery_bundle.issued_qr.payload,
            qr_payload_hash=delivery_bundle.issued_qr.payload_hash,
            issued_at=delivery_bundle.issued_qr.issued_at,
            valid_until=delivery_bundle.issued_qr.valid_until,
            verification_url=delivery_bundle.verification_url,
            card_image_url=delivery_bundle.card_image_url,
            card_pdf_url=delivery_bundle.card_pdf_url,
            legal_document_url=delivery_bundle.legal_document_url,
        )
        db.db_manager.update_member_ecp_hash(self.member.member_id, new_generated_ecp_hash)
        db.db_manager.update_ecp_request_status(self.req_details.request_id, "approved")
        
        # The ecp_hash attribute in self.req_details is the photo_hash and should not be changed to the final ECP hash.
        # self.req_details.approved_ecp_hash = new_generated_ecp_hash # This attribute no longer exists in the EcpRequest model
        self.req_details.status = "approved"
        self.req_details.signed_qr_payload = delivery_bundle.issued_qr.payload
        self.req_details.signed_qr_data = delivery_bundle.issued_qr.qr_data
        self.req_details.signed_qr_url = delivery_bundle.qr_url

        send_to_google_wallet(self.req_details) # Placeholder
        email_warning = None
        try:
            send_ecp_issued_email(
                self.member,
                delivery_bundle.issued_qr,
                secret_manager.get_secret,
                verification_url=delivery_bundle.verification_url,
                card_image=delivery_bundle.card_image,
                card_pdf=delivery_bundle.card_pdf,
                card_image_url=delivery_bundle.card_image_url,
                card_pdf_url=delivery_bundle.card_pdf_url,
                legal_document_url=delivery_bundle.legal_document_url,
            )
        except EmailNotificationError as exc:
            email_warning = self.tr(f"The request was approved, but email notification failed: {exc}")
        if email_warning:
            QMessageBox.warning(self, self.tr("Email Notification Failed"), email_warning)
        else:
            show_success_message(self.tr("The request has been approved."))
        self.accept() # Zatvorí dialóg

    def reject_request(self):
        if not self.ecp_record or not self.ecp_record.photo_hash:
            show_error_message(self.tr("Cannot reject: eCP record or photo hash is missing."))
            return

        db.db_manager.update_ecp_request_status(self.req_details.request_id, "rejected")
        if self.ecp_record.ecp_id:
            db.db_manager.delete_ecp_record_by_id(self.ecp_record.ecp_id)
        else:
            db.db_manager.delete_ecp_record_by_photo_hash(self.ecp_record.photo_hash)
        delete_photo_from_bucket(self.ecp_record.photo_hash)
        
        # If the member previously had an ecp_hash that now becomes invalid by rejecting this request,
        # it might be appropriate to nullify it here. But if this is a new request, the member's ecp_hash should already be null.
        # To be safe, if the portal logic were different:
        # if self.member.ecp_hash == self.ecp_record.ecp_hash: # If ecp_hash was temporarily set
        #     db.db_manager.update_member_ecp_hash(self.member.member_id, None)

        show_success_message(self.tr("The request has been rejected."))
        self.accept() # Zatvorí dialóg
