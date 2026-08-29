# config.py
import io
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import configparser
from cryptography.hazmat.primitives import padding

from app_paths import ensure_config_dir, resolve_config_file

SECRETS_FILENAME = "secrets.properties"
APP_CONFIG_FILENAME = "config.properties"


class SecretManager:
    def __init__(self, properties_file=None):
        # Defaults to config/secrets.properties, migrating a legacy root-level
        # file on first use so existing installations keep their PIN/secrets.
        self.properties_file = properties_file or resolve_config_file(SECRETS_FILENAME)
        self.secrets = {}
        self.pin = None
        self.salt = None

    def _decrypt_to_dict(self, pin):
        """Decrypt the properties file with ``pin`` and return (secrets, salt).

        Raises on any failure; callers decide how to report it.
        """
        with open(self.properties_file, "rb") as f:
            encrypted_data = f.read()

        # Extract salt and encrypted data
        salt_length = int.from_bytes(encrypted_data[:4], byteorder='big')
        salt = encrypted_data[4:4 + salt_length]
        encrypted_data = encrypted_data[4 + salt_length:]

        key = self.derive_key(pin, salt)
        decrypted_data = self.decrypt(encrypted_data, key)

        # Load decrypted data into configparser
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(decrypted_data.decode("utf-8"))

        return dict(config.items("DEFAULT")), salt

    def decrypt_file(self, pin):
        self.pin = pin
        try:
            self.secrets, self.salt = self._decrypt_to_dict(pin)
            return True
        except Exception as e:
            print(f"Chyba pri dešifrovaní: {e}")
            return False

    def verify_pin(self, pin):
        """Check ``pin`` against the stored file without touching current state.

        Used before sensitive actions (e.g. exporting plaintext secrets) so a
        re-authentication cannot discard unsaved edits held in the UI.
        """
        if not pin:
            return False
        try:
            self._decrypt_to_dict(pin)
            return True
        except Exception:
            return False

    def derive_key(self, pin, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=65536,
            backend=default_backend()
        )
        key = kdf.derive(pin.encode("utf-8"))
        return key

    def decrypt(self, encrypted_data, key):
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]

        cipher = Cipher(algorithms.AES(key), mode=modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
        return unpadded_data

    def get_secret(self, secret_name):
        return self.secrets.get(secret_name)

    def encrypt_and_save_file(self, secrets, pin):
        try:
            self.salt = os.urandom(16)
            key = self.derive_key(pin, self.salt)

            # Create configparser object and add secrets
            config = configparser.ConfigParser(interpolation=None)
            config["DEFAULT"] = secrets

            # Serialize configparser to an in-memory buffer so plaintext
            # secrets are never written to disk unencrypted.
            buffer = io.StringIO()
            config.write(buffer)
            config_string = buffer.getvalue()

            encrypted_data = self.encrypt(config_string.encode("utf-8"), key)

            # Prepend salt length and salt to encrypted data
            salt_length = len(self.salt).to_bytes(4, byteorder='big')
            data_to_save = salt_length + self.salt + encrypted_data

            parent_dir = os.path.dirname(os.path.abspath(self.properties_file))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(self.properties_file, "wb") as f:
                f.write(data_to_save)

            self.secrets = dict(secrets)
            return True
        except Exception as e:
            print(f"Error encrypting and saving secrets: {e}")
            return False

    def encrypt(self, data, key):
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), mode=modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        combined = iv + ciphertext
        return combined

    def get_logo_url(self): # Name is already English
        return f"https://storage.googleapis.com/{self.secrets.get('bucket_name')}/{self.secrets.get('logo_pic')}"


# Function to quickly get the language without initializing the entire application
def get_preferred_language():
    """Reads preferred language directly from config file for early app setup."""
    config = configparser.ConfigParser(interpolation=None)
    app_config_path = resolve_config_file(APP_CONFIG_FILENAME)
    if os.path.exists(app_config_path):
        config.read(app_config_path, encoding='utf-8')
        return config.get('DEFAULT', 'preferred_language', fallback='en_US')
    return 'en_US' # Fallback if the file does not exist


# Create a global instance of SecretManager
secret_manager = SecretManager()
