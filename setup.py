import os
from PyQt5.QtWidgets import ( QApplication,
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QFormLayout, QMessageBox, QDialog, QDialogButtonBox, QGridLayout
) # Add QFont
from PyQt5.QtCore import Qt, QTimer
from config import secret_manager # Importujeme globálny secret_manager
from PyQt5.QtGui import QIcon

class PinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zadajte PIN")
        self.result = False
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "Logo_sss.ico")  # Uprav cestu, ak je to potrebné
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
 
        layout = QVBoxLayout()
        label = QLabel("PIN:")
        self.pin_entry = QLineEdit()
        self.pin_entry.setFixedHeight(32) # Zväčšenie výšky políčka
        self.pin_entry.setEchoMode(QLineEdit.Password)
        self.pin_entry.setAlignment(Qt.AlignLeft)
        layout.addWidget(label)
        layout.addWidget(self.pin_entry)
        self.setMinimumWidth(350) # Nastavenie minimálnej šírky dialógu

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.check_pin)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        # Timer for automatic PIN check
        self.auto_check_timer = QTimer(self)
        self.auto_check_timer.setSingleShot(True)
        self.auto_check_timer.timeout.connect(self.attempt_auto_accept)
        self.pin_entry.textChanged.connect(self.schedule_auto_check)

    def schedule_auto_check(self):
        # Start or restart the timer with a short delay (e.g., 500ms)
        self.auto_check_timer.start(500)

    def attempt_auto_accept(self):
        pin = self.pin_entry.text()
        if pin and secret_manager.decrypt_file(pin): # Only attempt if PIN is not empty
            self.result = True
            self.accept()

    def check_pin(self):
        self.auto_check_timer.stop()
        pin = self.pin_entry.text()
        if secret_manager.decrypt_file(pin): #pouzivame globalny secret_manager
            self.result = True
            self.accept()
        else:
            QMessageBox.critical(self, "Chyba", "Nesprávny PIN!")
            self.pin_entry.clear()
            self.pin_entry.setFocus()

class NewPinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zadajte nový PIN")
        self.result = None
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "Logo_sss.ico")  # Uprav cestu, ak je to potrebné
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QFormLayout()
        self.new_pin_entry = QLineEdit()
        self.new_pin_entry.setFixedHeight(32) # Zväčšenie výšky políčka
        self.new_pin_entry.setEchoMode(QLineEdit.Password)
        self.new_pin_entry.setAlignment(Qt.AlignLeft)
        self.confirm_pin_entry = QLineEdit()
        self.confirm_pin_entry.setFixedHeight(32) # Zväčšenie výšky políčka
        self.confirm_pin_entry.setEchoMode(QLineEdit.Password)
        self.confirm_pin_entry.setAlignment(Qt.AlignLeft)
        layout.addRow("Nový PIN:", self.new_pin_entry)
        layout.addRow("Potvrďte PIN:", self.confirm_pin_entry)

        self.setMinimumWidth(450) # Nastavenie minimálnej šírky dialógu

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.check_pins)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)

    def check_pins(self):
        new_pin = self.new_pin_entry.text()
        confirmed_pin = self.confirm_pin_entry.text()
        if new_pin == confirmed_pin:
            if len(new_pin) >= 8:
                self.result = new_pin
                self.accept()
            else:
                QMessageBox.critical(self, "Chyba", "PIN musí mať aspoň 8 znakov!")
        else:
            QMessageBox.critical(self, "Chyba", "PINy sa nezhodujú!")
            self.new_pin_entry.clear()
            self.confirm_pin_entry.clear()

class SecretSetupGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nastavenie Secretov")
        self.secrets = {}
        self.entries = {} # Zväčšenie okna
        self.setFixedSize(800, 550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        icon_path = os.path.join(os.path.dirname(__file__), "icons", "Logo_sss.ico")  # Uprav cestu, ak je to potrebné
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.create_widgets()

    def create_widgets(self):
        layout = QVBoxLayout()
        grid = QGridLayout()
        layout.addLayout(grid)

        fields = [
            ("db_host", "DB host:"),
            ("db_port", "DB Port:"),
            ("db_name", "DB name:"),
            ("db_user", "DB user:"),
            ("db_password", "DB password:"),
            ("credentials_json", "JSON credentials:"),
            ("project_id", "Google Cloud project:"),
            ("bucket_name", "Bucket name:"),
            ("logo_pic", "Society Logo file:"),
            ("crypt_key", "Crypt key:")
        ]

        row = 0
        for key, label_text in fields:
            label = QLabel(label_text)
            entry = QLineEdit()
            entry.setFixedHeight(32) # Zväčšenie výšky políčok
            entry.setMinimumWidth(500) # Úprava minimálnej šírky políčok
            entry.setAlignment(Qt.AlignLeft)
            if key == "crypt_key":
                entry.setEchoMode(QLineEdit.Password)
            grid.addWidget(label, row, 0)
            grid.addWidget(entry, row, 1)
            self.entries[key] = entry
            row += 1

        self.save_button = QPushButton("Uložiť")
        self.save_button.clicked.connect(self.save_secrets)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def load_secrets(self):
        if secret_manager.secrets:
            for key, value in secret_manager.secrets.items():
                if key in self.entries:
                    self.entries[key].setText(value)

    def save_secrets(self):
        secrets_to_save = {}
        for key, entry in self.entries.items():
            secrets_to_save[key] = entry.text()

        if secret_manager.pin:
            pin = secret_manager.pin
        else:
            new_pin_dialog = NewPinDialog(self)
            if new_pin_dialog.exec_() == QDialog.Accepted:
                pin = new_pin_dialog.result
            else:
                return

        if secret_manager.encrypt_and_save_file(secrets_to_save, pin):
            QMessageBox.information(self, "Úspech", "Secrets boli úspešne uložené!")
            self.close()
        else:
            QMessageBox.critical(self, "Chyba", "Nepodarilo sa uložiť secrets!")

def run_setup(app):
    gui = SecretSetupGUI()
    gui.load_secrets()
    gui.show()
    app.exec_()
    return secret_manager

def show_pin_dialog(app):
    pin_dialog = PinDialog()
    if pin_dialog.exec_() == QDialog.Rejected or not pin_dialog.result:
        return False #vraciame False ak sa nepodarilo desifrovat
    return True #vraciame True ak sa podarilo desifrovat

if __name__ == "__main__":
    import sys
    from PyQt5.QtGui import QFont # Import QFont

    app = QApplication(sys.argv)

    default_font = QFont()
    default_font.setPointSize(11) # Nastavenie väčšej veľkosti písma (napr. 11pt)
    app.setFont(default_font)

    # Pokus o načítanie a dešifrovanie existujúcich secretov, ak súbor existuje
    if os.path.exists(secret_manager.properties_file):
        print(f"INFO: Súbor '{secret_manager.properties_file}' existuje. Pokus o dešifrovanie...")
        if not show_pin_dialog(app):
            # Ak dešifrovanie zlyhalo (nesprávny PIN alebo zrušené),
            # secret_manager.secrets zostanú prázdne.
            # GUI sa otvorí s prázdnymi poliami pre nové nastavenie.
            QMessageBox.warning(None, "Info",
                                "Nepodarilo sa dešifrovať existujúce nastavenia alebo bola operácia zrušená. "
                                "Môžete zadať nové nastavenia, ktoré prepíšu pôvodný súbor (ak existoval).")
        else:
            print("INFO: Existujúce secrets boli úspešne dešifrované.")

    setup_gui = SecretSetupGUI()
    # load_secrets() načíta hodnoty z secret_manager.secrets (ak boli úspešne dešifrované)
    setup_gui.load_secrets()
    setup_gui.show()
    sys.exit(app.exec_())
