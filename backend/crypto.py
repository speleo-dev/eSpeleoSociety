import base64
import hashlib
import hmac
import os


def make_check_hash_factory(get_secret):
    def create_check_hash():
        random_bytes = os.urandom(24)
        secret = (get_secret("crypt_key") or "").encode("utf-8")
        mac = hmac.new(secret, random_bytes, hashlib.sha256).digest()[:16]
        return base64.b32encode(random_bytes + mac).decode("utf-8")

    return create_check_hash
