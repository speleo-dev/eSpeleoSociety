# app_paths.py
"""Central location of user/machine-specific configuration files.

All runtime configuration lives in a single ``config/`` directory next to the
application so it can be excluded from version control as a whole (see
``.gitignore``). Static resources that must survive a fresh clone - translation
catalogs, the OpenAPI contract, CI workflows - deliberately stay where they are.

Note the directory is intentionally *not* a Python package: an ``__init__.py``
inside ``config/`` would shadow the top-level ``config.py`` module and break
every ``from config import secret_manager`` in the codebase.
"""

import os
import shutil

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(APP_ROOT, "config")

# Files that used to live in the application root and are now kept in config/.
MIGRATED_CONFIG_FILES = ("secrets.properties", "config.properties")


def ensure_config_dir() -> str:
    """Create the config directory when missing and return its path."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return CONFIG_DIR


def config_path(filename: str) -> str:
    """Absolute path of ``filename`` inside the config directory."""
    return os.path.join(CONFIG_DIR, filename)


def migrate_legacy_config_file(filename: str) -> str:
    """Move a pre-existing root-level config file into ``config/``.

    Keeps existing installations working after the layout change instead of
    silently falling back to defaults (which would look like lost settings and,
    for secrets.properties, like a forgotten PIN). Returns the resolved path.
    """
    target = config_path(filename)
    if os.path.exists(target):
        return target

    legacy = os.path.join(APP_ROOT, filename)
    if os.path.isfile(legacy):
        ensure_config_dir()
        try:
            shutil.move(legacy, target)
            print(f"INFO: Moved '{filename}' into the config/ directory.")
        except OSError as exc:
            print(f"WARNING: Could not move '{filename}' into config/: {exc}")
            return legacy
    return target


def resolve_config_file(filename: str) -> str:
    """Path to use for ``filename``, migrating a legacy copy if needed."""
    return migrate_legacy_config_file(filename)


def migrate_all_legacy_config_files() -> None:
    for filename in MIGRATED_CONFIG_FILES:
        migrate_legacy_config_file(filename)
