from pathlib import Path
import unittest


class EcpFlowWiringTest(unittest.TestCase):
    def test_issuance_and_approval_flows_use_signed_ecp_delivery_bundle(self):
        issuance_source = Path("dialogs/ecp_issuance_dialog.py").read_text(encoding="utf-8")
        approval_source = Path("dialogs/ecp_approval_dialog.py").read_text(encoding="utf-8")

        self.assertIn("issue_and_upload_ecp_delivery_bundle", issuance_source)
        self.assertIn("issue_and_upload_ecp_delivery_bundle", approval_source)
        self.assertIn("upload_to_bucket", issuance_source)
        self.assertIn("upload_to_bucket", approval_source)
        self.assertIn("update_ecp_record_issuance", issuance_source)
        self.assertIn("update_ecp_record_issuance", approval_source)
        self.assertIn("send_ecp_issued_email", issuance_source)
        self.assertIn("send_ecp_issued_email", approval_source)
        self.assertIn("card_image", issuance_source)
        self.assertIn("card_image", approval_source)

    def test_approval_flow_passes_native_wallet_barcode_data(self):
        approval_source = Path("dialogs/ecp_approval_dialog.py").read_text(encoding="utf-8")

        self.assertIn("signed_qr_data", approval_source)
        self.assertIn("delivery_bundle.issued_qr.qr_data", approval_source)

    def test_reject_request_deletes_photo_before_db_records_and_checks_result(self):
        approval_source = Path("dialogs/ecp_approval_dialog.py").read_text(encoding="utf-8")

        photo_delete_index = approval_source.index("if not delete_photo_from_bucket(self.ecp_record.photo_hash):")
        db_delete_index = approval_source.index("db.db_manager.delete_ecp_record_by_id(self.ecp_record.ecp_id)")

        self.assertLess(
            photo_delete_index,
            db_delete_index,
            "photo must be deleted from the bucket before the DB record, and only if it succeeded (audit #19)",
        )


if __name__ == "__main__":
    unittest.main()
