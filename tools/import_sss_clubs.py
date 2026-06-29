#!/usr/bin/env python3
"""Import the public SSS club directory into the local eSpeleoSociety DB."""

from __future__ import annotations

import argparse
import getpass
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

import requests

DEFAULT_URL = "https://sss.sk/zoznam-oblastnych-skupin/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MIGRATION_PATH = PROJECT_ROOT / "database/migrations/2026-06-29-club-directory-contacts.sql"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{5,}\d)")
URL_RE = re.compile(
    r"(?:https?://[A-Za-z0-9./?=&_%#:\-]+|www\.[A-Za-z0-9./?=&_%#:\-]+)"
)


@dataclass(frozen=True)
class ParsedCell:
    text: str
    hrefs: tuple[str, ...]


@dataclass(frozen=True)
class ClubDirectoryEntry:
    club_name: str
    president_name: str
    president_title_prefix: str
    president_first_name: str
    president_last_name: str
    president_title_suffix: str
    phone: str
    email: str
    webpage: str


class SssClubTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._table_depth = 0
        self._in_row = False
        self._in_cell = False
        self._current_row: list[ParsedCell] = []
        self._cell_parts: list[str] = []
        self._cell_hrefs: list[str] = []
        self.rows: list[list[ParsedCell]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table_depth += 1
            return
        if not self._table_depth:
            return
        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []
            self._cell_hrefs = []
        elif self._in_cell and tag == "br":
            self._cell_parts.append(", ")
        elif self._in_cell and tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._cell_hrefs.append(href)

    def handle_data(self, data):
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(
                ParsedCell(
                    text=normalize_text("".join(self._cell_parts)),
                    hrefs=tuple(self._cell_hrefs),
                )
            )
            self._in_cell = False
            self._cell_parts = []
            self._cell_hrefs = []
        elif tag == "tr" and self._in_row:
            if len(self._current_row) >= 3:
                self.rows.append(self._current_row[:3])
            self._in_row = False
            self._current_row = []
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip(" ,;\n\t")


def dedupe(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = normalize_text(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


PREFIX_TOKENS = {
    "bc.",
    "doc.",
    "ing.",
    "judr.",
    "mgr.",
    "mvdr.",
    "phdr.",
    "pharmdr.",
    "prof.",
    "rndr.",
    "art.",
}

SUFFIX_TOKENS = {
    "csc.",
    "drsc.",
    "ml.",
    "phd.",
}


def parse_person_name(full_name: str) -> tuple[str, str, str, str]:
    full_name = normalize_text(full_name)
    if not full_name:
        return "", "", "", ""

    name_part, suffix_part = (full_name.split(",", 1) + [""])[:2] if "," in full_name else (full_name, "")
    tokens = name_part.split()
    prefix_tokens = []
    while tokens and tokens[0].lower() in PREFIX_TOKENS:
        prefix_tokens.append(tokens.pop(0))

    trailing_suffix = []
    while tokens and tokens[-1].lower() in SUFFIX_TOKENS:
        trailing_suffix.insert(0, tokens.pop())

    first_name = tokens[0] if tokens else ""
    last_name = " ".join(tokens[1:]) if len(tokens) > 1 else ""
    suffix = " ".join(dedupe([suffix_part, " ".join(trailing_suffix)]))
    return " ".join(prefix_tokens), first_name, last_name, suffix


def normalize_url(url: str) -> str:
    url = normalize_text(url).rstrip(".,;")
    if url.startswith("www."):
        return f"https://{url}"
    return url


def dedupe_urls(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = normalize_url(value)
        key = re.sub(r"^https?://", "", cleaned.lower()).removeprefix("www.").rstrip("/")
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def extract_emails(contact_cell: ParsedCell) -> list[str]:
    candidates = EMAIL_RE.findall(contact_cell.text)
    for href in contact_cell.hrefs:
        if href.lower().startswith("mailto:"):
            email = unquote(href.split(":", 1)[1].split("?", 1)[0])
            candidates.extend(EMAIL_RE.findall(email))
    return dedupe(candidates)


def extract_webpages(contact_cell: ParsedCell) -> list[str]:
    candidates = []
    for href in contact_cell.hrefs:
        lower = href.lower()
        if lower.startswith("mailto:"):
            continue
        if lower.startswith(("http://", "https://", "www.")):
            candidates.append(normalize_url(href))
    candidates.extend(normalize_url(match) for match in URL_RE.findall(contact_cell.text))
    return dedupe_urls(candidates)


def extract_phones(contact_text: str, emails: list[str], webpages: list[str]) -> list[str]:
    searchable = contact_text
    for value in [*emails, *webpages]:
        searchable = searchable.replace(value, " ")
        if value.startswith("https://"):
            searchable = searchable.replace(value.removeprefix("https://"), " ")
        if value.startswith("http://"):
            searchable = searchable.replace(value.removeprefix("http://"), " ")

    candidates = []
    for match in PHONE_RE.findall(searchable):
        cleaned = normalize_text(match).strip(" ,;.")
        if sum(char.isdigit() for char in cleaned) >= 7:
            candidates.append(cleaned)
    return dedupe(candidates)


def parse_club_directory(html: str) -> list[ClubDirectoryEntry]:
    parser = SssClubTableParser()
    parser.feed(html)

    entries = []
    for row in parser.rows:
        club_name = normalize_text(row[0].text)
        president_name = normalize_text(row[1].text)
        if not club_name or club_name.lower() in {"nazov", "nazov skupiny", "klub"}:
            continue
        title_prefix, first_name, last_name, title_suffix = parse_person_name(president_name)
        emails = extract_emails(row[2])
        webpages = extract_webpages(row[2])
        phones = extract_phones(row[2].text, emails, webpages)
        entries.append(
            ClubDirectoryEntry(
                club_name=club_name,
                president_name=president_name,
                president_title_prefix=title_prefix,
                president_first_name=first_name,
                president_last_name=last_name,
                president_title_suffix=title_suffix,
                phone=", ".join(phones),
                email=", ".join(emails),
                webpage=", ".join(webpages),
            )
        )
    return entries


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def load_html(args) -> str:
    if args.html_file:
        return Path(args.html_file).read_text(encoding="utf-8")
    return fetch_html(args.url)


def apply_migration(manager) -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    with manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()


def apply_entries(entries: list[ClubDirectoryEntry], pin: str) -> None:
    from config import secret_manager
    import db

    if not secret_manager.decrypt_file(pin):
        raise SystemExit("Could not decrypt secrets.properties with the supplied PIN.")

    db.db_manager = db.DatabaseManager()
    apply_migration(db.db_manager)
    for entry in entries:
        db.db_manager.upsert_club_directory_entry(
            club_name=entry.club_name,
            president_name_text=entry.president_name,
            president_title_prefix=entry.president_title_prefix,
            president_first_name=entry.president_first_name,
            president_last_name=entry.president_last_name,
            president_title_suffix=entry.president_title_suffix,
            phone=entry.phone,
            email=entry.email,
            webpage=entry.webpage,
        )


def print_entries(entries: list[ClubDirectoryEntry]) -> None:
    print("club_name\tpresident_name\tphone\temail\twebpage")
    for entry in entries:
        print(
            f"{entry.club_name}\t{entry.president_name}\t"
            f"{entry.phone}\t{entry.email}\t{entry.webpage}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--html-file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--pin")
    args = parser.parse_args()

    entries = parse_club_directory(load_html(args))
    if args.apply:
        pin = args.pin or getpass.getpass("PIN: ")
        apply_entries(entries, pin)
        print(f"Imported or updated {len(entries)} SSS club directory rows.")
    else:
        print_entries(entries)
        print(f"\nDry-run parsed {len(entries)} SSS club directory rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
