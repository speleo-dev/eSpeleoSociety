# utils.py
import os, hmac, uuid, hashlib
import configparser
from typing import TYPE_CHECKING
import requests, os, binascii
import qrcode
import base64
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from cryptography.hazmat.primitives import padding # Added import
from cryptography.hazmat.primitives.ciphers import algorithms
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter
from PyQt5.QtCore import Qt, QTimer
from google.cloud import storage
from datetime import date
from babel import Locale, UnknownLocaleError # Import for Babel
from babel.core import localedata # Changed import
from config import secret_manager
from PyQt5.QtWidgets import QMainWindow, QApplication # Added for type hinting, access to status_bar and QApplication

if TYPE_CHECKING:
    from model import Member, Club


CONFIG_FILE_PATH = 'config.properties'
SUPPORTED_LOCALES_FILE_PATH = os.path.join('translate', 'supported_locales.ini')

_app_config_cache = None
_supported_locales_cache = None

def load_all_configs():
    """Loads both application and library configurations."""
    global _app_config_cache, _supported_locales_cache
    
    # Load app config
    _app_config_cache = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE_PATH):
        _app_config_cache.read(CONFIG_FILE_PATH, encoding='utf-8')
    else:
        _app_config_cache['DEFAULT'] = {
            'preferred_country': 'SK', # We store the country code
            'preferred_language': 'en_US',
            'membership_currency': 'EUR',
            'membership_fee_normal': '20.00',
            'membership_fee_discounted': '10.00',
            'membership_valid_until_month': '12',
            'membership_valid_until_day': '31',   # 31st
            'membership_renewal_window_days': '90', # 90 days before expiry
            'iban': '' # Default empty IBAN
        }
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as configfile:
                _app_config_cache.write(configfile)
            print(f"INFO: Created default '{CONFIG_FILE_PATH}'.")
        except IOError as e:
            print(f"ERROR: Could not write default '{CONFIG_FILE_PATH}': {e}")

    # Load supported locales
    _supported_locales_cache = configparser.ConfigParser()
    if os.path.exists(SUPPORTED_LOCALES_FILE_PATH):
        _supported_locales_cache.read(SUPPORTED_LOCALES_FILE_PATH, encoding='utf-8')
    else:
        print(f"WARNING: '{SUPPORTED_LOCALES_FILE_PATH}' not found. Creating with default values.")
        _supported_locales_cache['Locales'] = {
            'en_US': 'English (United States)'
        }
        try:
            os.makedirs(os.path.dirname(SUPPORTED_LOCALES_FILE_PATH), exist_ok=True)
            with open(SUPPORTED_LOCALES_FILE_PATH, 'w', encoding='utf-8') as localesfile:
                _supported_locales_cache.write(localesfile)
        except IOError as e:
            print(f"ERROR: Could not write default '{SUPPORTED_LOCALES_FILE_PATH}': {e}")

def load_logo():
    try:
        response = requests.get(secret_manager.get_logo_url())
        response.raise_for_status()
        image_data = response.content
        image = QImage.fromData(image_data)
        pixmap = QPixmap.fromImage(image)
        return pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        print("Error loading logo:", e)
        return None

def delete_photo_from_bucket(photo_hash: str):
    # Set environment variable for authentication
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secret_manager.get_secret("credentials_json")

    client = storage.Client(project=secret_manager.get_secret("project_id"))
    bucket = client.bucket(secret_manager.get_secret("bucket_name"))
    # The photo is saved with a .png extension
    blob = bucket.blob(f"{photo_hash}.png")
    try:
        blob.delete()
        print(f"Subor '{photo_hash}.png' bol odstraneny z bucketu '{secret_manager.get_secret("bucket_name")}'.")
    except Exception as e:
        print("Chyba pri mazaní fotografie z bucketu:", e)

def upload_photo_to_bucket(photo_hash: str, image_data):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secret_manager.get_secret("credentials_json")

    # Create a client and get the bucket
    client = storage.Client()
    bucket = client.bucket(secret_manager.get_secret("bucket_name"))

    destination_blob_name = f"{photo_hash}.png"
    # Create a blob object and upload the file
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(bytes(image_data), content_type="image/png")

