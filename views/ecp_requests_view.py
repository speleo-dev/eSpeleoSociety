from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QDialog, QHBoxLayout
from PyQt5.QtCore import Qt
from table_layout import ColumnSpec
from ui_table import SortableItem, create_columns_button, install_table_features
from utils import get_table_header_stylesheet, show_success_message # Pridaný import
import db

class ECPRequestsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        title_row = QHBoxLayout()
        header = QLabel(self.tr("eCP Requests"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        title_row.addWidget(header)
        title_row.addStretch()
        layout.addLayout(title_row)

        self.table = QTableWidget()
        self.table_controller = install_table_features(
            self.table,
            "ecp_requests",
            [
                ColumnSpec("applicant", self.tr("Applicant"), width=280, essential=True, stretch=True),
                ColumnSpec("request_date", self.tr("Request Date"), width=130),
                ColumnSpec("status", self.tr("Request Status"), width=130),
                ColumnSpec("process", self.tr("Process"), width=100, essential=True),
            ],
            parent=self,
        )
        title_row.addWidget(create_columns_button(self.table_controller, self))
        self.table.horizontalHeader().setStyleSheet(get_table_header_stylesheet())
        layout.addWidget(self.table)

    def refresh_data(self):
        requests = db.db_manager.fetch_ecp_requests()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(requests))
        for row, req in enumerate(requests):
            member = db.db_manager.fetch_member_by_id(req.member_id) # Use translated attribute
            applicant_name_str = "N/A"
            if member:
                applicant_name_str = " ".join(filter(None, [member.title_prefix, member.first_name, member.last_name, member.title_suffix]))
            self.table.setItem(row, 0, SortableItem(applicant_name_str))
            date_text_str = str(req.request_date) # Use translated attribute
            self.table.setItem(row, 1, SortableItem(date_text_str))
            self.table.setItem(row, 2, SortableItem(req.status)) # Use translated attribute
            if req.status.lower() == "pending": # Use translated attribute
                self.table.setItem(row, 3, SortableItem(""))
                btn_process = QPushButton(self.tr("Process"))
                # Použite default parameter pre zachytenie aktuálnej hodnoty req
                btn_process.clicked.connect(lambda checked, r=req: self.handle_request(r))
                self.table.setCellWidget(row, 3, btn_process)
            else:
                self.table.setCellWidget(row, 3, None)
                self.table.setItem(row, 3, SortableItem("-"))
        self.table.setSortingEnabled(True)

    def handle_request(self, req):
        from dialogs.ecp_approval_dialog import ECPApprovalDialog
        dlg = ECPApprovalDialog(req, self)
        if dlg.exec_() == QDialog.Accepted:
            show_success_message(self.tr("The request has been processed."))
            self.refresh_data()
