import base64
import json


DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def parse_limit(raw_value) -> int:
    if raw_value in (None, ""):
        return DEFAULT_LIMIT
    try:
        limit = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def encode_cursor(offset: int) -> str:
    payload = json.dumps({"offset": int(offset)}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        decoded = json.loads(payload.decode("utf-8"))
        return max(0, int(decoded.get("offset", 0)))
    except Exception:
        return 0


def encode_id_cursor(last_id: int) -> str:
    payload = json.dumps({"lastId": int(last_id)}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def decode_id_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        decoded = json.loads(payload.decode("utf-8"))
        return max(0, int(decoded.get("lastId", 0)))
    except Exception:
        return 0


def encode_keyset_cursor(values: dict) -> str:
    payload = json.dumps({"keyset": values}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def decode_keyset_cursor(cursor: str | None) -> dict:
    if not cursor:
        return {}
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        decoded = json.loads(payload.decode("utf-8"))
        keyset = decoded.get("keyset", {})
        return keyset if isinstance(keyset, dict) else {}
    except Exception:
        return {}


def paginate_items(items: list, limit: int, cursor: str | None) -> tuple[list, str | None]:
    offset = decode_cursor(cursor)
    page = items[offset:offset + limit]
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return page, next_cursor
