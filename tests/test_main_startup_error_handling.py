from pathlib import Path
import unittest


class MainStartupErrorHandlingTest(unittest.TestCase):
    def setUp(self):
        self.source = Path("main.py").read_text(encoding="utf-8")

    def test_database_init_goes_through_guarded_helper(self):
        self.assertIn("def init_database_or_show_error():", self.source)
        self.assertIn("init_database_or_show_error()", self.source)

        # The __main__ block must not call DatabaseManager() directly,
        # otherwise a connection failure would crash with just a console
        # traceback instead of the GUI error dialog.
        main_block = self.source[self.source.index('if __name__ == "__main__":'):]
        self.assertNotIn("db.DatabaseManager()", main_block)

    def test_database_init_failure_is_caught_and_reported_via_message_box(self):
        helper_start = self.source.index("def init_database_or_show_error():")
        helper_body = self.source[helper_start:helper_start + 700]

        self.assertIn("try:", helper_body)
        self.assertIn("db.DatabaseManager()", helper_body)
        self.assertIn("except Exception", helper_body)
        self.assertIn("QMessageBox.critical(", helper_body)
        self.assertIn("sys.exit(", helper_body)


if __name__ == "__main__":
    unittest.main()