def send_to_google_wallet(req_details):
    # Simulácia odoslania nového objektu preukazu do Google Wallet API.
    # Implementujte reálne volanie API podľa dokumentácie Google Wallet.
    print("Odosielam nový objekt preukazu do Google Wallet API pre žiadosť", req_details.get("photo_hash", "")) # Assuming translated key
    # Simulovaný výsledok:
    return True

def load_image_from_url(url, max_size=(225, 330)):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.content
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            raise Exception("Nepodarilo sa načítať pixmapu z dát.")
        # Scale the image to the maximum size while maintaining the aspect ratio
        pixmap = pixmap.scaled(max_size[0], max_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap
    except requests.exceptions.RequestException as e:
        print(f"Chyba pri načítaní obrázka z URL: {url} - {e}")
        return None
    
def decrypt_date(encrypted_hex):
    return _decrypt_data(encrypted_hex)

def _encrypt_data(data: str) -> str:
    try:
        # Use the first 16 bytes of the key for AES; the key must be the same as in the DB
        key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]
        cipher = AES.new(key_bytes, AES.MODE_CBC)
        iv = cipher.iv  # Use the generated IV

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data.encode('utf-8')) + padder.finalize()

        ciphertext = cipher.encrypt(padded_data)

        combined = iv + ciphertext
        return binascii.hexlify(combined).decode('utf-8')
    except Exception as e:
        print(f"Error encrypting data: {e}")
        return None

def _decrypt_data(encrypted_hex: str) -> str:
    if not encrypted_hex: return None

    if not isinstance(encrypted_hex, str):
        print(f"Warning: Expected a hex string for decryption, got: {type(encrypted_hex)}")
        return None

    if len(encrypted_hex) % 32 != 0:
        print(f"Warning: Invalid hex string length for decryption, expected multiple of 32, got: {len(encrypted_hex)}")
        return None

    try:
        # Convert hex string to bytes
        encrypted_bytes = binascii.unhexlify(encrypted_hex)

        # Separate IV (first 16 bytes)
        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        # Use the first 16 bytes of the key; the key must be the same as in the DB
        key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)

        decrypted_padded = cipher.decrypt(ciphertext)

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        return unpadded_data.decode('utf-8')
    except (binascii.Error, ValueError, Exception) as e:
        print(f"Decryption error for hex '{encrypted_hex}': {e}")
        return None  # Return None if decoding fails

def _encrypt_symmetric(plaintext: str) -> bytes:
    """Symmetrically encrypts a string using AES CBC and returns bytes (iv + ciphertext)."""
    try:
        key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]
        cipher = AES.new(key_bytes, AES.MODE_CBC)
        iv = cipher.iv

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()
        
        ciphertext = cipher.encrypt(padded_data)
        return iv + ciphertext
    except Exception as e:
        print(f"Error during symmetric encryption: {e}")
        return None

def _decrypt_symmetric(encrypted_data: bytes) -> str:
    """Symmetrically decrypts bytes (iv + ciphertext) using AES CBC."""
    try:
        key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
        decrypted_padded = cipher.decrypt(ciphertext)

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted_data.decode('utf-8')
    except (ValueError, KeyError, Exception) as e:
        print(f"Error during symmetric decryption: {e}")
        return None

