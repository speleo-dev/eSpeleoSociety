# eSpeleo Security Hardening - Phase 3 & 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** Fix birth date encryption (#6) and UI bugs (#9-12)

**Architecture:** pgp_sym_encrypt with random IV, UI bug fixes with proper state management

**Tech Stack:** PostgreSQL, pgcrypto, PyQt5

## Global Constraints
- PostgreSQL 14+ with pgcrypto
- pgcrypto functions: pgp_sym_encrypt, pgp_sym_decrypt
- All DB changes must have rollback scripts
- UI changes need regression tests

---

## Phase 3: Fix Birth Date Encryption

### Task 1: Add pgp_sym_encrypt Support

**Files:**
- Modify: `espeleo/db.py`
- Modify: `database/schema.sql`
- Create: `database/migrations/2026-07-17-birthdate-pgp.sql`
- Test: `tests/test_db_pgp_encryption.py`

**Issue:** Zero IV causes deterministic encryption - same date = same ciphertext

**Interfaces:**
- Consumes: birth_date string, crypt_key
- Produces: pgp_sym_encrypt encrypted value with random IV

- [ ] **Step 1: Add pgp_sym_encrypt wrapper**

```python
# espeleo/db.py - in DatabaseManager
def _encrypt_birth_date(self, birth_date: str | None) -> str | None:
    """Encrypt birth date using pgp_sym_encrypt with random IV.
    
    Uses pgp_sym_encrypt for authenticated encryption with random IV.
    Each encryption produces different ciphertext for same input.
    """
    if birth_date is None or birth_date == '':
        return None
    
    crypt_key = self.config.get_secret('crypt_key')
    if not crypt_key:
        raise ValueError("crypt_key not configured")
    
    # Use pgp_sym_encrypt with AES-256
    query = """
        SELECT pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256')
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (birth_date, crypt_key))
            result = cur.fetchone()[0]
            return result


def _decrypt_birth_date(self, encrypted: str | None) -> str | None:
    """Decrypt birth date encrypted with pgp_sym_encrypt."""
    if encrypted is None:
        return None
    
    crypt_key = self.config.get_secret('crypt_key')
    if not crypt_key:
        raise ValueError("crypt_key not configured")
    
    query = """
        SELECT pgp_sym_decrypt(%s, %s)
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (encrypted, crypt_key))
            result = cur.fetchone()[0]
            return result
```

- [ ] **Step 2: Create migration script**

```sql
-- database/migrations/2026-07-17-birthdate-pgp.sql
-- Migrate birth_date_encrypted from AES-CBC (zero IV) to pgp_sym_encrypt

BEGIN;

-- Add new column for pgp-encrypted data
ALTER TABLE members ADD COLUMN birth_date_pgp bytea;

-- Note: Cannot automatically migrate old encrypted data without original plaintext
-- This migration requires application-level re-encryption on next member update
-- OR manual decryption + re-encryption script with crypt_key access

-- Add comment explaining the change
COMMENT ON COLUMN members.birth_date_encrypted IS 
    'DEPRECATED: Old AES-CBC encryption with zero IV. Use birth_date_pgp.';

COMMENT ON COLUMN members.birth_date_pgp IS 
    'New PGP-encrypted birth date with random IV. Preferred column.';

COMMIT;
```

- [ ] **Step 3: Update insert_member to use pgp_sym_encrypt**

```python
# espeleo/db.py - modify insert_member
# Find: encrypt(birth_date, 'aes')
# Replace with pgp_sym_encrypt

def insert_member(self, member_data: dict) -> int:
    """Insert member with PGP-encrypted birth date."""
    # ... other fields ...
    
    birth_date_pgp = self._encrypt_birth_date(member_data.get('birth_date'))
    
    query = """
        INSERT INTO members (
            first_name, last_name, birth_date_pgp,  -- Use new column
            email, phone, ...
        ) VALUES (%s, %s, %s, ...)
        RETURNING member_id
    """
    # ... execute ...
```

- [ ] **Step 4: Write encryption tests**

