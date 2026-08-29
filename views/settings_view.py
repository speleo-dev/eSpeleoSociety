# views/settings_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox, QPushButton,
    QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QFrame,
    QColorDialog, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor
from banking.payment_link_factory import get_available_generators
import utils
import os
import uuid


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
        self.generated_sticker_data = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        header = QLabel(self.tr("Application Settings"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        form_layout = QFormLayout()

        # Preferred country
        self.country_combo = QComboBox()
        form_layout.addRow(self.tr("Preferred Country:"), self.country_combo)

        # Preferred language / localization
        self.language_combo = QComboBox()
        supported_locales = utils.get_supported_locales_display()
        for code, display_name in supported_locales.items():
            self.language_combo.addItem(display_name, code)
        form_layout.addRow(self.tr("Preferred Language:"), self.language_combo)

        # Currency for membership fees
        self.currency_edit = QLineEdit()
        form_layout.addRow(self.tr("Membership Currency:"), self.currency_edit)

        # Normal membership fee amount
        self.fee_normal_spinbox = QDoubleSpinBox()
        self.fee_normal_spinbox.setDecimals(2)
        self.fee_normal_spinbox.setMinimum(0.00)
        self.fee_normal_spinbox.setMaximum(9999.99)
        form_layout.addRow(self.tr("Normal Membership Fee:"), self.fee_normal_spinbox)

        # Discounted membership fee amount
        self.fee_discounted_spinbox = QDoubleSpinBox()
        self.fee_discounted_spinbox.setDecimals(2)
        self.fee_discounted_spinbox.setMinimum(0.00)
        self.fee_discounted_spinbox.setMaximum(9999.99)
        form_layout.addRow(self.tr("Discounted Membership Fee:"), self.fee_discounted_spinbox)

        # Membership validity date (month and day)
        self.valid_until_month_spinbox = QSpinBox()
        self.valid_until_month_spinbox.setRange(1, 12)
        self.valid_until_day_spinbox = QSpinBox()
        self.valid_until_day_spinbox.setRange(1, 31)
        form_layout.addRow(
            self.tr("Membership Valid Until (Month/Day):"),
            self._create_horizontal_layout([self.valid_until_month_spinbox, self.valid_until_day_spinbox])
        )

        # Year for which eCPs are issued (read-only)
        self.ecp_year_edit = QLineEdit()
        self.ecp_year_edit.setReadOnly(True)
        form_layout.addRow(self.tr("Issue year:"), self.ecp_year_edit)

        # Number of days for membership renewal
        self.renewal_window_spinbox = QSpinBox()
        self.renewal_window_spinbox.setRange(0, 365)
        form_layout.addRow(self.tr("Membership Renewal Window (days):"), self.renewal_window_spinbox)

        # IBAN
        self.iban_edit = QLineEdit()
        form_layout.addRow(self.tr("IBAN:"), self.iban_edit)

        # Account Name
        self.account_name_edit = QLineEdit()
        form_layout.addRow(self.tr("Account Name:"), self.account_name_edit)

        # Payment Link Generator
        self.payment_generator_combo = QComboBox()
        self.payment_generator_combo.addItem(self.tr("None (do not generate)"), "")
        for generator_name in get_available_generators():
            self.payment_generator_combo.addItem(generator_name, generator_name)
        form_layout.addRow(self.tr("Payment Link for eCP:"), self.payment_generator_combo)

        layout.addLayout(form_layout)

        # --- Google Wallet Settings ---
        wallet_header = QLabel(self.tr("Google Wallet Settings"))
        wallet_header.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(wallet_header)

        wallet_layout = QFormLayout()
        self.wallet_class_id_suffix_edit = QLineEdit()
        wallet_layout.addRow(self.tr("Pass Class ID Suffix:"), self.wallet_class_id_suffix_edit)

        self.wallet_checker_url_edit = QLineEdit()
        wallet_layout.addRow(self.tr("QR Code Verification URL:"), self.wallet_checker_url_edit)

        self.wallet_origin_domain_edit = QLineEdit()
        wallet_layout.addRow(self.tr("Wallet JWT Origin Domain:"), self.wallet_origin_domain_edit)
        layout.addLayout(wallet_layout)

        # --- Predefined Certificates Settings ---
        header_certs = QLabel(self.tr("Predefined Certificates"))
        header_certs.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(header_certs)

        certs_layout = QHBoxLayout()
        self.table_certs = QTableWidget()
        self.table_certs.setColumnCount(1)
        self.table_certs.setHorizontalHeaderLabels([self.tr("Certificate Name")])
        self.table_certs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_certs.horizontalHeader().setStyleSheet(utils.get_table_header_stylesheet())
        certs_layout.addWidget(self.table_certs)

        cert_btns_layout = QVBoxLayout()
        self.btn_add_cert = QPushButton(self.tr("➕ Add"))
        self.btn_add_cert.clicked.connect(self.add_cert_row)
        self.btn_remove_cert = QPushButton(self.tr("➖ Remove"))
        self.btn_remove_cert.clicked.connect(self.remove_cert_row)
        cert_btns_layout.addWidget(self.btn_add_cert)
        cert_btns_layout.addWidget(self.btn_remove_cert)
        cert_btns_layout.addStretch()
        certs_layout.addLayout(cert_btns_layout)
        layout.addLayout(certs_layout)

        # --- Membership Sticker Generation ---
        sticker_header = QLabel(self.tr("Membership Sticker Generator"))
        sticker_header.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(sticker_header)

        sticker_layout = QFormLayout()

        # Template file path
        self.sticker_template_path_edit = QLineEdit()
        self.sticker_template_path_edit.setReadOnly(True)
        self.btn_browse_template = QPushButton(self.tr("Browse..."))
        self.btn_browse_template.clicked.connect(self._browse_template_file)
        template_path_layout = QHBoxLayout()
        template_path_layout.addWidget(self.sticker_template_path_edit)
        template_path_layout.addWidget(self.btn_browse_template)
        sticker_layout.addRow(self.tr("Sticker Template (256x256 PNG):"), template_path_layout)

        # Sticker text color
        self.sticker_text_color_edit = QLineEdit()
        self.btn_pick_color = QPushButton(self.tr("Pick Color..."))
        self.btn_pick_color.clicked.connect(self._pick_sticker_text_color)
        text_color_layout = QHBoxLayout()
        text_color_layout.addWidget(self.sticker_text_color_edit)
        text_color_layout.addWidget(self.btn_pick_color)
        sticker_layout.addRow(self.tr("Sticker Text Color:"), text_color_layout)

        # Sticker background color
        self.sticker_bg_transparent_checkbox = QCheckBox(self.tr("Transparent Background"))
        self.sticker_bg_transparent_checkbox.stateChanged.connect(self._toggle_bg_color_widgets)
        sticker_layout.addRow(self.sticker_bg_transparent_checkbox)

        self.sticker_bg_color_edit = QLineEdit()
        self.btn_pick_bg_color = QPushButton(self.tr("Pick Color..."))
        self.btn_pick_bg_color.clicked.connect(self._pick_sticker_bg_color)
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(self.sticker_bg_color_edit)
        bg_color_layout.addWidget(self.btn_pick_bg_color)
        self.sticker_bg_color_label = QLabel(self.tr("Sticker Background Color:"))
        sticker_layout.addRow(self.sticker_bg_color_label, bg_color_layout)

        # Generate / Deploy buttons and preview
        sticker_buttons_layout = QHBoxLayout()
        self.btn_generate_sticker = QPushButton(self.tr("Generate Sticker"))
        self.btn_generate_sticker.setEnabled(False)
        self.btn_generate_sticker.clicked.connect(self._generate_sticker_preview)
        self.btn_deploy_sticker = QPushButton(self.tr("Deploy Sticker"))
        self.btn_deploy_sticker.setEnabled(False)
        self.btn_deploy_sticker.clicked.connect(self._deploy_sticker)
        sticker_buttons_layout.addWidget(self.btn_generate_sticker)
        sticker_buttons_layout.addWidget(self.btn_deploy_sticker)

        self.sticker_preview_label = QLabel(self.tr("No sticker generated yet."))
        self.sticker_preview_label.setFixedSize(500, 120)
        self.sticker_preview_label.setAlignment(Qt.AlignCenter)
        self.sticker_preview_label.setFrameShape(QFrame.StyledPanel)
        self.sticker_preview_label.setStyleSheet("border: 1px solid #B0B0B0; background-color: #F0F0F0;")

        sticker_layout.addRow(sticker_buttons_layout)
        sticker_layout.addRow(self.tr("Current Sticker Preview:"), self.sticker_preview_label)
        layout.addLayout(sticker_layout)

        # Save button
        self.save_button = QPushButton(self.tr("Save Settings"))
        self.save_button.clicked.connect(self.save_settings)

        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.save_button, alignment=Qt.AlignLeft)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        # Signals
        self.iban_edit.textChanged.connect(self.update_payment_generator_state)
        self.account_name_edit.textChanged.connect(self.update_payment_generator_state)

    # --- Helpers ---

    def _create_horizontal_layout(self, widgets):
        """Helper to create a QHBoxLayout for multiple widgets in one form row."""
        h_layout = QHBoxLayout()
        for widget in widgets:
            h_layout.addWidget(widget)
        return h_layout

    def update_payment_generator_state(self):
        """Enables/disables the payment link generator based on IBAN and Account Name."""
        iban_ok = bool(self.iban_edit.text().strip())
        account_name_ok = bool(self.account_name_edit.text().strip())
        self.payment_generator_combo.setEnabled(iban_ok and account_name_ok)
        if not (iban_ok and account_name_ok):
            self.payment_generator_combo.setCurrentIndex(0)

    def _reload_countries_for_language(self):
        selected_lang_code = self.language_combo.currentData()
        current_country_code_selection = self.country_combo.currentData()

        countries_data = utils.get_world_countries(locale_identifier=selected_lang_code)
        self.country_combo.clear()
        for name, code in countries_data:
            self.country_combo.addItem(name, code)

        new_index = self.country_combo.findData(current_country_code_selection)
        self.country_combo.setCurrentIndex(new_index if new_index >= 0 else 0)

    # --- Certificate table ---

    def add_cert_row(self):
        row_count = self.table_certs.rowCount()
        self.table_certs.insertRow(row_count)
        self.table_certs.setItem(row_count, 0, QTableWidgetItem(""))
        self.table_certs.editItem(self.table_certs.item(row_count, 0))

    def remove_cert_row(self):
        current_row = self.table_certs.currentRow()
        if current_row >= 0:
            self.table_certs.removeRow(current_row)

    # --- Sticker ---

    def _browse_template_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Sticker Template"), "", self.tr("PNG Images (*.png)")
        )
        if file_path:
            self.sticker_template_path_edit.setText(file_path)
            self.btn_generate_sticker.setEnabled(True)
            self.btn_deploy_sticker.setEnabled(False)
            self.generated_sticker_data = None

    def _pick_sticker_text_color(self):
        current_color = self.sticker_text_color_edit.text()
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.sticker_text_color_edit.setText(color.name())

    def _pick_sticker_bg_color(self):
        current_color = self.sticker_bg_color_edit.text()
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.sticker_bg_color_edit.setText(color.name())

    def _toggle_bg_color_widgets(self):
        is_transparent = self.sticker_bg_transparent_checkbox.isChecked()
        self.sticker_bg_color_label.setEnabled(not is_transparent)
        self.sticker_bg_color_edit.setEnabled(not is_transparent)
        self.btn_pick_bg_color.setEnabled(not is_transparent)

    def _generate_sticker_preview(self):
        template_path = self.sticker_template_path_edit.text()
        if not template_path or not os.path.exists(template_path):
            utils.show_warning_message(self.tr("Please select a valid template file first."))
            return
        try:
            with open(template_path, 'rb') as f:
                template_data = f.read()

            year = str(utils.get_membership_fee_year())
            sticker_data = utils.generate_membership_sticker(template_data, year)
            if not sticker_data:
                utils.show_error_message(self.tr("Failed to generate sticker image."))
                self.btn_deploy_sticker.setEnabled(False)
                self.generated_sticker_data = None
                return

            self.generated_sticker_data = sticker_data
            pixmap = QPixmap()
            pixmap.loadFromData(sticker_data)
            self.sticker_preview_label.setPixmap(pixmap)
            self.btn_deploy_sticker.setEnabled(True)
            utils.show_success_message(self.tr("Sticker generated. You can now deploy it."))
        except Exception as e:
            self.btn_deploy_sticker.setEnabled(False)
            self.generated_sticker_data = None
            utils.show_error_message(f"{self.tr('An error occurred during sticker generation')}: {e}")

    def _deploy_sticker(self):
        if not self.generated_sticker_data:
            utils.show_warning_message(self.tr("No sticker has been generated yet. Please generate one first."))
            return
        try:
            year = str(utils.get_membership_fee_year())
            blob_name = f"membership_stickers/sticker_{year}_{uuid.uuid4().hex}.png"
            public_url = utils.upload_to_bucket(blob_name, self.generated_sticker_data, "image/png")
            if not public_url:
                utils.show_error_message(self.tr("Failed to upload sticker to cloud storage."))
                return
            utils.set_membership_sticker_url(public_url)
            pixmap = utils.load_image_from_url(public_url, max_size=(500, 120))
            if pixmap:
                self.sticker_preview_label.setPixmap(pixmap)
            utils.show_success_message(self.tr("Sticker successfully deployed to the cloud."))
            self.btn_deploy_sticker.setEnabled(False)
        except Exception as e:
            utils.show_error_message(f"{self.tr('An error occurred during sticker deployment')}: {e}")

    # --- Load / Save ---

    def load_settings(self):
        pref_country_code = utils.get_preferred_country_code()
        pref_language_code = utils.get_preferred_language()

        countries_data = utils.get_world_countries(locale_identifier=pref_language_code)
        self.country_combo.clear()
        for country_name, country_code in countries_data:
            self.country_combo.addItem(country_name, country_code)

        current_country_index = self.country_combo.findData(pref_country_code)
        if current_country_index >= 0:
            self.country_combo.setCurrentIndex(current_country_index)
        elif self.country_combo.count() > 0:
            self.country_combo.setCurrentIndex(0)

        current_lang_index = self.language_combo.findData(pref_language_code)
        if current_lang_index >= 0:
            self.language_combo.setCurrentIndex(current_lang_index)
        elif self.language_combo.count() > 0:
            self.language_combo.setCurrentIndex(0)

        self.language_combo.currentIndexChanged.connect(self._reload_countries_for_language)

        self.currency_edit.setText(utils.get_membership_currency())
        self.fee_normal_spinbox.setValue(utils.get_membership_fee_normal())
        self.fee_discounted_spinbox.setValue(utils.get_membership_fee_discounted())
        self.valid_until_month_spinbox.setValue(utils.get_membership_valid_until_month())
        self.valid_until_day_spinbox.setValue(utils.get_membership_valid_until_day())
        self.renewal_window_spinbox.setValue(utils.get_membership_renewal_window_days())
        self.ecp_year_edit.setText(str(utils.get_membership_fee_year()))
        self.iban_edit.setText(utils.get_iban())
        self.account_name_edit.setText(utils.get_account_name())

        saved_generator = utils.get_payment_link_generator_name()
        index = self.payment_generator_combo.findData(saved_generator)
        if index != -1:
            self.payment_generator_combo.setCurrentIndex(index)
        self.update_payment_generator_state()

        # Certificates
        self.table_certs.setRowCount(0)
        certs = utils.get_predefined_certificates()
        self.table_certs.setRowCount(len(certs))
        for row, cert_name in enumerate(certs):
            self.table_certs.setItem(row, 0, QTableWidgetItem(cert_name))

        # Sticker settings
        sticker_template_path = utils.get_membership_sticker_template_path()
        if sticker_template_path and os.path.exists(sticker_template_path):
            self.sticker_template_path_edit.setText(sticker_template_path)
            self.btn_generate_sticker.setEnabled(True)

        sticker_url = utils.get_membership_sticker_url()
        if sticker_url:
            pixmap = utils.load_image_from_url(sticker_url, max_size=(500, 120))
            if pixmap:
                self.sticker_preview_label.setPixmap(pixmap)

        sticker_text_color = utils.get_membership_sticker_text_color()
        self.sticker_text_color_edit.setText(sticker_text_color)

        sticker_bg_color = utils.get_membership_sticker_bg_color()
        is_transparent = sticker_bg_color.lower() == 'transparent'
        self.sticker_bg_transparent_checkbox.setChecked(is_transparent)
        if not is_transparent:
            self.sticker_bg_color_edit.setText(sticker_bg_color)
        self._toggle_bg_color_widgets()

        # Google Wallet settings
        self.wallet_class_id_suffix_edit.setText(utils.get_wallet_class_id_suffix())
        self.wallet_checker_url_edit.setText(utils.get_wallet_checker_url())
        self.wallet_origin_domain_edit.setText(utils.get_wallet_origin_domain())

    def save_settings(self):
        selected_country_code = self.country_combo.currentData()
        selected_language_code = self.language_combo.currentData()
        membership_currency = self.currency_edit.text().strip().upper()
        membership_fee_normal = f"{self.fee_normal_spinbox.value():.2f}"
        membership_fee_discounted = f"{self.fee_discounted_spinbox.value():.2f}"
        membership_valid_until_month = str(self.valid_until_month_spinbox.value())
        membership_valid_until_day = str(self.valid_until_day_spinbox.value())
        membership_renewal_window_days = str(self.renewal_window_spinbox.value())
        iban = self.iban_edit.text().strip().upper()
        account_name = self.account_name_edit.text().strip()
        payment_link_generator_name = self.payment_generator_combo.currentData()
        sticker_template_path = self.sticker_template_path_edit.text()
        sticker_text_color = self.sticker_text_color_edit.text()
        wallet_class_id_suffix = self.wallet_class_id_suffix_edit.text()
        wallet_checker_url = self.wallet_checker_url_edit.text()
        wallet_origin_domain = self.wallet_origin_domain_edit.text()

        if self.sticker_bg_transparent_checkbox.isChecked():
            sticker_bg_color = 'transparent'
        else:
            sticker_bg_color = self.sticker_bg_color_edit.text()

        if not selected_country_code:
            utils.show_warning_message(self.tr("Please select a preferred country."))
            return
        if not selected_language_code:
            utils.show_warning_message(self.tr("Please select a preferred language."))
            return
        if not membership_currency:
            utils.show_warning_message(self.tr("Please enter the membership currency."))
            return

        certs = []
        for row in range(self.table_certs.rowCount()):
            item = self.table_certs.item(row, 0)
            if item and item.text().strip():
                certs.append(item.text().strip())

        if utils.save_app_settings(
            selected_country_code, selected_language_code,
            membership_currency, membership_fee_normal, membership_fee_discounted,
            membership_valid_until_month, membership_valid_until_day, membership_renewal_window_days,
            iban, account_name, payment_link_generator_name,
            sticker_template_path, sticker_text_color, sticker_bg_color,
            wallet_class_id_suffix, wallet_checker_url, wallet_origin_domain,
            predefined_certificates=certs
        ):
            utils.show_success_message(self.tr("Settings saved successfully."))
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save settings."))

    def showEvent(self, event):
        """Called when the widget is shown."""
        super().showEvent(event)
        self.load_settings()