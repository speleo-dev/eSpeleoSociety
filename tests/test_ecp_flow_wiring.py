from pathlib import Path
import unittest


class EcpFlowWiringTest(unittest.TestCase):
    def test_issuance_and_approval_flows_upload_signed_qr(self):
        issuance_source = Path("dialogs/ecp_issuance_dialog.py").read_text(encoding="utf-8")
        approval_source = Path("dialogs/ecp_approval_dialog.py").read_text(encoding="utf-8")

        self.assertIn("issue_and_upload_signed_ecp_qr", issuance_source)
        self.assertIn("issue_and_upload_signed_ecp_qr", approval_source)
        self.assertIn("upload_to_bucket", issuance_source)
        self.assertIn("upload_to_bucket", approval_source)
        self.assertIn("update_ecp_record_issuance", issuance_source)
        self.assertIn("update_ecp_record_issuance", approval_source)


if __name__ == "__main__":
    unittest.main()
