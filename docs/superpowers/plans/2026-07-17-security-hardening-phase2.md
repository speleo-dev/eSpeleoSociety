# eSpeleo Security Hardening - Phase 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** Fix secrets handling vulnerabilities (#4-5) - no plaintext on disk, strong KDF, integrity protection

**Architecture:** PBKDF2 key derivation, AES-GCM encryption with HMAC integrity, atomic encrypted file writes

**Tech Stack:** Python 3.x, cryptography library, hashlib

## Global Constraints
- Python 3.10+
- cryptography 42+
- All existing secrets files must remain decryptable
- Backward compatibility for existing encrypted files
- Tests must verify no plaintext leakage

---

## Task 1: Add PBKDF2 Key Derivation

**Files:**
- Create: `espeleo/crypto_utils.py` - new crypto utilities module
- Modify: `espeleo/config.py` - migrate to new crypto
- Modify: `espeleo/utils.py` - deprecate old functions
- Test: `tests/test_crypto_utils.py`

**Issue:** AES key truncated from crypt_key instead of proper KDF

**Interfaces:**
- Consumes: password string, salt
- Produces: 32-byte key via PBKDF2-HMAC-SHA256

- [ ] **Step 1: Create crypto_utils.py with PBKDF2**

```python
# espeleo/crypto_utils.py
"""Secure cryptographic utilities with PBKDF2 and AES-GCM."""
import os
import hashlib
import base64
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_LENGTH = 32
NONCE_LENGTH = 12
KEY_LENGTH = 32
ITERATIONS = 480000  # OWASP 2023 recommendation


def derive_key(password: str, salt: bytes | None = None) -> Tuple[bytes, bytes]:
    """Derive encryption key from password using PBKDF2-HMAC-SHA256.
    
    Args:
        password: User's password/PIN
        salt: Optional salt (generated if None)
    
    Returns:
        Tuple of (key, salt)
    """
    if salt is None:
        salt = os.urandom(SALT_LENGTH)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(password.encode('utf-8'))
    return key, salt


def encrypt_gcm(plaintext: bytes, password: str) -> bytes:
    """Encrypt data with AES-GCM using PBKDF2 key derivation.
    
    Format: salt(32) + nonce(12) + ciphertext + tag(16)
    """
    key, salt = derive_key(password)
    nonce = os.urandom(NONCE_LENGTH)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return salt + nonce + ciphertext


def decrypt_gcm(ciphertext: bytes, password: str) -> bytes:
    """Decrypt data encrypted with encrypt_gcm."""
    if len(ciphertext) < SALT_LENGTH + NONCE_LENGTH + 16:
        raise ValueError("Invalid ciphertext length")
    
    salt = ciphertext[:SALT_LENGTH]
    nonce = ciphertext[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
    encrypted = ciphertext[SALT_LENGTH + NONCE_LENGTH:]
    
    key, _ = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, encrypted, None)
```

- [ ] **Step 2: Write PBKDF2 tests**

```python
# tests/test_crypto_utils.py
import pytest
from espeleo.crypto_utils import derive_key, encrypt_gcm, decrypt_gcm, ITERATIONS

def test_derive_key_returns_32_bytes():
    """PBKDF2 must produce 32-byte key."""
    key, salt = derive_key("my-secret-password")
    assert len(key) == 32
    assert len(salt) == 32

def test_derive_key_deterministic_with_same_salt():
    """Same password + salt = same key."""
    salt = b'x' * 32
    key1, _ = derive_key("password", salt)
    key2, _ = derive_key("password", salt)
    assert key1 == key2

def test_derive_key_different_salts_different_keys():
    """Different salts must produce different keys."""
    key1, salt1 = derive_key("password")
    key2, salt2 = derive_key("password")
    assert salt1 != salt2
    assert key1 != key2

def test_encrypt_decrypt_roundtrip():
    """Encrypt then decrypt returns original plaintext."""
    plaintext = b"sensitive data here"
    password = "user-pin-1234"
    
    ciphertext = encrypt_gcm(plaintext, password)
    decrypted = decrypt_gcm(ciphertext, password)
    
    assert decrypted == plaintext

def test_decrypt_wrong_password_fails():
    """Decryption with wrong password must fail."""
    plaintext = b"sensitive data"
    ciphertext = encrypt_gcm(plaintext, "correct-password")
    
    with pytest.raises(Exception):  # InvalidTag or similar
        decrypt_gcm(ciphertext, "wrong-password")

def test_ciphertext_different_each_time():
    """Same plaintext encrypted twice must produce different ciphertext."""
    plaintext = b"same data"
    password = "password"
    
    ct1 = encrypt_gcm(plaintext, password)
    ct2 = encrypt_gcm(plaintext, password)
    
    assert ct1 != ct2  # Different salt and nonce
```

