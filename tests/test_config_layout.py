import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import app_paths

REPO_ROOT = Path(app_paths.APP_ROOT)


class ConfigDirectoryLayoutTest(unittest.TestCase):
    def test_config_dir_is_not_a_python_package(self):
        """An __init__.py inside config/ would shadow the top-level config.py
        module and break every `from config import secret_manager`."""
        self.assertFalse(
            (REPO_ROOT / "config" / "__init__.py").exists(),
            "config/__init__.py shadows config.py - remove it",
        )

    def test_config_module_still_resolves_to_config_py(self):
        import config

        self.assertTrue(
            config.__file__.endswith("config.py"),
            f"`import config` resolved to {config.__file__} instead of config.py",
        )
        self.assertTrue(hasattr(config, "secret_manager"))

    def test_config_directory_is_git_ignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "config/config.properties"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, "config/ is not covered by .gitignore")

    def test_no_config_files_are_tracked(self):
        tracked = subprocess.run(
            ["git", "ls-files", "config/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(tracked, "", f"config/ must stay untracked, found: {tracked}")

    def test_secrets_default_path_lives_in_config_dir(self):
        from config import SecretManager

        manager = SecretManager()
        self.assertEqual(
            os.path.dirname(os.path.abspath(manager.properties_file)),
            os.path.abspath(app_paths.CONFIG_DIR),
        )


class LegacyConfigMigrationTest(unittest.TestCase):
    """Existing installs keep their settings/PIN after the layout change."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self._original_root = app_paths.APP_ROOT
        self._original_dir = app_paths.CONFIG_DIR
        app_paths.APP_ROOT = self.temp_dir
        app_paths.CONFIG_DIR = os.path.join(self.temp_dir, "config")

    def tearDown(self):
        app_paths.APP_ROOT = self._original_root
        app_paths.CONFIG_DIR = self._original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_root_file_is_moved_into_config_dir(self):
        legacy = os.path.join(self.temp_dir, "secrets.properties")
        with open(legacy, "wb") as handle:
            handle.write(b"encrypted-payload")

        resolved = app_paths.migrate_legacy_config_file("secrets.properties")

        self.assertEqual(resolved, os.path.join(app_paths.CONFIG_DIR, "secrets.properties"))
        self.assertTrue(os.path.isfile(resolved))
        self.assertFalse(os.path.exists(legacy), "legacy file should have been moved, not copied")
        with open(resolved, "rb") as handle:
            self.assertEqual(handle.read(), b"encrypted-payload")

    def test_existing_config_file_is_never_overwritten_by_legacy_copy(self):
        os.makedirs(app_paths.CONFIG_DIR, exist_ok=True)
        target = os.path.join(app_paths.CONFIG_DIR, "secrets.properties")
        with open(target, "wb") as handle:
            handle.write(b"current")
        legacy = os.path.join(self.temp_dir, "secrets.properties")
        with open(legacy, "wb") as handle:
            handle.write(b"stale")

        app_paths.migrate_legacy_config_file("secrets.properties")

        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), b"current")

    def test_missing_legacy_file_returns_config_path_without_creating_it(self):
        resolved = app_paths.migrate_legacy_config_file("config.properties")
        self.assertEqual(resolved, os.path.join(app_paths.CONFIG_DIR, "config.properties"))
        self.assertFalse(os.path.exists(resolved))


if __name__ == "__main__":
    unittest.main()