```python
# tests/test_db_pgp_encryption.py
import pytest
from datetime import date
from espeleo.db import DatabaseManager

class MockConfig:
    def get_secret(self, key):
        if key == 'crypt_key':
            return 'test-crypt-key-32-bytes-long!!'
        return None

def test_encrypt_same_date_different_ciphertext():
    """pgp_sym_encrypt must produce different ciphertext for same input."""
    # Mock or use test DB
    db = DatabaseManager(MockConfig())
    
    date_str = "1990-05-15"
    
    # Encrypt same date twice
    encrypted1 = db._encrypt_birth_date(date_str)
    encrypted2 = db._encrypt_birth_date(date_str)
    
    # Must be different (random IV)
    assert encrypted1 != encrypted2
    
    # But decrypt to same value
    decrypted1 = db._decrypt_birth_date(encrypted1)
    decrypted2 = db._decrypt_birth_date(encrypted2)
    assert decrypted1 == date_str
    assert decrypted2 == date_str

def test_roundtrip_various_dates():
    """Test encryption/decryption of various date formats."""
    db = DatabaseManager(MockConfig())
    
    test_dates = [
        "1990-01-01",
        "2000-12-31",
        "1985-06-15",
        None,
        "",
    ]
    
    for date_str in test_dates:
        if date_str:
            encrypted = db._encrypt_birth_date(date_str)
            decrypted = db._decrypt_birth_date(encrypted)
            assert decrypted == date_str
        else:
            assert db._encrypt_birth_date(date_str) is None
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_db_pgp_encryption.py -v
# Expected: tests may SKIP if no test DB, or PASS with ESPELEO_TEST_DATABASE_URL
```

- [ ] **Step 6: Commit PGP changes**

```bash
git add espeleo/db.py database/migrations/2026-07-17-birthdate-pgp.sql tests/test_db_pgp_encryption.py
git commit -m "security(db): use pgp_sym_encrypt for birth dates

Fixes audit finding #6:
- Replace deterministic AES-CBC (zero IV) with pgp_sym_encrypt
- Random IV ensures different ciphertext for same date
- Add migration script for new column
- Backward compatible with old column"
```

---

## Phase 4: Fix UI Bugs

### Task 2: Fix Notifications Checkbox (#9)

**Files:**
- Modify: `espeleo/dialogs/ecp_issuance_dialog.py`
- Test: `tests/test_ecp_dialog_notifications.py`

**Issue:** `notifications_enabled=True` hardcoded, checkbox ignored

**Interfaces:**
- Consumes: Checkbox state from UI
- Produces: Correct notifications_enabled value

- [ ] **Step 1: Find and fix hardcoded value**

```python
# espeleo/dialogs/ecp_issuance_dialog.py
# Find line ~170 with: notifications_enabled=True
# Replace with actual checkbox state

class EcpIssuanceDialog(QDialog):
    def _on_issue_clicked(self):
        """Handle issue button click."""
        # ... validation ...
        
        # Get actual checkbox state instead of hardcoded True
        notifications_enabled = self.notifications_checkbox.isChecked()
        
        # Pass to issuance logic
        self._issue_ecp(
            member_id=self.member_id,
            photo_path=self.photo_path,
            gdpr_consent=self.gdpr_checkbox.isChecked(),
            notifications_enabled=notifications_enabled,  # Use actual value
        )
```

- [ ] **Step 2: Write checkbox test**

