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
        layout.setAlignment(Qt.AlignTop) # Zarovnanie obsahu nahor

        header = QLabel(self.tr("Application Settings"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        form_layout = QFormLayout()

        # Preferovaná krajina
        self.country_combo = QComboBox()
        form_layout.addRow(self.tr("Preferred Country:"), self.country_combo)

        # Preferovaný jazyk / lokalizácia
        self.language_combo = QComboBox()
        supported_locales = utils.get_supported_locales_display()
        for code, display_name in supported_locales.items():
            self.language_combo.addItem(display_name, code) # Uložíme kód ako UserData
        form_layout.addRow(self.tr("Preferred Language:"), self.language_combo)

        # Mena pre členské príspevky
        self.currency_edit = QLineEdit()
        form_layout.addRow(self.tr("Membership Currency:"), self.currency_edit)

        # Výška normálneho členského
        self.fee_normal_spinbox = QDoubleSpinBox()
        self.fee_normal_spinbox.setDecimals(2)
        self.fee_normal_spinbox.setMinimum(0.00)
        self.fee_normal_spinbox.setMaximum(9999.99)
        form_layout.addRow(self.tr("Normal Membership Fee:"), self.fee_normal_spinbox)

        # Výška zľavneného členského
        self.fee_discounted_spinbox = QDoubleSpinBox()
        self.fee_discounted_spinbox.setDecimals(2)
        self.fee_discounted_spinbox.setMinimum(0.00)
        self.fee_discounted_spinbox.setMaximum(9999.99)
        form_layout.addRow(self.tr("Discounted Membership Fee:"), self.fee_discounted_spinbox)

        # Dátum platnosti členského (mesiac a deň)
        self.valid_until_month_spinbox = QSpinBox()
        self.valid_until_month_spinbox.setRange(1, 12)
        self.valid_until_day_spinbox = QSpinBox()
        self.valid_until_day_spinbox.setRange(1, 31)
        form_layout.addRow(self.tr("Membership Valid Until (Month/Day):"), self._create_horizontal_layout([self.valid_until_month_spinbox, self.valid_until_day_spinbox]))

        # Počet dní na obnovu členského
        self.renewal_window_spinbox = QSpinBox()
        self.renewal_window_spinbox.setRange(0, 365) # Napr. 0 až 365 dní
        form_layout.addRow(self.tr("Membership Renewal Window (days):"), self.renewal_window_spinbox)

        # IBAN
        self.iban_edit = QLineEdit()
        form_layout.addRow(self.tr("IBAN:"), self.iban_edit)

        layout.addLayout(form_layout)

        # Tlačidlo Uložiť
        self.save_button = QPushButton(self.tr("Save Settings"))
        self.save_button.clicked.connect(self.save_settings)
        
        buttons_layout = QVBoxLayout() # Použijeme QVBoxLayout pre tlačidlo
        buttons_layout.addWidget(self.save_button, alignment=Qt.AlignLeft) # Zarovnanie doľava
        buttons_layout.addStretch() # Odsadenie zospodu

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _create_horizontal_layout(self, widgets):
        """Helper to create a QHBoxLayout for multiple widgets in one form row."""
        h_layout = QHBoxLayout()
        for widget in widgets:
            h_layout.addWidget(widget)
        return h_layout

    def load_settings(self):
        # Načítanie preferovanej krajiny
        pref_country_code = utils.get_preferred_country_code()
        pref_language_code = utils.get_preferred_language()

        # Načítanie zoznamu krajín na základe aktuálne preferovaného jazyka
        # utils.get_world_countries() použije preferovaný jazyk, ak nie je špecifikovaný
        countries_data = utils.get_world_countries(locale_identifier=pref_language_code)
        self.country_combo.clear()
        for country_name, country_code in countries_data:
            self.country_combo.addItem(country_name, country_code) # Názov ako text, kód ako dáta

        current_country_index = self.country_combo.findData(pref_country_code)
        if current_country_index >= 0:
            self.country_combo.setCurrentIndex(current_country_index)
        elif self.country_combo.count() > 0:
             # Ak preferovaný kód krajiny nie je v zozname, vyberieme prvú
            self.country_combo.setCurrentIndex(0)

        # Načítanie preferovaného jazyka
        current_lang_index = self.language_combo.findData(pref_language_code)
        if current_lang_index >= 0:
            self.language_combo.setCurrentIndex(current_lang_index)
        elif self.language_combo.count() > 0:
            self.language_combo.setCurrentIndex(0) # Fallback na prvú položku
        
        # Ak sa zmenil jazyk, zoznam krajín sa mohol zmeniť, tak ho prenačítame
        self.language_combo.currentIndexChanged.connect(self._reload_countries_for_language)

        # Načítanie ostatných nastavení
        self.currency_edit.setText(utils.get_membership_currency())
        self.fee_normal_spinbox.setValue(utils.get_membership_fee_normal())
        self.fee_discounted_spinbox.setValue(utils.get_membership_fee_discounted())
        self.valid_until_month_spinbox.setValue(utils.get_membership_valid_until_month())
        self.valid_until_day_spinbox.setValue(utils.get_membership_valid_until_day())
        self.renewal_window_spinbox.setValue(utils.get_membership_renewal_window_days())
        self.iban_edit.setText(utils.get_iban())

    def _reload_countries_for_language(self):
        selected_lang_code = self.language_combo.currentData()
        current_country_code_selection = self.country_combo.currentData() # Zapamätáme si aktuálne vybraný kód krajiny

        countries_data = utils.get_world_countries(locale_identifier=selected_lang_code)
        self.country_combo.clear()
        for name, code in countries_data:
            self.country_combo.addItem(name, code)
        
        new_index = self.country_combo.findData(current_country_code_selection)
        self.country_combo.setCurrentIndex(new_index if new_index >= 0 else 0)

    def save_settings(self):
        selected_country_code = self.country_combo.currentData() # Získame kód krajiny
        selected_language_code = self.language_combo.currentData()
        membership_currency = self.currency_edit.text().strip().upper()
        membership_fee_normal = f"{self.fee_normal_spinbox.value():.2f}" # Uložíme ako string s 2 desatinnými miestami
        membership_fee_discounted = f"{self.fee_discounted_spinbox.value():.2f}" # Uložíme ako string
        membership_valid_until_month = str(self.valid_until_month_spinbox.value())
        membership_valid_until_day = str(self.valid_until_day_spinbox.value())
        membership_renewal_window_days = str(self.renewal_window_spinbox.value())
        iban = self.iban_edit.text().strip().upper()

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
            # Po úspešnom uložení môžeme znova načítať nastavenia,
            # aby sa prejavili zmeny (napr. zoznam krajín v inom jazyku)
            # Toto môže byť dôležité, ak zmena jazyka ovplyvňuje iné časti UI okamžite.
            # Pre jednoduchosť to tu teraz nerobíme, ale je to možnosť.
            # utils.load_all_configs() # Znovu načíta konfiguráciu z disku
            # self.load_settings() # Znovu načíta hodnoty do UI
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save settings."))

    def showEvent(self, event):
        """Called when the widget is shown."""
        super().showEvent(event)
        self.load_settings() # Vždy načítať aktuálne nastavenia pri zobrazení