# config.py
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import configparser
from cryptography.hazmat.primitives import padding

class SecretManager:
    def __init__(self, properties_file="secrets.properties"):
        self.properties_file = properties_file
        self.secrets = {}
        self.pin = None
        self.salt = None

    def decrypt_file(self, pin):
        self.pin = pin
        try:
            with open(self.properties_file, "rb") as f:
                encrypted_data = f.read()

            # Extract salt and encrypted data
            salt_length = int.from_bytes(encrypted_data[:4], byteorder='big')
            self.salt = encrypted_data[4:4 + salt_length]
            encrypted_data = encrypted_data[4 + salt_length:]

            key = self.derive_key(pin, self.salt)
            decrypted_data = self.decrypt(encrypted_data, key)

            # Load decrypted data into configparser
            config = configparser.ConfigParser()
            config.read_string(decrypted_data.decode("utf-8"))

            # Extract secrets
            self.secrets = dict(config.items("DEFAULT"))

            return True
        except Exception as e:
            print(f"Chyba pri dešifrovaní: {e}")
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
            config = configparser.ConfigParser()
            config["DEFAULT"] = secrets

            # Serialize configparser to string
            config_string = ""
            with open("temp.properties", "w") as configfile:
                config.write(configfile)
            with open("temp.properties", "r") as configfile:
                config_string = configfile.read()
            os.remove("temp.properties")

            encrypted_data = self.encrypt(config_string.encode("utf-8"), key)

            # Prepend salt length and salt to encrypted data
            salt_length = len(self.salt).to_bytes(4, byteorder='big')
            data_to_save = salt_length + self.salt + encrypted_data

            with open(self.properties_file, "wb") as f:
                f.write(data_to_save)
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
    config = configparser.ConfigParser()
    if os.path.exists('config.properties'):
        config.read('config.properties', encoding='utf-8')
        return config.get('DEFAULT', 'preferred_language', fallback='en_US')
    return 'en_US' # Fallback if the file does not exist

# Create a global instance of SecretManager
secret_manager = SecretManager()