```python
# tests/test_ecp_dialog_notifications.py
import pytest
from unittest.mock import MagicMock, patch
from espeleo.dialogs.ecp_issuance_dialog import EcpIssuanceDialog

def test_notifications_checkbox_respected():
    """Notifications checkbox state must be passed to issuance."""
    # Mock dialog
    dialog = EcpIssuanceDialog()
    dialog.member_id = 123
    dialog.photo_path = "/path/to/photo.jpg"
    
    # Mock checkbox states
    dialog.notifications_checkbox = MagicMock()
    dialog.gdpr_checkbox = MagicMock()
    
    # Test unchecked
    dialog.notifications_checkbox.isChecked.return_value = False
    dialog.gdpr_checkbox.isChecked.return_value = True
    
    with patch.object(dialog, '_issue_ecp') as mock_issue:
        dialog._on_issue_clicked()
        
        call_kwargs = mock_issue.call_args[1]
        assert call_kwargs['notifications_enabled'] is False
    
    # Test checked
    dialog.notifications_checkbox.isChecked.return_value = True
    
    with patch.object(dialog, '_issue_ecp') as mock_issue:
        dialog._on_issue_clicked()
        
        call_kwargs = mock_issue.call_args[1]
        assert call_kwargs['notifications_enabled'] is True
```

- [ ] **Step 3: Commit notifications fix**

```bash
git add espeleo/dialogs/ecp_issuance_dialog.py tests/test_ecp_dialog_notifications.py
git commit -m "fix(dialogs): respect notifications checkbox state

Fixes audit finding #9:
- Remove hardcoded notifications_enabled=True
- Use actual checkbox isChecked() value"
```

---

### Task 3: Fix Photo Hash from UUID (#10)

**Files:**
- Modify: `espeleo/dialogs/ecp_issuance_dialog.py`
- Test: `tests/test_ecp_dialog_photo_hash.py`

**Issue:** `photo_hash` computed from random UUID, not image bytes

**Interfaces:**
- Consumes: Image file path
- Produces: SHA256 hash of actual image bytes

- [ ] **Step 1: Fix photo hash computation**

```python
# espeleo/dialogs/ecp_issuance_dialog.py
# Find line ~147 with: hashlib.sha256(uuid.uuid4().bytes)
# Replace with hash of actual image

import hashlib

def _compute_photo_hash(self, photo_path: str) -> str:
    """Compute SHA256 hash of actual image bytes.
    
    Uses image content for deduplication, not random UUID.
    """
    with open(photo_path, 'rb') as f:
        image_bytes = f.read()
    
    return hashlib.sha256(image_bytes).hexdigest()

def _on_photo_selected(self, photo_path: str):
    """Handle photo selection."""
    # ... load and display photo ...
    
    # Compute hash from actual image
    self.photo_hash = self._compute_photo_hash(photo_path)
```

- [ ] **Step 2: Write photo hash test**

```python
# tests/test_ecp_dialog_photo_hash.py
import tempfile
import hashlib
import os
from espeleo.dialogs.ecp_issuance_dialog import EcpIssuanceDialog

def test_photo_hash_from_image_content():
    """Photo hash must be computed from image bytes, not UUID."""
    dialog = EcpIssuanceDialog()
    
    # Create temp image file
    image_data = b"fake-image-bytes-for-testing"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
        f.write(image_data)
        photo_path = f.name
    
    try:
        # Compute hash twice for same image
        hash1 = dialog._compute_photo_hash(photo_path)
        hash2 = dialog._compute_photo_hash(photo_path)
        
        # Must be identical (deterministic from content)
        assert hash1 == hash2
        assert hash1 == hashlib.sha256(image_data).hexdigest()
        
        # Different image = different hash
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f2:
            f2.write(b"different-image-data")
            photo_path2 = f2.name
        
        try:
            hash3 = dialog._compute_photo_hash(photo_path2)
            assert hash3 != hash1
        finally:
            os.unlink(photo_path2)
    finally:
        os.unlink(photo_path)

def test_photo_hash_not_random():
    """Photo hash must not be random/UUID-based."""
    dialog = EcpIssuanceDialog()
    
    image_data = b"test-image"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
        f.write(image_data)
        photo_path = f.name
    
    try:
        hashes = [dialog._compute_photo_hash(photo_path) for _ in range(5)]
        
        # All hashes must be identical
        assert len(set(hashes)) == 1
    finally:
        os.unlink(photo_path)
```

- [ ] **Step 3: Commit photo hash fix**

