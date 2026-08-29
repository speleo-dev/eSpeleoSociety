import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit
except ImportError:  # pragma: no cover - PyQt5 is a hard runtime dep
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not available")
class SecretSetupGuiTest(unittest.TestCase):
    """The setup window must actually render its fields.

    Regression guard: create_widgets() once built the layout but never called
    setLayout(), so the dialog opened completely empty after a correct PIN.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _build(self):
        import setup

        return setup, setup.SecretSetupGUI()

    def test_window_has_a_layout_with_all_fields(self):
        setup, gui = self._build()

        self.assertIsNotNone(gui.layout(), "setup window has no layout - it would render empty")
        self.assertEqual(len(gui.entries), len(setup.SECRET_SETUP_FIELDS))

        # Every entry must be parented into the window, otherwise it is invisible.
        for key, entry in gui.entries.items():
            with self.subTest(field=key):
                self.assertIsNotNone(entry.parentWidget(), f"field '{key}' is not attached to the window")

    def test_credentials_field_is_masked_and_has_import_button(self):
        setup, gui = self._build()

        self.assertIn("credentials_json", gui.entries)
        self.assertEqual(gui.entries["credentials_json"].echoMode(), QLineEdit.Password)
        self.assertTrue(hasattr(gui, "import_credentials_json"))

    def test_load_secrets_populates_line_edits_and_combobox(self):
        from config import secret_manager

        original = secret_manager.secrets
        secret_manager.secrets = {"db_host": "10.0.0.5", "log_level": "INFO"}
        try:
            _setup, gui = self._build()
            gui.load_secrets()
            self.assertEqual(gui.entries["db_host"].text(), "10.0.0.5")
            self.assertIsInstance(gui.entries["log_level"], QComboBox)
            self.assertEqual(gui.entries["log_level"].currentText(), "INFO")
        finally:
            secret_manager.secrets = original


if __name__ == "__main__":
    unittest.main()
