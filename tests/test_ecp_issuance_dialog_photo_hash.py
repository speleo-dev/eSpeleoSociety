from pathlib import Path
import unittest


class EcpIssuanceDialogPhotoHashTest(unittest.TestCase):
    """dialogs/ecp_issuance_dialog.py must not import PyQt5 directly in tests
    (project convention), so the fix is verified via source-text inspection.
    """

    def setUp(self):
        self.source = Path("dialogs/ecp_issuance_dialog.py").read_text(encoding="utf-8")

    def test_photo_hash_is_derived_from_actual_photo_bytes(self):
        # photo_hash must be computed from the actual PNG bytes of the loaded
        # photo, not from a random UUID that has no relation to the image
        # (breaks fetch_ecp_record_by_photo_hash content-based lookup/dedup).
        self.assertIn("photo_hash_val = hashlib.sha256(image_data).hexdigest()", self.source)
        self.assertNotIn("uuid.uuid4()", self.source)

    def test_uuid_module_is_not_imported_unused(self):
        import_line = next(
            line for line in self.source.splitlines() if line.startswith("import os, hashlib")
        )
        self.assertNotIn("uuid", import_line)


if __name__ == "__main__":
    unittest.main()
