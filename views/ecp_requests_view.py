from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QDialog
from PyQt5.QtCore import Qt
from utils import get_table_header_stylesheet, show_success_message # Pridaný import
import db

class ECPRequestsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("eCP Requests"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([self.tr("Applicant"), self.tr("Request Date"), self.tr("Request Status"), self.tr("Process")])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) # Applicant
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Request Date
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Request Status
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Process
        header.setStretchLastSection(True)
        header.setStyleSheet(get_table_header_stylesheet())
        layout.addWidget(self.table)

    def refresh_data(self):
        requests = db.db_manager.fetch_ecp_requests()
        self.table.setRowCount(len(requests))
        for row, req in enumerate(requests):
            member = db.db_manager.fetch_member_by_id(req.member_id) # Use translated attribute
            applicant_name_str = "N/A"
            if member:
                applicant_name_str = " ".join(filter(None, [member.title_prefix, member.first_name, member.last_name, member.title_suffix]))
            self.table.setItem(row, 0, QTableWidgetItem(applicant_name_str))
            date_text_str = str(req.request_date) # Use translated attribute
            self.table.setItem(row, 1, QTableWidgetItem(date_text_str))
            self.table.setItem(row, 2, QTableWidgetItem(req.status)) # Use translated attribute
            if req.status.lower() == "pending": # Use translated attribute
                btn_process = QPushButton(self.tr("Process"))
                # Použite default parameter pre zachytenie aktuálnej hodnoty req
                btn_process.clicked.connect(lambda checked, r=req: self.handle_request(r))
                self.table.setCellWidget(row, 3, btn_process)
            else:
                self.table.setItem(row, 3, QTableWidgetItem("-"))

    def handle_request(self, req):
        from dialogs.ecp_approval_dialog import ECPApprovalDialog
        dlg = ECPApprovalDialog(req, self)
        if dlg.exec_() == QDialog.Accepted:
            show_success_message(self.tr("The request has been processed."))
            self.refresh_data()
