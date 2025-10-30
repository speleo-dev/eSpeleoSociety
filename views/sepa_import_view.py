# views/sepa_import_view.py
from datetime import datetime
from PyQt5.QtWidgets import ( 
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QColor
from utils import parse_camt053, get_table_header_stylesheet, get_iban, get_membership_fee_normal, get_membership_fee_discounted, show_info_message, show_warning_message, show_error_message, show_success_message, encrypt_fee_reference
import db # Potrebujeme pre prístup k databáze


class SepaImportView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel(self.tr("Import SEPA Statement"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.import_button = QPushButton(self.tr("Select XML File"))
        self.import_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.import_button)
        
        # Tabuľka na zobrazenie výsledkov
        self.table = QTableWidget()
        self.table.setColumnCount(5) # ECP Hash, Name / Payer IBAN, Amount, Currency, Payment Date
        self.table.setHorizontalHeaderLabels([
            self.tr("ECP Hash"), self.tr("Name / Payer IBAN"),
            self.tr("Amount"), self.tr("Currency"), self.tr("Payment Date")
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ECP Hash
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Name / Payer IBAN
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Amount
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Currency
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Payment Date
        header.setStretchLastSection(False)
        header.setStyleSheet(get_table_header_stylesheet())
        layout.addWidget(self.table)
        
        # Tlačidlo pre uloženie platieb
        self.save_button = QPushButton(self.tr("Save Payments"))
        self.save_button.clicked.connect(self.save_payments)
        layout.addWidget(self.save_button)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select XML File"), "", self.tr("XML Files (*.xml)"))
        if file_path:
            self.start_import(file_path)

    def start_import(self, file_path: str):
        self.processed_transactions = [] # Inicializujeme zoznam transakcií
        parsed_data = parse_camt053(file_path)
        self.processed_transactions = self.process_transactions(parsed_data)

        if parsed_data.get('error'):
            show_error_message(self.tr(f"Error parsing XML: {parsed_data['error']}"))
            self.table.setRowCount(0)
            return

        config_iban = get_iban()
        if not config_iban:
            show_warning_message(self.tr("IBAN is not configured in application settings. Cannot verify statement account."))
            # Pokračujeme v importe, ale bez overenia IBANu výpisu
        
        statement_iban = parsed_data.get('statement_iban')
        if config_iban and statement_iban and config_iban.replace(" ", "") != statement_iban.replace(" ", ""):
            show_warning_message(self.tr(f"Statement IBAN ({statement_iban}) does not match configured IBAN ({config_iban})."))
            # Rozhodnúť sa, či pokračovať alebo nie. Pre teraz pokračujeme.

        self.display_results(self.processed_transactions)
        if self.processed_transactions:
            show_success_message(self.tr("SEPA file processed. You can now save valid payments."))

    def process_transactions(self, parsed_data: dict) -> list:
        normal_fee = get_membership_fee_normal()
        discounted_fee = get_membership_fee_discounted()
        processed_transactions = []
        for tx_data in parsed_data.get('transactions', []):
            processed_tx = {
                'ecp_hash_display': tx_data.get('ecp_hash_candidate', self.tr("N/A")),
                'name_or_iban': "",
                'amount': 0.0,
                'currency': tx_data.get('currency', ''),
                'payment_date': tx_data.get('transaction_date', self.tr('N/A')),
                'bg_color': QColor("white"), 
                'text_color': QColor("black") 
            }
            try:
                tx_amount = float(tx_data.get('amount', 0))
                processed_tx['amount'] = tx_amount
            except ValueError:
                processed_tx['bg_color'] = QColor("lightgray") # Sivé pozadie pre nevalidnú sumu
                processed_tx['name_or_iban'] = self.tr("Invalid amount in transaction")
                processed_transactions.append(processed_tx)
                continue

            ecp_hash = tx_data.get('ecp_hash_candidate')
            member = None
            ecp_record = None

            if ecp_hash:
                ecp_record = db.db_manager.fetch_ecp(ecp_hash)
                if ecp_record:
                    member = db.db_manager.fetch_member_by_id(ecp_record.member_id)

            if member and ecp_record:
                processed_tx['name_or_iban'] = f"{member.first_name} {member.last_name}"
                expected_fee = discounted_fee if member.discounted_membership else normal_fee

                if ecp_record.is_ecp_active:
                    if abs(tx_amount - expected_fee) < 0.001: # Porovnanie floatov
                        processed_tx['bg_color'] = QColor("lightgreen")
                    elif tx_amount < expected_fee:
                        processed_tx['bg_color'] = QColor("salmon") # Svetlo červená
                    else: # tx_amount > expected_fee
                        processed_tx['bg_color'] = QColor("lightblue")
                else: # ecp_record not active
                    if abs(tx_amount - normal_fee) < 0.001 or abs(tx_amount - discounted_fee) < 0.001:
                        processed_tx['bg_color'] = QColor("yellow")
                    else: # Neaktívny ECP, nesprávna suma
                        processed_tx['bg_color'] = QColor("lightgray") 
            else: # ecp_hash chýba, alebo ecp_record nenájdený, alebo člen nenájdený
                processed_tx['bg_color'] = QColor("lightgray")
                processed_tx['name_or_iban'] = tx_data.get('debtor_account_iban', self.tr('N/A'))
                if abs(tx_amount - normal_fee) < 0.001 or abs(tx_amount - discounted_fee) < 0.001:
                    processed_tx['text_color'] = QColor("darkGreen")
                else:
                    processed_tx['text_color'] = QColor("red")
            
            processed_transactions.append(processed_tx)

    def save_payments(self):
        if not hasattr(self, 'processed_transactions') or not self.processed_transactions:
            show_warning_message(self.tr("No transactions to save. Please import a SEPA file first."))
            return

        saved_count = 0
        for tx in self.processed_transactions:
            if tx['bg_color'] == QColor("lightgreen") and tx['ecp_hash_display'] != self.tr("N/A"):  # Len úspešné platby
                ecp_hash = tx['ecp_hash_display']
                member = db.db_manager.fetch_member_by_hash(ecp_hash)
                if member:
                    encrypted_ref = encrypt_fee_reference(ecp_hash, datetime.datetime.now().year)
                    if encrypted_ref:
                        db.db_manager.insert_fee_record(member.member_id, datetime.datetime.now().year, encrypted_ref)
                        saved_count += 1
        
        if saved_count > 0:
            show_success_message(self.tr(f"Successfully saved {saved_count} payments."))
        else:
            show_info_message(self.tr("No valid payments found to save."))
        
    def display_results(self, processed_transactions: list):
        self.table.setRowCount(0) 
        if not processed_transactions:
            return
        self.table.setRowCount(len(processed_transactions))

        for row_idx, tx_info in enumerate(processed_transactions):
            ecp_item = QTableWidgetItem(tx_info['ecp_hash_display'])
            name_iban_item = QTableWidgetItem(tx_info['name_or_iban'])
            amount_item = QTableWidgetItem(f"{tx_info['amount']:.2f}") # Formátovanie na 2 desatinné miesta
            currency_item = QTableWidgetItem(tx_info['currency'])
            date_item = QTableWidgetItem(tx_info['payment_date'])

            items = [ecp_item, name_iban_item, amount_item, currency_item, date_item]

            for col_idx, item in enumerate(items):
                item.setBackground(tx_info['bg_color'])
                item.setForeground(tx_info['text_color'])
                self.table.setItem(row_idx, col_idx, item)
        
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def showEvent(self, event):
        """Called when the widget is shown."""
        super().showEvent(event)
        # Prípadne vyčistiť tabuľku pri každom zobrazení view
        # self.table.setRowCount(0) 
