# secrets_export.py
"""Qt-free serialization of decrypted secrets to TXT/CSV.

Kept out of ``setup.py`` so the format can be unit tested without a display and
reused from any tooling. The produced files contain **plaintext secrets** - the
caller is responsible for asking for the PIN again and for writing the file
with restrictive permissions (see :func:`write_secrets_export`).
"""

import csv
import datetime
import io
import os

EXPORT_WARNING = (
    "WARNING: This file contains PLAINTEXT secrets (passwords, private keys, "
    "API credentials). Store it encrypted, never commit it, and delete it once "
    "you no longer need it."
)


def _timestamp() -> str:
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def build_secrets_txt(secrets: dict, fields) -> str:
    """Human readable ``key = value`` dump.

    ``fields`` is a sequence of ``(key, label)`` pairs defining the order.
    Multi-line values (JSON keys, PEM material) are indented so the file stays
    readable and unambiguous.
    """
    lines = [
        "# eSpeleoSociety secrets export",
        f"# Generated: {_timestamp()}",
        f"# {EXPORT_WARNING}",
        "",
    ]

    for key, label in fields:
        value = secrets.get(key, "")
        value = "" if value is None else str(value)
        lines.append(f"# {label}")
        if "\n" in value:
            lines.append(f"{key} =")
            for value_line in value.splitlines():
                lines.append(f"    {value_line}")
        else:
            lines.append(f"{key} = {value}")
        lines.append("")

    extra = [key for key in sorted(secrets) if key not in {k for k, _ in fields}]
    if extra:
        lines.append("# --- additional secrets not shown in the setup form ---")
        for key in extra:
            value = secrets.get(key)
            lines.append(f"{key} = {'' if value is None else value}")
        lines.append("")

    return "\n".join(lines)


def build_secrets_csv(secrets: dict, fields) -> str:
    """``key,label,value`` CSV. Uses the csv module so embedded newlines,
    commas and quotes (JSON keys, PEM blocks) survive a round trip."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["key", "label", "value"])

    known = {k for k, _ in fields}
    for key, label in fields:
        value = secrets.get(key, "")
        writer.writerow([key, label, "" if value is None else str(value)])

    for key in sorted(k for k in secrets if k not in known):
        value = secrets.get(key)
        writer.writerow([key, "", "" if value is None else str(value)])

    return buffer.getvalue()


def build_secrets_export(secrets: dict, fields, export_format: str) -> str:
    export_format = (export_format or "").lower()
    if export_format == "csv":
        return build_secrets_csv(secrets, fields)
    if export_format == "txt":
        return build_secrets_txt(secrets, fields)
    raise ValueError(f"Unsupported export format: {export_format!r}")


def write_secrets_export(path: str, secrets: dict, fields, export_format: str = None) -> str:
    """Write the export to ``path`` with owner-only permissions.

    ``export_format`` defaults to the file extension. Returns the format used.
    """
    if export_format is None:
        export_format = os.path.splitext(path)[1].lstrip(".").lower() or "txt"

    content = build_secrets_export(secrets, fields, export_format)

    # Create the file without a readable-by-others window.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        handle = os.fdopen(fd, "w", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise
    with handle:
        handle.write(content)

    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # best effort (e.g. on Windows / exotic filesystems)

    return export_format