```bash
git add espeleo/dialogs/ecp_issuance_dialog.py tests/test_ecp_dialog_photo_hash.py
git commit -m "fix(dialogs): compute photo hash from image content

Fixes audit finding #10:
- Replace UUID-based hash with SHA256 of image bytes
- Enables proper photo deduplication
- Hash is deterministic for same image content"
```

---

### Task 4: Fix Cancel Button Portrait Reset (#11)

**Files:**
- Modify: `espeleo/dialogs/member_management_dialog.py`
- Test: `tests/test_member_dialog_cancel.py`

**Issue:** Cancel doesn't reset pending_portrait_result and preview

**Interfaces:**
- Consumes: Cancel button click
- Produces: Full state reset including portrait

- [ ] **Step 1: Fix cancel_changes method**

```python
# espeleo/dialogs/member_management_dialog.py
# Find cancel_changes around line 454-485

def cancel_changes(self):
    """Cancel all pending changes and reset to original state."""
    # Reset text fields (existing code)
    self.first_name_input.setText(self.original_data.get('first_name', ''))
    self.last_name_input.setText(self.original_data.get('last_name', ''))
    # ... other fields ...
    
    # FIX: Also reset portrait state
    self.pending_portrait_result = None
    self.portrait_preview.clear()
    self.portrait_preview.setText("No portrait")
    
    # Reload original portrait from database if exists
    if self.member_id:
        self._load_member_portrait(self.member_id)
```

- [ ] **Step 2: Write cancel test**

```python
# tests/test_member_dialog_cancel.py
import pytest
from unittest.mock import MagicMock, patch
from espeleo.dialogs.member_management_dialog import MemberManagementDialog

def test_cancel_resets_portrait_state():
    """Cancel must reset pending portrait and preview."""
    dialog = MemberManagementDialog()
    dialog.member_id = 123
    
    # Set up pending portrait state
    dialog.pending_portrait_result = {"photo_hash": "abc123"}
    dialog.portrait_preview = MagicMock()
    dialog.first_name_input = MagicMock()
    dialog.last_name_input = MagicMock()
    
    # Mock original data
    dialog.original_data = {
        'first_name': 'John',
        'last_name': 'Doe'
    }
    
    with patch.object(dialog, '_load_member_portrait'):
        dialog.cancel_changes()
        
        # Pending portrait must be cleared
        assert dialog.pending_portrait_result is None
        
        # Preview must be cleared
        dialog.portrait_preview.clear.assert_called_once()
        dialog.portrait_preview.setText.assert_called_with("No portrait")
```

- [ ] **Step 3: Commit cancel fix**

```bash
git add espeleo/dialogs/member_management_dialog.py tests/test_member_dialog_cancel.py
git commit -m "fix(dialogs): reset portrait on cancel

Fixes audit finding #11:
- Clear pending_portrait_result on cancel
- Clear portrait preview
- Reload original portrait from DB"
```

---

### Task 5: Fix President Lookup Silent Failure (#12)

**Files:**
- Modify: `espeleo/dialogs/club_management_dialog.py`
- Test: `tests/test_club_dialog_president.py`

**Issue:** President not found logs to console, silently sets None

**Interfaces:**
- Consumes: president_id from selection
- Produces: User-facing error or success

- [ ] **Step 1: Add proper error handling**

```python
# espeleo/dialogs/club_management_dialog.py
# Find president lookup around line 304-317

def _on_save_clicked(self):
    """Save club changes."""
    president_id = self.president_combo.currentData()
    
    if president_id:
        # Verify president exists
        member = self.db_manager.fetch_member_by_id(president_id)
        
        if member is None:
            # FIX: Show error to user instead of silent print
            QMessageBox.warning(
                self,
                "Invalid President",
                f"Selected president (ID: {president_id}) not found in members database.\n"
                "Please select a valid member as president."
            )
            return  # Don't save with invalid president
        
        president_name = f"{member.first_name} {member.last_name}"
    else:
        president_name = None
    
    # Continue with save...
```

- [ ] **Step 2: Write president validation test**

