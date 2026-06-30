import re
import unicodedata


def normalize_member_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_friendly = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", ascii_friendly.casefold()).strip()


def member_matches_fast_search(member, query: str) -> bool:
    tokens = normalize_member_search_text(query).split()
    if not tokens:
        return True

    first_name = normalize_member_search_text(getattr(member, "first_name", ""))
    last_name = normalize_member_search_text(getattr(member, "last_name", ""))
    full_name = normalize_member_search_text(f"{first_name} {last_name}")
    reversed_name = normalize_member_search_text(f"{last_name} {first_name}")
    searchable_values = (first_name, last_name, full_name, reversed_name)
    return all(any(value.startswith(token) for value in searchable_values) for token in tokens)