def generate_payment_reference(ecp_hash: str, year: int) -> str:
    """Generates a Base32 encoded, encrypted payment reference from the lower half of an ECP hash and a year."""
    lower_half_hash = ecp_hash[len(ecp_hash)//2:]
    plaintext = f"{lower_half_hash}:{year}"
    encrypted_bytes = _encrypt_symmetric(plaintext)
    return base64.b32encode(encrypted_bytes).decode('utf-8') if encrypted_bytes else None

def parse_payment_reference(reference: str) -> tuple[str, int] | None:
    """Parses a payment reference to get the lower half of the ECP hash and the year."""
    encrypted_bytes = base64.b32decode(reference.encode('utf-8'))
    decrypted_text = _decrypt_symmetric(encrypted_bytes)
    if decrypted_text and ':' in decrypted_text:
        parts = decrypted_text.split(':', 1)
        return parts[0], int(parts[1])
    return None

def encrypt_fee_reference(ecp_hash: str, year: int) -> str:
    """Encrypts the ECP hash and year for the fee reference."""
    data = f"{ecp_hash}:{year}"
    return _encrypt_data(data)

def decrypt_fee_reference(reference: str) -> tuple[str, int]:
    """Decrypts the fee reference and returns the ECP hash and year."""
    decrypted = _decrypt_data(reference)
    if decrypted:
        parts = decrypted.split(":")
        return parts[0], int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else None
    return None, None
    
def create_check_hash():
    random_bytes = os.urandom(24)
    mac_full = hmac.new(secret_manager.get_secret("crypt_key").encode('utf-8'), random_bytes, hashlib.sha256).digest()
    mac = mac_full[:16]
    combined = random_bytes + mac
    encoded = base64.b32encode(combined).decode('utf-8')
    return encoded

def verify_check_hash(check_hash):
    try:
        combined = base64.b32decode(check_hash)
        if len(combined) != 40:
            return False
        random_bytes = combined[:24]
        mac_provided = combined[24:]
        expected_mac = hmac.new(secret_manager.get_secret("crypt_key").encode('utf-8'), random_bytes, hashlib.sha256).digest()[:16]
        return hmac.compare_digest(mac_provided, expected_mac)
    except Exception:
        return False

def generate_qr_code(data, logo_path):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    
    # Add logo to the center of the QR code
    if os.path.exists(logo_path):
        from PIL import Image
        logo = Image.open(logo_path)
        logo = logo.resize((img.size[0] // 4, img.size[1] // 4))
        pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
        img.paste(logo, pos, logo if logo.mode == 'RGBA' else None)
    
    return img

def parse_camt053(xml_file):
    """Parses a camt.053 XML file and extracts relevant data."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file}: {e}")
        return {'statement_iban': None, 'transactions': [], 'error': f"XML Parse Error: {e}"}

    # Define common namespaces - camt.053 can have different versions
    # Attempt to find the namespace dynamically or use a common one.
    # For simplicity, we'll try a common pattern. More robust parsing might need to inspect the root tag.
    ns_map = {'bk': root.tag.split('}')[0][1:] if '}' in root.tag else 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'}
    
    stmt_iban_element = root.find('.//bk:Stmt/bk:Acct/bk:Id/bk:IBAN', ns_map)
    statement_iban = stmt_iban_element.text if stmt_iban_element is not None else None

    transactions = []
    for entry in root.findall('.//bk:Ntry', ns_map):
        credit_debit_indicator_el = entry.find('bk:CdtDbtInd', ns_map)
        if credit_debit_indicator_el is None or credit_debit_indicator_el.text != 'CRDT':
            continue # Skip non-credit entries

        amount_el = entry.find('bk:Amt', ns_map)
        amount = amount_el.text if amount_el is not None else '0'
        currency = amount_el.attrib.get('Ccy', '') if amount_el is not None else ''

        bookg_dt_el = entry.find('.//bk:BookgDt/bk:Dt', ns_map)
        transaction_date = bookg_dt_el.text if bookg_dt_el is not None else None

        ntry_ref_el = entry.find('bk:NtryRef', ns_map)
        transaction_reference = ntry_ref_el.text if ntry_ref_el is not None else None

        # Extract payer's reference (potential ecp_hash)
        # Prefer Unstructured Remittance, then EndToEndId
        ecp_hash_candidate = None
        ustrd_el = entry.find('.//bk:RmtInf/bk:Ustrd', ns_map)
        if ustrd_el is not None and ustrd_el.text:
            ecp_hash_candidate = ustrd_el.text.strip()
        else:
            e2e_id_el = entry.find('.//bk:Refs/bk:EndToEndId', ns_map)
            if e2e_id_el is not None and e2e_id_el.text:
                ecp_hash_candidate = e2e_id_el.text.strip()

        # Extract payer's IBAN
        debtor_iban_el = entry.find('.//bk:RltdPties/bk:DbtrAcct/bk:Id/bk:IBAN', ns_map)
        debtor_account_iban = debtor_iban_el.text if debtor_iban_el is not None else None

        transactions.append({
            'ecp_hash_candidate': ecp_hash_candidate,
            'amount': amount,
            'currency': currency,
            'transaction_date': transaction_date,
            'transaction_reference': transaction_reference,
            'debtor_account_iban': debtor_account_iban
        })
    return {'statement_iban': statement_iban, 'transactions': transactions, 'error': None}

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
_ICON_CACHE = {} # Simple cache for QPixmap objects

def _get_scaled_pixmap_from_cache(pix_file_name: str, target_size: int) -> QPixmap:
    """Loads or returns a scaled QPixmap from the cache."""
    cache_key = (pix_file_name, target_size)
    if cache_key not in _ICON_CACHE:
        pixmap_path = os.path.join(ICON_FOLDER, pix_file_name)
        pix = QPixmap(pixmap_path)
        if not pix.isNull():
            _ICON_CACHE[cache_key] = pix.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            _ICON_CACHE[cache_key] = None # Or return a transparent placeholder if the icon does not exist
    return _ICON_CACHE[cache_key]

def get_icon(icon_name: str) -> QIcon:
    icon_path = os.path.join(ICON_FOLDER, icon_name)
    if os.path.exists(icon_path):
        return QIcon(icon_path)

# For type annotations, we will use strings (forward references) to avoid import problems
# during program execution if `from __future__ import annotations` is not used.
def get_state_pixmap(member: 'Member', club: 'Club') -> QPixmap:
    IMAGE_SIZE = 20 # Renamed constant, Enlarged for better visibility, originally 16 in main_window legend

    image_files = []


    if member.primary_club_id != club.club_id:
        icon_filename = "caver_yellow.png"
    else: # Is in the primary club or it is their primary club
        member_status = member.status # Assuming translated attribute
        if member_status == "active": # Value "aktivny" might also need translation if it's a controlled vocabulary
            icon_filename = "caver_green.png"
        elif member_status == "inactive":
            icon_filename = "caver_gray_inv.png"
        elif member_status == "applicant":
            icon_filename = "caver_gray_dark.png"
    
    if club.president_id is not None \
        and member.member_id == club.president_id \
        and member.primary_club_id == club.club_id: # President of their primary club, assuming translated attributes
        icon_filename = "caver_gold.png"
    
    if member.status == "zblocked": # Blocked has priority, assuming translated attribute
        icon_filename = "caver_baned.png"

    if member.status is None: # Assuming translated attribute
        image_files = ["caver_black.png"]
    else: 
        image_files = [icon_filename]

        if member.discounted_membership: # Assuming translated attribute
            image_files.append("star_icon.png")

        if not member.has_paid_fee(): # Assuming translated method
            image_files.append("exclamation_icon.png")
    
        if member.ecp_hash: # Assuming translated attribute
            image_files.append("wallet-icon_72.png")

    # Creating a composite icon
    # Each additional icon will have the full width of IMAGE_SIZE
    total_width = len(image_files) * IMAGE_SIZE
    composite = QPixmap(total_width, IMAGE_SIZE)
    composite.fill(Qt.transparent) # Transparent background

    painter = QPainter(composite)

    # We draw the additional icons next to each other, behind the base icon
    current_x = 0
    for pix_file in image_files:
        scaled_pix = _get_scaled_pixmap_from_cache(pix_file, IMAGE_SIZE)
        if scaled_pix: # If scaled_pix is None (icon not found/loaded), we skip drawing
            painter.drawPixmap(current_x, 0, scaled_pix)
        current_x += IMAGE_SIZE

    painter.end()
    return composite

def upload_to_bucket(blob_name: str, data: bytes, content_type: str) -> str:
    """Uploads data to GCS and returns the public URL."""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secret_manager.get_secret("credentials_json")
    project_id = secret_manager.get_secret("project_id")
    bucket_name = secret_manager.get_secret("bucket_name")

    if not all([project_id, bucket_name, secret_manager.get_secret("credentials_json")]):
        print("GCS config missing (project_id, bucket_name, or credentials_json). Cannot upload.")
        return None

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    blob = bucket.blob(blob_name)
    try:
        blob.upload_from_string(data, content_type=content_type)
        blob.make_public() # Ensure the blob is publicly readable
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        print(f"File {blob_name} uploaded to {bucket_name}. Public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error uploading {blob_name} to bucket {bucket_name}: {e}")
        return None

def delete_object_from_bucket_by_url(gcs_url: str):
    """Deletes an object from GCS given its public URL."""
    if not gcs_url or not gcs_url.startswith("https://storage.googleapis.com/"):
        print(f"Invalid GCS URL for deletion: {gcs_url}")
        return

    expected_bucket_name = secret_manager.get_secret("bucket_name")
    try:
        path_parts = gcs_url.split(f"https://storage.googleapis.com/", 1)[1].split('/', 1)
        bucket_name_from_url = path_parts[0]
        blob_name = path_parts[1]

        if bucket_name_from_url != expected_bucket_name:
            print(f"Skipping deletion: URL bucket '{bucket_name_from_url}' does not match configured bucket '{expected_bucket_name}'.")
            return

        # Re-use upload_to_bucket's setup for client, or make a common GCS client getter
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secret_manager.get_secret("credentials_json")
        client = storage.Client(project=secret_manager.get_secret("project_id"))
        bucket = client.bucket(bucket_name_from_url)
        blob = bucket.blob(blob_name)
        
        if blob.exists(): # Check if blob exists before trying to delete
            blob.delete()
            print(f"Object '{blob_name}' deleted from bucket '{bucket_name_from_url}'.")
        else:
            print(f"Object '{blob_name}' not found in bucket '{bucket_name_from_url}' for deletion.")
    except Exception as e:
        print(f"Error deleting object from URL {gcs_url}: {e}")

def get_table_header_stylesheet() -> str:
    """Returns the stylesheet for dark table headers."""
    return """
        QHeaderView::section {
            background-color: #011F4B; /* Dark gray background */
            color: white;              /* White text */
            padding: 1px;              /* Inner margin for text */
            border: 1px solid #B3CDE0; /* Subtle border around each header section */
        }
    """

def _get_main_window_instance() -> QMainWindow:
    """Helper to find the QMainWindow instance."""
    app = QApplication.instance()
    if not app:
        return None
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None

def _set_status_message(message: str, background_color: str, text_color: str = "white", duration: int = 5000):
    """
    Internal function to display a message in the status bar with a specified background color.
    Automatically finds the main application window.
    """
    main_window_instance = _get_main_window_instance()

    if not main_window_instance or not hasattr(main_window_instance, 'status_bar'):
        print(f"Error: MainWindow instance or status_bar not provided for message: {message}")
        return

    status_bar = main_window_instance.status_bar
    original_stylesheet = status_bar.styleSheet()
    new_style = f"QStatusBar {{ background-color: {background_color}; color: {text_color}; border-top: 1px solid #B0B0B0; }} QStatusBar::item {{ border: none; }}"
    
    status_bar.setStyleSheet(new_style)
    status_bar.showMessage(message, duration)

    QTimer.singleShot(duration, lambda: status_bar.setStyleSheet(original_stylesheet))

def show_success_message(message: str, duration: int = 15000):
    """Displays a success message (green background)."""
    _set_status_message(message, background_color="#4CAF50", text_color="white", duration=duration)

def show_warning_message(message: str, duration: int = 15000):
    """Displays a warning message (orange background)."""
    _set_status_message(message, background_color="#FF9800", text_color="black", duration=duration)

def show_error_message(message: str, duration: int = 15000):
    """Displays an error message (red background)."""
    _set_status_message(message, background_color="#F44336", text_color="white", duration=duration)

def show_info_message(message: str, duration: int = 15000):
    """Displays an informational message (blue background)."""
    _set_status_message(message, background_color="#2196F3", text_color="white", duration=duration)

def get_preferred_country_code() -> str:
    if _app_config_cache is None:
        print("WARNING: App config not loaded. Call load_all_configs() at startup.")
        return 'SK' # Fallback
    return _app_config_cache.get('DEFAULT', 'preferred_country', fallback='SK').upper()

def get_preferred_language() -> str:
    if _app_config_cache is None:
        print("WARNING: App config not loaded. Call load_all_configs() at startup.")
        return 'sk_SK' # Fallback
    return _app_config_cache.get('DEFAULT', 'preferred_language', fallback='en_US')

def get_world_countries(locale_identifier: str = None) -> list[tuple[str, str]]:
    """
    Returns a list of (localized_country_name, country_code) tuples using Babel.
    Filters for 2-letter country codes and sorts by localized name.
    """
    if locale_identifier is None:
        locale_identifier = get_preferred_language()

    try:
        locale = Locale.parse(locale_identifier)
        if locale is None or locale.territories is None: # Additional check
             print(f"Warning: Could not get territories for locale '{locale_identifier}'. Returning empty list.")
             return []
        
        countries = []
        for code, name in locale.territories.items():
            # We only include standard 2-letter country codes
            # and omit codes for regions, continents, etc. (e.g., 'ZZ', 'EU', 'EZ', 'UN', 'QO')
            # and also codes that do not have a valid name in the given locale (Babel might return the code as the name)
            if len(code) == 2 and code.isalpha() and code.upper() != name:
                countries.append((name, code.upper()))
        
        # Sort by localized country name
        countries.sort(key=lambda x: x[0])
        return countries
    except UnknownLocaleError:
        print(f"Error: Locale '{locale_identifier}' is unknown to Babel. Returning empty list.")
        return []
    except Exception as e:
        print(f"Error fetching countries from Babel for locale '{locale_identifier}': {e}. Returning empty list.")
        return []

def save_app_settings(
    preferred_country_code: str,
    preferred_language: str,
    membership_currency: str,
    membership_fee_normal: str, # Store as string, convert on use
    membership_fee_discounted: str, # Store as string
    membership_valid_until_month: str, # Store as string
    membership_valid_until_day: str, # Store as string
    membership_renewal_window_days: str, # Store as string
    iban: str
) -> bool:
    """Saves application settings to the config file."""
    global _app_config_cache
    if _app_config_cache is None:
        load_all_configs() # Ensure config is loaded

    _app_config_cache['DEFAULT']['preferred_country'] = preferred_country_code.upper()
    _app_config_cache['DEFAULT']['preferred_language'] = preferred_language
    _app_config_cache['DEFAULT']['membership_currency'] = membership_currency.upper()
    _app_config_cache['DEFAULT']['membership_fee_normal'] = membership_fee_normal
    _app_config_cache['DEFAULT']['membership_fee_discounted'] = membership_fee_discounted
    _app_config_cache['DEFAULT']['membership_valid_until_month'] = membership_valid_until_month
    _app_config_cache['DEFAULT']['membership_valid_until_day'] = membership_valid_until_day
    _app_config_cache['DEFAULT']['membership_renewal_window_days'] = membership_renewal_window_days
    _app_config_cache['DEFAULT']['iban'] = iban.strip().upper()

    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as configfile:
            _app_config_cache.write(configfile)
        print(f"INFO: Application settings saved to '{CONFIG_FILE_PATH}'.")
        return True
    except IOError as e:
        print(f"ERROR: Could not write application settings to '{CONFIG_FILE_PATH}': {e}")
        return False

def get_supported_locales_display() -> dict:
    """Returns a dictionary of supported locales and their display names."""
    if _supported_locales_cache is None:
        load_all_configs() # Ensure config is loaded if it hasn't been already
    if _supported_locales_cache and _supported_locales_cache.has_section('Locales'):
        return dict(_supported_locales_cache.items('Locales'))
    return {} # Return empty dict if loading fails or section is missing

# Getters for new membership settings
def get_membership_currency() -> str:
    if _app_config_cache is None: load_all_configs()
    return _app_config_cache.get('DEFAULT', 'membership_currency', fallback='EUR')

def get_membership_fee_normal() -> float:
    if _app_config_cache is None: load_all_configs()
    try:
        return float(_app_config_cache.get('DEFAULT', 'membership_fee_normal', fallback='20.00'))
    except ValueError:
        return 20.00 # Fallback on conversion error

def get_membership_fee_discounted() -> float:
    if _app_config_cache is None: load_all_configs()
    try:
        return float(_app_config_cache.get('DEFAULT', 'membership_fee_discounted', fallback='10.00'))
    except ValueError:
        return 10.00 # Fallback on conversion error

def get_membership_valid_until_month() -> int:
    if _app_config_cache is None: load_all_configs()
    try:
        return int(_app_config_cache.get('DEFAULT', 'membership_valid_until_month', fallback='12'))
    except ValueError:
        return 12 # Fallback

def get_membership_valid_until_day() -> int:
    if _app_config_cache is None: load_all_configs()
    try:
        return int(_app_config_cache.get('DEFAULT', 'membership_valid_until_day', fallback='31'))
    except ValueError:
        return 31 # Fallback

def get_membership_renewal_window_days() -> int:
    if _app_config_cache is None: load_all_configs()
    try:
        return int(_app_config_cache.get('DEFAULT', 'membership_renewal_window_days', fallback='90'))
    except ValueError:
        return 90 # Fallback

def get_iban() -> str:
    if _app_config_cache is None: load_all_configs()
    return _app_config_cache.get('DEFAULT', 'iban', fallback='')