```python
# tests/test_club_dialog_president.py
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QMessageBox
from espeleo.dialogs.club_management_dialog import ClubManagementDialog

def test_invalid_president_shows_error():
    """Invalid president selection must show error, not silent failure."""
    dialog = ClubManagementDialog()
    dialog.db_manager = MagicMock()
    
    # Setup combo with invalid president ID
    dialog.president_combo = MagicMock()
    dialog.president_combo.currentData.return_value = 99999
    
    # Mock DB returning None (member not found)
    dialog.db_manager.fetch_member_by_id.return_value = None
    
    with patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
        result = dialog._on_save_clicked()
        
        # Error dialog must be shown
        mock_warning.assert_called_once()
        args = mock_warning.call_args[0]
        assert "Invalid President" in args[1]
        assert "not found" in args[2]

def test_valid_president_saves_successfully():
    """Valid president selection saves without error."""
    dialog = ClubManagementDialog()
    dialog.db_manager = MagicMock()
    
    # Setup combo with valid president ID
    dialog.president_combo = MagicMock()
    dialog.president_combo.currentData.return_value = 1
    
    # Mock DB returning valid member
    mock_member = MagicMock()
    mock_member.first_name = "John"
    mock_member.last_name = "Doe"
    dialog.db_manager.fetch_member_by_id.return_value = mock_member
    
    # Mock other UI elements
    dialog.club_name_input = MagicMock()
    dialog.club_name_input.text.return_value = "Test Club"
    
    with patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
        with patch.object(dialog, '_save_club') as mock_save:
            dialog._on_save_clicked()
            
            # No warning shown
            mock_warning.assert_not_called()
            
            # Save called with president
            mock_save.assert_called_once()
```

- [ ] **Step 3: Commit president fix**

```bash
git add espeleo/dialogs/club_management_dialog.py tests/test_club_dialog_president.py
git commit -m "fix(dialogs): validate president selection with user feedback

Fixes audit finding #12:
- Check if selected president exists in database
- Show QMessageBox warning if invalid
- Prevent save with non-existent president
- No silent data loss"
```

---

## Phase 3-4 Verification

- [ ] **Step 6: Run all phase 3-4 tests**

```bash
python -m pytest tests/test_db_pgp_encryption.py tests/test_ecp_dialog_notifications.py tests/test_ecp_dialog_photo_hash.py tests/test_member_dialog_cancel.py tests/test_club_dialog_president.py -v
# Expected: 8+ tests PASS
```

- [ ] **Step 7: Update documentation**

```bash
# Add to CODE_AUDIT.md status update
echo "
## Status Update 2026-07-17

Fixed:
- #6: Birth date encryption uses pgp_sym_encrypt with random IV
- #9: Notifications checkbox now respected
- #10: Photo hash computed from image content
- #11: Cancel button resets portrait state
- #12: President validation shows user error
" >> espeleo/CODE_AUDIT.md

git add espeleo/CODE_AUDIT.md
git commit -m "docs: update audit status for phase 3-4 fixes"
```

- [ ] **Step 8: Full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | head -50
# Verify no regressions
```

---

## Summary

**Fixed audit findings:** #6, #9, #10, #11, #12

**New files:**
- `database/migrations/2026-07-17-birthdate-pgp.sql`
- `tests/test_db_pgp_encryption.py`
- `tests/test_ecp_dialog_notifications.py`
- `tests/test_ecp_dialog_photo_hash.py`
- `tests/test_member_dialog_cancel.py`
- `tests/test_club_dialog_president.py`

**Modified files:**
- `espeleo/db.py` - pgp_sym_encrypt/decrypt methods
- `espeleo/dialogs/ecp_issuance_dialog.py` - notifications, photo hash
- `espeleo/dialogs/member_management_dialog.py` - cancel resets portrait
- `espeleo/dialogs/club_management_dialog.py` - president validation
- `espeleo/CODE_AUDIT.md` - status update

**Tests added:** 8+ tests

**Security improvements:**
- Random IV for birth date encryption
- Photo deduplication works correctly
- UI bugs fixed with proper state management