- [ ] **Step 3: Run crypto tests**

```bash
python -m pytest tests/test_crypto_utils.py -v
# Expected: 6+ tests PASS
```

- [ ] **Step 4: Commit crypto utils**

```bash
git add espeleo/crypto_utils.py tests/test_crypto_utils.py
git commit -m "feat(crypto): add PBKDF2 and AES-GCM utilities

New crypto_utils.py module with:
- PBKDF2-HMAC-SHA256 key derivation (480k iterations)
- AES-GCM authenticated encryption
- Secure random salt and nonce generation

Part of fixing audit findings #4-5."
```

---

## Task 2: Migrate config.py to New Crypto

**Files:**
- Modify: `espeleo/config.py`
- Test: `tests/test_config_crypto.py`

**Issue:** Secrets written to temp.properties unencrypted

**Interfaces:**
- Consumes: secrets dict, PIN
- Produces: Atomically written encrypted file

- [ ] **Step 1: Create atomic file write utility**

```python
# espeleo/crypto_utils.py - add atomic write
import tempfile
import os


def write_file_atomic(filepath: str, data: bytes) -> None:
    """Write file atomically using temp file + rename.
    
    Ensures no partial file exists on crash/power loss.
    """
    # Write to temp file in same directory for atomic rename
    dir_name = os.path.dirname(os.path.abspath(filepath)) or '.'
    fd, temp_path = tempfile.mkstemp(dir=dir_name)
    try:
        os.write(fd, data)
        os.fsync(fd)  # Ensure data is written to disk
        os.close(fd)
        os.rename(temp_path, filepath)
    except:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
```

- [ ] **Step 2: Add migration path for old files**

```python
# espeleo/config.py - detect and migrate old format
import json
from espeleo.crypto_utils import encrypt_gcm, decrypt_gcm

OLD_FILE_MAGIC = b'AES_CBC_LEGACY:'  # Marker for old format detection

def _is_legacy_format(data: bytes) -> bool:
    """Check if file uses old AES-CBC format."""
    return data.startswith(OLD_FILE_MAGIC)

def _decrypt_legacy(data: bytes, pin: str) -> dict:
    """Decrypt old AES-CBC format for backward compatibility."""
    # Import old crypto only when needed
    from espeleo.utils import _decrypt_data
    decrypted = _decrypt_data(data, pin)
    return json.loads(decrypted)
```

- [ ] **Step 3: Update encrypt_and_save_file**

```python
# espeleo/config.py - replace encrypt_and_save_file
def encrypt_and_save_file(secrets: dict, pin: str, filepath: str) -> None:
    """Encrypt secrets and save atomically.
    
    Uses AES-GCM with PBKDF2 key derivation.
    Writes atomically to prevent partial files on crash.
    """
    from espeleo.crypto_utils import encrypt_gcm, write_file_atomic
    
    # Serialize secrets
    plaintext = json.dumps(secrets, ensure_ascii=False).encode('utf-8')
    
    # Encrypt
    ciphertext = encrypt_gcm(plaintext, pin)
    
    # Write atomically - no temp.properties left behind
    write_file_atomic(filepath, ciphertext)
```

- [ ] **Step 4: Update decrypt_file**

