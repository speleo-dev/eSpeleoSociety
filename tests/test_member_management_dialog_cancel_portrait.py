from pathlib import Path
import unittest


class MemberManagementDialogCancelPortraitTest(unittest.TestCase):
    """dialogs/member_management_dialog.py must not import PyQt5 directly in
    tests (project convention), so the fix is verified via source-text
    inspection.
    """

    def setUp(self):
        self.source = Path("dialogs/member_management_dialog.py").read_text(encoding="utf-8")
        cancel_start = self.source.index("def cancel_changes(self):")
        next_def = self.source.index("\n    def ", cancel_start + 1)
        self.cancel_changes_body = self.source[cancel_start:next_def]

    def test_cancel_changes_discards_pending_portrait_upload(self):
        # A photo loaded via "Load Photo" but not yet saved must not survive
        # Cancel, otherwise it silently gets uploaded on the next Save even
        # though the user believed the change was discarded.
        self.assertIn("self.pending_portrait_result = None", self.cancel_changes_body)

    def test_cancel_changes_restores_portrait_preview(self):
        self.assertIn("self.load_existing_portrait_preview()", self.cancel_changes_body)


if __name__ == "__main__":
    unittest.main()
