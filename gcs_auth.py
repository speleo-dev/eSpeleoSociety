# gcs_auth.py
"""Shared helper for resolving Google Cloud Storage credentials.

``credentials_json`` (a secret configured via setup.py) can be either:

1. The full content of a GCP service account key (a JSON object). This is the
   recommended form: the key travels inside the encrypted ``secrets.properties``
   file, so it can't go missing when the app is set up on a new machine.
2. A path to a service account key file on disk (legacy form, kept for
   backwards compatibility with existing installs).

:func:`resolve_gcs_credentials` never raises; it returns ``(credentials, error)``
where exactly one of the two is set.
"""

import json
import os


def resolve_gcs_credentials(credentials_json: str):
    """Resolve a ``google.auth.credentials.Credentials`` object.

    Returns ``(credentials, None)`` on success or ``(None, error_message)``.
    """
    if not credentials_json:
        return None, "credentials_json is not configured."

    stripped = credentials_json.strip()

    if stripped.startswith("{"):
        try:
            from google.oauth2 import service_account
        except ImportError as exc:
            return None, f"Missing dependency for GCS credentials: {exc}"
        try:
            info = json.loads(stripped)
        except ValueError as exc:
            return None, f"credentials_json is not valid JSON: {exc}"
        try:
            return service_account.Credentials.from_service_account_info(info), None
        except Exception as exc:
            return None, f"credentials_json content is not a valid service account key: {exc}"

    # Legacy form: a path to a key file on disk.
    if not os.path.isfile(stripped):
        return None, (
            f"GCS credentials file '{stripped}' was not found. "
            "Re-import the service account key in the Secrets Setup dialog "
            "so it is stored directly (recommended), or restore the file at that path."
        )

    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        return None, f"Missing dependency for GCS credentials: {exc}"
    try:
        return service_account.Credentials.from_service_account_file(stripped), None
    except Exception as exc:
        return None, f"GCS credentials file '{stripped}' could not be loaded: {exc}"