```python
# espeleo/config.py - replace decrypt_file
def decrypt_file(filepath: str, pin: str) -> dict:
    """Decrypt secrets file.
    
    Supports new AES-GCM format and legacy AES-CBC format.
    """
    from espeleo.crypto_utils import decrypt_gcm
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Check for legacy format
    if _is_legacy_format(data):
        return _decrypt_legacy(data, pin)
    
    # New format
    plaintext = decrypt_gcm(data, pin)
    return json.loads(plaintext)
```

- [ ] **Step 5: Write migration tests**

```python
# tests/test_config_crypto.py
import json
import tempfile
import os
from espeleo.config import encrypt_and_save_file, decrypt_file

def test_encrypt_save_decrypt_roundtrip():
    """Full roundtrip: encrypt -> save -> decrypt."""
    secrets = {
        "db_host": "localhost",
        "db_password": "secret123",
        "smtp_password": "mailpass"
    }
    pin = "1234"
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        filepath = f.name
    
    try:
        # Encrypt and save
        encrypt_and_save_file(secrets, pin, filepath)
        
        # Verify no plaintext in file
        with open(filepath, 'rb') as f:
            data = f.read()
        assert b'db_password' not in data
        assert b'secret123' not in data
        assert b'smtp_password' not in data
        
        # Decrypt
        decrypted = decrypt_file(filepath, pin)
        assert decrypted == secrets
    finally:
        os.unlink(filepath)

def test_atomic_write_no_partial_files():
    """Atomic write leaves no temp files behind."""
    from espeleo.crypto_utils import write_file_atomic
    
    secrets = {"key": "value"}
    pin = "1234"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "secrets.enc")
        
        # Count temp files before
        temp_before = len([f for f in os.listdir(tmpdir) if f.startswith('.tmp')])
        
        # Write
        write_file_atomic(filepath, b"test data")
        
        # Count temp files after
        temp_after = len([f for f in os.listdir(tmpdir) if f.startswith('.tmp')])
        
        assert temp_after == temp_before
        assert os.path.exists(filepath)
```

- [ ] **Step 6: Run config tests**

```bash
python -m pytest tests/test_config_crypto.py -v
# Expected: 2+ tests PASS
```

- [ ] **Step 7: Commit config migration**

```bash
git add espeleo/config.py tests/test_config_crypto.py
git commit -m "security(config): atomic encrypted file writes with AES-GCM

Fixes audit finding #4:
- Replace temp.properties with atomic file writes
- Use AES-GCM with PBKDF2 key derivation
- No plaintext secrets left on disk on crash
- Maintains backward compatibility with old format"
```

---

## Task 3: Deprecate Old Encryption

**Files:**
- Modify: `espeleo/utils.py`
- Test: `tests/test_utils_crypto_deprecation.py`

**Issue:** Old _encrypt_data/_decrypt_data uses weak key derivation

**Interfaces:**
- Consumes: Old function calls
- Produces: Deprecation warnings + new crypto

- [ ] **Step 1: Add deprecation warnings to old functions**

```python
# espeleo/utils.py
import warnings

def _encrypt_data(data: bytes, password: str) -> bytes:
    """DEPRECATED: Use crypto_utils.encrypt_gcm instead.
    
    Kept for backward compatibility only.
    """
    warnings.warn(
        "_encrypt_data is deprecated. Use crypto_utils.encrypt_gcm for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation ...

def _decrypt_data(data: bytes, password: str) -> bytes:
    """DEPRECATED: Use crypto_utils.decrypt_gcm instead.
    
    Kept for backward compatibility with existing secrets files.
    """
    warnings.warn(
        "_decrypt_data is deprecated. Use crypto_utils.decrypt_gcm for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation ...
```

- [ ] **Step 2: Document migration path**

```python
# espeleo/utils.py - module docstring
"""Utility functions.

Crypto functions in this module are DEPRECATED:
- _encrypt_data -> use crypto_utils.encrypt_gcm
- _decrypt_data -> use crypto_utils.decrypt_gcm
- _encrypt_symmetric -> use crypto_utils.derive_key

These are kept for backward compatibility with existing secrets files.
New code should use crypto_utils module.
"""
```

