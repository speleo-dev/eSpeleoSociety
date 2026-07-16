from pathlib import Path
import unittest


class EcpAtomicIssuanceWiringTest(unittest.TestCase):
    """Audit #18: insert_ecp/update_ecp_record_issuance/update_member_ecp_hash/
    update_ecp_request_status must share one transaction() instead of running as
    independent auto-commit statements."""

    def test_issuance_dialog_wraps_ecp_creation_in_one_transaction(self):
        source = Path("dialogs/ecp_issuance_dialog.py").read_text(encoding="utf-8")

        self.assertIn("with db.db_manager.transaction() as conn:", source)
        self.assertIn("db.db_manager.insert_ecp(ecp_obj, conn=conn)", source)
        self.assertIn(
            "db.db_manager.update_member_ecp_hash(self.member.member_id, self.member.ecp_hash, conn=conn)",
            source,
        )
        self.assertIn("legal_document_url=delivery_bundle.legal_document_url,\n                    conn=conn,\n                )", source)

    def test_approval_dialog_wraps_ecp_approval_in_one_transaction(self):
        source = Path("dialogs/ecp_approval_dialog.py").read_text(encoding="utf-8")

        self.assertIn("with db.db_manager.transaction() as conn:", source)
        self.assertIn(
            'db.db_manager.update_member_ecp_hash(self.member.member_id, new_generated_ecp_hash, conn=conn)',
            source,
        )
        self.assertIn(
            'db.db_manager.update_ecp_request_status(self.req_details.request_id, "approved", conn=conn)',
            source,
        )


if __name__ == "__main__":
    unittest.main()
