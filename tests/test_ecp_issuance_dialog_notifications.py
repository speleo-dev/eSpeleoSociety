from pathlib import Path
import unittest


class EcpIssuanceDialogNotificationsTest(unittest.TestCase):
    """dialogs/ecp_issuance_dialog.py must not import PyQt5 directly in tests
    (project convention), so the fix is verified via source-text inspection.
    """

    def setUp(self):
        self.source = Path("dialogs/ecp_issuance_dialog.py").read_text(encoding="utf-8")

    def test_ecp_record_uses_notifications_checkbox_state(self):
        # The "Enable Notifications" checkbox must actually control the
        # notifications_enabled flag stored in the eCP record instead of
        # always being hardcoded to True.
        self.assertIn("notifications_enabled=self.chk_notifications.isChecked()", self.source)
        self.assertNotIn("notifications_enabled=True", self.source)


if __name__ == "__main__":
    unittest.main()