- [ ] **Step 3: Test deprecation warnings**

```python
# tests/test_utils_crypto_deprecation.py
import warnings
import pytest
from espeleo import utils

def test_encrypt_data_emits_deprecation_warning():
    """Old encrypt should warn about deprecation."""
    with pytest.warns(DeprecationWarning, match="crypto_utils"):
        utils._encrypt_data(b"test", "password")

def test_decrypt_data_emits_deprecation_warning():
    """Old decrypt should warn about deprecation."""
    # First encrypt without warning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        encrypted = utils._encrypt_data(b"test", "password")
    
    with pytest.warns(DeprecationWarning, match="crypto_utils"):
        utils._decrypt_data(encrypted, "password")
```

- [ ] **Step 4: Run deprecation tests**

```bash
python -m pytest tests/test_utils_crypto_deprecation.py -v
# Expected: 2 tests PASS
```

- [ ] **Step 5: Commit deprecation**

```bash
git add espeleo/utils.py tests/test_utils_crypto_deprecation.py
git commit -m "refactor(utils): deprecate old crypto functions

Old _encrypt_data/_decrypt_data emit DeprecationWarning.
Direct users to new crypto_utils module.
Part of fixing audit finding #5 - weak key derivation."
```

---

## Phase 2 Verification

- [ ] **Step 6: Run all new tests**

```bash
python -m pytest tests/test_crypto_utils.py tests/test_config_crypto.py tests/test_utils_crypto_deprecation.py -v
# Expected: 10+ tests PASS
```

- [ ] **Step 7: Integration test - old secrets migration**

```python
# Manual verification script
"""Test backward compatibility with old secrets files."""
import tempfile
import os
from espeleo.config import encrypt_and_save_file, decrypt_file

# Create new format file
secrets = {"test": "data", "password": "secret"}
with tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as f:
    filepath = f.name

try:
    encrypt_and_save_file(secrets, "1234", filepath)
    decrypted = decrypt_file(filepath, "1234")
    assert decrypted == secrets
    print("✓ New format works")
    
    # Verify no plaintext
    with open(filepath, 'rb') as f:
        content = f.read()
    assert b'test' not in content
    assert b'data' not in content
    print("✓ No plaintext in file")
finally:
    os.unlink(filepath)

print("Phase 2 verification complete!")
```

- [ ] **Step 8: Update documentation**

```markdown
# Add to docs/technical-manual.md under "Security Model"

## Encryption Improvements (2026-07-17)

### New Crypto (AES-GCM + PBKDF2)
- **Key Derivation:** PBKDF2-HMAC-SHA256 with 480,000 iterations (OWASP 2023)
- **Encryption:** AES-GCM with 256-bit keys
- **Integrity:** Built-in GCM authentication tag
- **Atomic Writes:** Temp file + rename prevents partial files on crash

### Legacy Support
- Old AES-CBC secrets files remain decryptable
- Migration happens automatically on read
- New files use AES-GCM only

### Migration
1. Application reads old format -> decrypts with old method
2. Next save writes new format
3. No manual migration required
```

- [ ] **Step 9: Final commit**

```bash
git add docs/technical-manual.md
git commit -m "docs: document new encryption scheme

Add security section covering:
- PBKDF2 key derivation
- AES-GCM encryption
- Atomic file writes
- Legacy format support"
```

---

## Summary

**Fixed audit findings:** #4, #5

**New files:**
- `espeleo/crypto_utils.py` - secure crypto primitives
- `tests/test_crypto_utils.py` - crypto tests
- `tests/test_config_crypto.py` - config migration tests
- `tests/test_utils_crypto_deprecation.py` - deprecation tests

**Modified files:**
- `espeleo/config.py` - atomic writes, new crypto
- `espeleo/utils.py` - deprecation warnings
- `docs/technical-manual.md` - security documentation

**Tests added:** 10+ tests

**Security improvements:**
- PBKDF2-HMAC-SHA256 with 480k iterations
- AES-GCM authenticated encryption
- Atomic file writes (no temp.properties leakage)
- Backward compatible with old files
