# views/settings_view.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox, QPushButton, 
    QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt, QCoreApplication
import utils

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop) # Align content to the top

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
            self.language_combo.addItem(display_name, code) # We save the code as UserData
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
        form_layout.addRow(self.tr("Membership Valid Until (Month/Day):"), self._create_horizontal_layout([self.valid_until_month_spinbox, self.valid_until_day_spinbox]))

        # Number of days for membership renewal
        self.renewal_window_spinbox = QSpinBox()
        self.renewal_window_spinbox.setRange(0, 365) # E.g., 0 to 365 days
        form_layout.addRow(self.tr("Membership Renewal Window (days):"), self.renewal_window_spinbox)

        # IBAN
        self.iban_edit = QLineEdit()
        form_layout.addRow(self.tr("IBAN:"), self.iban_edit)

        layout.addLayout(form_layout)

        # Save button
        self.save_button = QPushButton(self.tr("Save Settings"))
        self.save_button.clicked.connect(self.save_settings)
        
        buttons_layout = QVBoxLayout() # We use QVBoxLayout for the button
        buttons_layout.addWidget(self.save_button, alignment=Qt.AlignLeft) # Align left
        buttons_layout.addStretch() # Indentation from the bottom

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _create_horizontal_layout(self, widgets):
        """Helper to create a QHBoxLayout for multiple widgets in one form row."""
        h_layout = QHBoxLayout()
        for widget in widgets:
            h_layout.addWidget(widget)
        return h_layout

    def load_settings(self):
        # Loading preferred country
        pref_country_code = utils.get_preferred_country_code()
        pref_language_code = utils.get_preferred_language()

        # Loading the list of countries based on the currently preferred language
        # utils.get_world_countries() will use the preferred language if not specified
        countries_data = utils.get_world_countries(locale_identifier=pref_language_code)
        self.country_combo.clear()
        for country_name, country_code in countries_data:
            self.country_combo.addItem(country_name, country_code) # Name as text, code as data

        current_country_index = self.country_combo.findData(pref_country_code)
        if current_country_index >= 0:
            self.country_combo.setCurrentIndex(current_country_index)
        elif self.country_combo.count() > 0:
             # If the preferred country code is not in the list, we select the first one
            self.country_combo.setCurrentIndex(0)

        # Loading preferred language
        current_lang_index = self.language_combo.findData(pref_language_code)
        if current_lang_index >= 0:
            self.language_combo.setCurrentIndex(current_lang_index)
        elif self.language_combo.count() > 0:
            self.language_combo.setCurrentIndex(0) # Fallback na prvú položku
        
        # If the language has changed, the list of countries may have changed, so we reload it
        self.language_combo.currentIndexChanged.connect(self._reload_countries_for_language)

        # Loading other settings
        self.currency_edit.setText(utils.get_membership_currency())
        self.fee_normal_spinbox.setValue(utils.get_membership_fee_normal())
        self.fee_discounted_spinbox.setValue(utils.get_membership_fee_discounted())
        self.valid_until_month_spinbox.setValue(utils.get_membership_valid_until_month())
        self.valid_until_day_spinbox.setValue(utils.get_membership_valid_until_day())
        self.renewal_window_spinbox.setValue(utils.get_membership_renewal_window_days())
        self.iban_edit.setText(utils.get_iban())

    def _reload_countries_for_language(self):
        selected_lang_code = self.language_combo.currentData()
        current_country_code_selection = self.country_combo.currentData() # We remember the currently selected country code

        countries_data = utils.get_world_countries(locale_identifier=selected_lang_code)
        self.country_combo.clear()
        for name, code in countries_data:
            self.country_combo.addItem(name, code)
        
        new_index = self.country_combo.findData(current_country_code_selection)
        self.country_combo.setCurrentIndex(new_index if new_index >= 0 else 0)

    def save_settings(self):
        selected_country_code = self.country_combo.currentData() # We get the country code
        selected_language_code = self.language_combo.currentData()
        membership_currency = self.currency_edit.text().strip().upper()
        membership_fee_normal = f"{self.fee_normal_spinbox.value():.2f}" # We save as a string with 2 decimal places
        membership_fee_discounted = f"{self.fee_discounted_spinbox.value():.2f}" # We save as a string
        membership_valid_until_month = str(self.valid_until_month_spinbox.value())
        membership_valid_until_day = str(self.valid_until_day_spinbox.value())
        membership_renewal_window_days = str(self.renewal_window_spinbox.value())
        iban = self.iban_edit.text().strip().upper()

        if not selected_country_code:
            utils.show_warning_message(self.tr("Please select a preferred country."))
            return

        if not selected_language_code:
            utils.show_warning_message(self.tr("Please select a preferred language."))
            return
        if not membership_currency:
            utils.show_warning_message(self.tr("Please enter the membership currency."))
            return

        if utils.save_app_settings(
            selected_country_code, selected_language_code,
            membership_currency, membership_fee_normal, membership_fee_discounted,
            membership_valid_until_month, membership_valid_until_day, membership_renewal_window_days,
            iban
        ):
            utils.show_success_message(self.tr("Settings saved successfully."))
            # After successful saving, we can reload the settings
            # to reflect the changes (e.g., list of countries in another language).
            # This can be important if a language change affects other parts of the UI immediately.
            # For simplicity, we are not doing this here now, but it is an option.
            # utils.load_all_configs() # Reloads the configuration from disk
            # self.load_settings() # Reloads the values into the UI
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save settings."))

    def showEvent(self, event):
        """Called when the widget is shown."""
        super().showEvent(event)
        self.load_settings() # Always load current settings when shown