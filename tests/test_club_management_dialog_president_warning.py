from pathlib import Path
import unittest


class ClubManagementDialogPresidentWarningTest(unittest.TestCase):
    """dialogs/club_management_dialog.py must not import PyQt5 directly in
    tests (project convention), so the fix is verified via source-text
    inspection.
    """

    def setUp(self):
        self.source = Path("dialogs/club_management_dialog.py").read_text(encoding="utf-8")

    def test_missing_president_shows_ui_warning_instead_of_print(self):
        # If president_id does not match any club member, the operator must
        # be warned in the UI instead of the failure only being printed to
        # the console while save is reported as successful.
        found_at = self.source.index("president_name_found = False")
        fallback_block = self.source[found_at:found_at + 800]

        self.assertIn("if not president_name_found:", fallback_block)
        self.assertIn("show_warning_message(", fallback_block)
        self.assertNotIn("print(", fallback_block)


if __name__ == "__main__":
    unittest.main()
