import datetime
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedAddress:
    street: str
    city: str
    zip_code: str
    country: str


def normalize_cell_text(value) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def parse_full_name(value: str) -> tuple[str, str]:
    parts = normalize_cell_text(value).split(" ", 1)
    if not parts or not parts[0]:
        raise ValueError("Full name must contain at least a first name.")
    return parts[0], parts[1] if len(parts) > 1 else ""


def parse_address_text(value: str) -> ParsedAddress:
    parts = [part.strip() for part in str(value or "").split(",")]
    parts = (parts + ["", "", "", ""])[:4]
    return ParsedAddress(
        street=parts[0],
        city=parts[1],
        zip_code=parts[2],
        country=parts[3],
    )


def parse_optional_date(value: str):
    text = normalize_cell_text(value)
    if not text:
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc
