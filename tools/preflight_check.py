"""Project-specific pre-flight checks for eSpeleoSociety.

Complements the unit test suite with checks that unit tests do not cover:
translation catalog integrity, API contract coverage, migration safety and
architectural layering.

Usage::

    python3 tools/preflight_check.py            # run every check
    python3 tools/preflight_check.py --list     # show available checks
    python3 tools/preflight_check.py i18n api   # run selected checks

Exit code is non-zero when any check fails, so it can be wired into CI.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TRANSLATION_FILES = ["translate/sk_SK.ts", "translate/en_US.ts"]
PRO_FILE = "eSpeleoSociety.pro"
OPENAPI_FILE = "docs/api/openapi.yaml"
BACKEND_APP = "backend/app.py"
MIGRATIONS_DIR = "database/migrations"
UI_DIRS = ["views", "dialogs"]

TR_PATTERN = re.compile(r"self\.tr\(|QCoreApplication\.translate\(|QApplication\.translate\(")
API_PATH_PATTERN = re.compile(r"\"(/api/v1[^\"]*)\"")
OPENAPI_PATH_PATTERN = re.compile(r"^ {2}(/[^:]*):\s*$")
SQL_IN_UI_PATTERN = re.compile(r"\b(?:cursor|cur|conn)\.execute\(|\bSELECT\s+.*\bFROM\b", re.IGNORECASE)


class Result:
    def __init__(self, name: str) -> None:
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")


def _python_sources() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        parts = set(path.relative_to(REPO_ROOT).parts)
        if parts & {".git", ".venv", "build", "__pycache__", "tests"}:
            continue
        files.append(path)
    return sorted(files)


def check_i18n() -> Result:
    """Translation catalogs parse and cover every module with translatable strings."""
    result = Result("i18n")

    for rel in TRANSLATION_FILES:
        path = REPO_ROOT / rel
        if not path.is_file():
            result.error(f"missing translation catalog: {rel}")
            continue
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            result.error(f"{rel} is not valid XML: {exc}")
            continue
        messages = tree.getroot().iter("message")
        unfinished = sum(
            1
            for message in messages
            if (message.find("translation") is not None
                and message.find("translation").get("type") in {"unfinished", "obsolete"})
        )
        if unfinished:
            result.warn(f"{rel}: {unfinished} unfinished/obsolete translations")

    pro_path = REPO_ROOT / PRO_FILE
    if not pro_path.is_file():
        result.error(f"missing {PRO_FILE}")
        return result

    pro_text = pro_path.read_text(encoding="utf-8", errors="replace")
    for source in _python_sources():
        rel = source.relative_to(REPO_ROOT).as_posix()
        if not TR_PATTERN.search(source.read_text(encoding="utf-8", errors="replace")):
            continue
        if rel not in pro_text:
            result.error(f"{rel} contains translatable strings but is missing from SOURCES in {PRO_FILE}")

    return result


def check_api() -> Result:
    """Every backend route is described in the OpenAPI contract."""
    result = Result("api")

    app_path = REPO_ROOT / BACKEND_APP
    spec_path = REPO_ROOT / OPENAPI_FILE
    if not app_path.is_file() or not spec_path.is_file():
        result.error(f"missing {BACKEND_APP} or {OPENAPI_FILE}")
        return result

    implemented = set()
    for match in API_PATH_PATTERN.findall(app_path.read_text(encoding="utf-8", errors="replace")):
        route = match[len("/api/v1"):] or "/"
        if route.endswith("/") and len(route) > 1:
            continue  # prefix fragment used for startswith matching, not a route
        implemented.add(route)

    documented = set()
    for line in spec_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = OPENAPI_PATH_PATTERN.match(line)
        if match:
            documented.add(match.group(1))

    def normalise(route: str) -> str:
        return re.sub(r"\{[^}]+\}", "{}", route)

    documented_norm = {normalise(route) for route in documented}
    for route in sorted(implemented):
        if normalise(route) not in documented_norm:
            result.error(f"route {route} is implemented in {BACKEND_APP} but not documented in {OPENAPI_FILE}")

    implemented_norm = {normalise(route) for route in implemented}
    for route in sorted(documented):
        if normalise(route) not in implemented_norm:
            result.warn(f"route {route} is documented but not implemented")

    result.note(f"{len(implemented)} implemented routes, {len(documented)} documented paths")
    return result


def check_migrations() -> Result:
    """Migrations are transactional so a failure cannot leave a half-applied schema."""
    result = Result("migrations")

    migrations_dir = REPO_ROOT / MIGRATIONS_DIR
    if not migrations_dir.is_dir():
        result.error(f"missing {MIGRATIONS_DIR}")
        return result

    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        result.warn("no migrations found")
        return result

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO_ROOT).as_posix()
        has_begin = re.search(r"^\s*BEGIN\s*;", text, re.IGNORECASE | re.MULTILINE) is not None
        has_commit = re.search(r"^\s*COMMIT\s*;", text, re.IGNORECASE | re.MULTILINE) is not None
        if not (has_begin and has_commit):
            result.error(f"{rel} is not wrapped in BEGIN; ... COMMIT;")

    result.note(f"checked {len(files)} migration files")
    return result


def check_layering() -> Result:
    """UI modules must not execute SQL directly."""
    result = Result("layering")

    for directory in UI_DIRS:
        base = REPO_ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if SQL_IN_UI_PATTERN.search(line):
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    result.error(f"{rel}:{lineno} executes SQL from the UI layer: {line.strip()[:90]}")

    return result


def check_secrets() -> Result:
    """No plaintext secret material is tracked in the working tree."""
    result = Result("secrets")

    forbidden_files = ["temp.properties", "github-token.txt", ".env"]
    for name in forbidden_files:
        path = REPO_ROOT / name
        if path.exists():
            result.error(f"{name} exists in the repository root and must never be committed")

    # config/ holds machine-specific configuration and must stay untracked.
    tracked_config = subprocess.run(
        ["git", "ls-files", "config/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tracked_config:
        for entry in tracked_config.splitlines():
            result.error(f"{entry} is tracked but config/ must be git-ignored")

    # An __init__.py in config/ turns the directory into a package that shadows
    # the top-level config.py module and breaks every `from config import ...`.
    if (REPO_ROOT / "config" / "__init__.py").exists():
        result.error("config/__init__.py shadows config.py and breaks all imports of it")

    key_pattern = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    for path in REPO_ROOT.rglob("*"):
        parts = set(path.relative_to(REPO_ROOT).parts)
        if parts & {".git", ".venv", "build", "__pycache__", "config"}:
            continue
        if not path.is_file() or path.suffix in {".png", ".jpg", ".ico", ".qm", ".pdf"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if key_pattern.search(text):
            rel = path.relative_to(REPO_ROOT).as_posix()
            result.error(f"{rel} contains a PEM private key block")

    return result


CHECKS = {
    "i18n": check_i18n,
    "api": check_api,
    "migrations": check_migrations,
    "layering": check_layering,
    "secrets": check_secrets,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("checks", nargs="*", help="Checks to run (default: all)")
    parser.add_argument("--list", action="store_true", help="List available checks and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, func in CHECKS.items():
            print(f"{name:<12} {(func.__doc__ or '').strip().splitlines()[0]}")
        return 0

    selected = args.checks or list(CHECKS)
    unknown = [name for name in selected if name not in CHECKS]
    if unknown:
        parser.error(f"unknown check(s): {', '.join(unknown)}")

    failed = 0
    for name in selected:
        result = CHECKS[name]()
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {name}")
        for note in result.notes:
            print(f"    note: {note}")
        for warning in result.warnings:
            print(f"    warn: {warning}")
        for error in result.errors:
            print(f"    error: {error}")
        if not result.ok:
            failed += 1

    print()
    print(f"{len(selected) - failed}/{len(selected)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
