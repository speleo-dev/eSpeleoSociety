# SEPA and eCP Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the current thick-client code enough to run focused tests, fix the broken SEPA payment import path, and remove the eCP approval crash before the larger API/OAuth2 migration.

**Architecture:** Keep the existing PyQt thick client, but extract payment classification into a pure Python module that can be tested without a live database or GUI. Keep Google Wallet as a stub for now, but make the stub accept the actual request object shape used by the dialogs.

**Tech Stack:** Python 3, PyQt5, unittest, PostgreSQL via the existing `db.py` adapter.

---

### Task 1: Test Harness and Importability

**Files:**
- Create: `tests/test_utils_importability.py`
- Modify: `utils.py`

- [ ] **Step 1: Write the failing test**

```python
import importlib


def test_utils_imports_without_optional_cloud_and_crypto_dependencies():
    module = importlib.import_module("utils")
    assert hasattr(module, "parse_camt053")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_utils_importability -v`
Expected before implementation: import fails when optional dependencies such as `Crypto` or `google.cloud.storage` are not installed.

- [ ] **Step 3: Write minimal implementation**

Move `Crypto.Cipher.AES` and `google.cloud.storage` imports behind helper functions inside `utils.py`, so import-time behavior only requires modules needed by the called function.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_utils_importability -v`
Expected after implementation: `OK`.

### Task 2: SEPA Processing Logic

**Files:**
- Create: `sepa_processing.py`
- Create: `tests/test_sepa_processing.py`
- Modify: `views/sepa_import_view.py`

- [ ] **Step 1: Write the failing tests**

```python
from decimal import Decimal
from types import SimpleNamespace

from sepa_processing import process_transactions


def test_process_transactions_returns_valid_payment_for_active_member():
    parsed = {"transactions": [{"ecp_hash_candidate": "ecp-1", "amount": "20.00", "currency": "EUR"}]}
    member = SimpleNamespace(first_name="Ada", last_name="Lovelace", discounted_membership=False)
    ecp = SimpleNamespace(member_id=7, is_ecp_active=True)

    result = process_transactions(
        parsed,
        normal_fee=Decimal("20.00"),
        discounted_fee=Decimal("10.00"),
        fetch_ecp=lambda value: ecp if value == "ecp-1" else None,
        fetch_member_by_id=lambda value: member if value == 7 else None,
    )

    assert result[0]["status"] == "valid"
    assert result[0]["name_or_iban"] == "Ada Lovelace"


def test_process_transactions_returns_list_for_unknown_reference():
    parsed = {
        "transactions": [{
            "ecp_hash_candidate": "missing",
            "amount": "20.00",
            "currency": "EUR",
            "debtor_account_iban": "SK00",
        }]
    }

    result = process_transactions(
        parsed,
        normal_fee=Decimal("20.00"),
        discounted_fee=Decimal("10.00"),
        fetch_ecp=lambda value: None,
        fetch_member_by_id=lambda value: None,
    )

    assert len(result) == 1
    assert result[0]["status"] == "unknown_reference_expected_amount"
    assert result[0]["name_or_iban"] == "SK00"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_sepa_processing -v`
Expected before implementation: `ModuleNotFoundError: No module named 'sepa_processing'`.

- [ ] **Step 3: Write minimal implementation**

Add `sepa_processing.process_transactions()` that classifies parsed camt.053 transactions without importing PyQt. Update `SepaImportView.process_transactions()` to call the pure function and return the resulting list.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_sepa_processing -v`
Expected after implementation: `OK`.

### Task 3: eCP Wallet Request Helper

**Files:**
- Create: `tests/test_wallet_request.py`
- Modify: `utils.py`
- Modify: `dialogs/ecp_approval_dialog.py`

- [ ] **Step 1: Write the failing test**

```python
from types import SimpleNamespace

from utils import get_request_field


def test_get_request_field_supports_object_attributes():
    request = SimpleNamespace(photo_hash="photo-1")
    assert get_request_field(request, "photo_hash") == "photo-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_wallet_request -v`
Expected before implementation: import succeeds after Task 1, but `get_request_field` is missing.

- [ ] **Step 3: Write minimal implementation**

Add `get_request_field()` and update `send_to_google_wallet()` to use it instead of `req_details.get(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_wallet_request -v`
Expected after implementation: `OK`.

### Task 4: Final Verification

**Files:**
- Modify: `requirements.txt`
- Modify: `db.py`

- [ ] **Step 1: Add runtime dependency manifest**

Create `requirements.txt` with the dependencies imported by the current application.

- [ ] **Step 2: Align eCP request query with insert path**

Change `DatabaseManager.fetch_ecp_requests()` to join `ecp_requests.photo_hash` to `ecp_records.photo_hash`, because `insert_ecp_request()` writes `photo_hash` and not `ecp_record_id`.

- [ ] **Step 3: Run all focused verification**

Run: `python3 -m unittest discover -s tests -v`
Expected: all focused tests pass.

Run: `python3 -c "<ast parse all .py files>"`
Expected: all Python files parse successfully.
