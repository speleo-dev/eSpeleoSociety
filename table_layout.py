# table_layout.py
"""Qt-free model of a user-adjustable table layout.

Column geometry is addressed by a **stable key**, never by position, so a
persisted layout survives adding, removing or reordering columns in the code.
Anything unknown or corrupted is dropped instead of raising - a bad layout file
must never stop a table from being displayed.

The Qt side lives in :mod:`ui_table`; keeping the rules here means they can be
unit tested without a display server.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

MIN_COLUMN_WIDTH = 40
MAX_COLUMN_WIDTH = 1200
DEFAULT_COLUMN_WIDTH = 140

LAYOUT_VERSION = 1


@dataclass
class ColumnSpec:
    """Declarative description of one table column.

    ``key`` is the stable identifier used in the persisted layout. ``label`` is
    the (translated) header text and may change freely between releases.
    """

    key: str
    label: str
    width: int = DEFAULT_COLUMN_WIDTH
    hidden: bool = False
    essential: bool = False
    stretch: bool = False
    numeric: bool = False
    tooltip: str = ""

    def __post_init__(self):
        if not self.key:
            raise ValueError("ColumnSpec.key must not be empty")
        self.width = clamp_width(self.width)
        if self.essential:
            # An essential column (identity, row actions) can never be hidden -
            # otherwise the row becomes unusable with no obvious way back.
            self.hidden = False


def clamp_width(width) -> int:
    try:
        value = int(width)
    except (TypeError, ValueError):
        return DEFAULT_COLUMN_WIDTH
    return max(MIN_COLUMN_WIDTH, min(MAX_COLUMN_WIDTH, value))


@dataclass
class TableLayout:
    """Persisted per-table state: widths, visibility, order and sorting."""

    widths: dict = field(default_factory=dict)
    hidden: list = field(default_factory=list)
    order: list = field(default_factory=list)
    sort_key: str = ""
    sort_descending: bool = False

    def is_hidden(self, key: str) -> bool:
        return key in self.hidden

    def width_for(self, spec: ColumnSpec) -> int:
        return clamp_width(self.widths.get(spec.key, spec.width))


def default_layout(specs) -> TableLayout:
    """Layout implied by the column declarations themselves."""
    return TableLayout(
        widths={spec.key: spec.width for spec in specs},
        hidden=[spec.key for spec in specs if spec.hidden],
        order=[spec.key for spec in specs],
    )


def sanitize_layout(raw, specs) -> TableLayout:
    """Turn arbitrary decoded JSON into a layout that is safe to apply.

    Unknown keys are dropped, missing ones fall back to the declared defaults,
    widths are clamped, essential columns are forced visible and the order is
    completed with any column the stored layout did not know about.
    """
    specs = list(specs)
    by_key = {spec.key: spec for spec in specs}
    known = list(by_key)

    if not isinstance(raw, dict):
        return default_layout(specs)

    widths = {}
    raw_widths = raw.get("widths")
    if isinstance(raw_widths, dict):
        for key, value in raw_widths.items():
            if key in by_key:
                widths[key] = clamp_width(value)
    for spec in specs:
        widths.setdefault(spec.key, spec.width)

    raw_hidden = raw.get("hidden")
    if isinstance(raw_hidden, (list, tuple, set)):
        hidden = [key for key in known if key in set(raw_hidden) and not by_key[key].essential]
    else:
        hidden = [spec.key for spec in specs if spec.hidden]

    if len(hidden) == len(known):
        # Never persist a state where the table looks empty and broken.
        hidden = [key for key in hidden if key != known[0]]

    raw_order = raw.get("order")
    order = []
    if isinstance(raw_order, (list, tuple)):
        for key in raw_order:
            if key in by_key and key not in order:
                order.append(key)
    for key in known:
        if key not in order:
            order.append(key)

    sort_key = raw.get("sort_key")
    if sort_key not in by_key:
        sort_key = ""

    return TableLayout(
        widths=widths,
        hidden=hidden,
        order=order,
        sort_key=sort_key or "",
        sort_descending=bool(raw.get("sort_descending")),
    )


def encode_layout(layout: TableLayout) -> str:
    return json.dumps(
        {
            "version": LAYOUT_VERSION,
            "widths": layout.widths,
            "hidden": list(layout.hidden),
            "order": list(layout.order),
            "sort_key": layout.sort_key,
            "sort_descending": bool(layout.sort_descending),
        },
        sort_keys=True,
    )


def decode_layout(text, specs) -> TableLayout:
    """Parse a stored layout string. Never raises - falls back to defaults."""
    if not text:
        return default_layout(specs)
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        return default_layout(specs)
    return sanitize_layout(raw, specs)


def visible_specs(specs, layout: TableLayout):
    """Specs in persisted visual order, hidden ones removed."""
    by_key = {spec.key: spec for spec in specs}
    ordered = [by_key[key] for key in layout.order if key in by_key]
    for spec in specs:
        if spec not in ordered:
            ordered.append(spec)
    return [spec for spec in ordered if not layout.is_hidden(spec.key)]


def toggle_hidden(layout: TableLayout, spec: ColumnSpec, hidden: bool, specs) -> TableLayout:
    """Return a layout with ``spec`` shown/hidden, refusing invalid states."""
    keys = [s.key for s in specs]
    new_hidden = [key for key in layout.hidden if key in keys]
    if hidden and not spec.essential:
        if spec.key not in new_hidden:
            new_hidden.append(spec.key)
        if len(new_hidden) == len(keys):
            new_hidden.remove(spec.key)
    else:
        new_hidden = [key for key in new_hidden if key != spec.key]
    layout.hidden = new_hidden
    return layout


# --- persistence -----------------------------------------------------------
#
# Layouts live next to the other user-specific configuration in config/ (which
# is git-ignored) rather than in the platform settings store, so a user can
# reset their UI simply by deleting one obvious file.

LAYOUT_STORE_FILENAME = "table_layouts.json"


def _store_path() -> str:
    import app_paths

    return app_paths.config_path(LAYOUT_STORE_FILENAME)


def _read_store() -> dict:
    try:
        with open(_store_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_layout(table_key: str, specs) -> TableLayout:
    """Stored layout for ``table_key``, or the declared defaults."""
    raw = _read_store().get(table_key)
    if raw is None:
        return default_layout(specs)
    return sanitize_layout(raw, specs)


def save_layout(table_key: str, layout: TableLayout) -> bool:
    """Persist ``layout``. Returns False instead of raising on I/O problems -
    failing to remember a column width must never break the application."""
    import app_paths

    store = _read_store()
    store[table_key] = json.loads(encode_layout(layout))
    try:
        app_paths.ensure_config_dir()
        with open(_store_path(), "w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2, sort_keys=True)
    except OSError as exc:
        print(f"WARNING: Could not save table layout for '{table_key}': {exc}")
        return False
    return True


def clear_layout(table_key: str) -> bool:
    store = _read_store()
    if store.pop(table_key, None) is None:
        return False
    try:
        with open(_store_path(), "w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2, sort_keys=True)
    except OSError:
        return False
    return True
