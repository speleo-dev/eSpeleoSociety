# PyQt5 UI patterns in eSpeleoSociety

## Application shell

`main.py` builds the shell: a `QHBoxLayout` with a fixed 300 px
`NavigationPanel` on the left and the stacked content views on the right, plus a
`QStatusBar` used for transient feedback. The global `QPushButton` style and the
status bar style are set once on the `QApplication` in `main.py` — put
app-wide chrome there, not in individual views.

Views live in `views/*.py` and modal editors in `dialogs/*.py`. Each view is a
`QWidget` subclass with an `init_ui(self)` method that builds the layout; keep
that convention for new views.

## Feedback: status bar over modal dialogs

`utils.py` provides non-blocking status bar helpers backed by
`_set_status_message`:

```python
from utils import show_success_message, show_warning_message, show_error_message, show_info_message
```

Use these for routine outcomes (saved, uploaded, nothing found, background job
finished). Reserve `QMessageBox` for decisions the operator must make or for
destructive confirmations.

Current drift: dialogs use the status helpers consistently, while list views
still fall back to `QMessageBox` for non-critical messages. When you touch a
view, migrate its informational popups to the status helpers.

## Tables

List views use `QTableWidget` with:

- `utils.get_table_header_stylesheet()` for the header — always use the helper,
  never restyle a header locally
- alternating row color `#E8E8E8` and highlight `#E8D888` (see design tokens)
- `QHeaderView` resize modes set explicitly per column
- `QAbstractItemView` selection behavior set to whole rows for member/club lists

Inline editing goes through `inline_editing.py` and `views/editing_delegates.py`
rather than ad-hoc `itemChanged` handlers. Reuse those delegates for any new
editable column so validation and commit semantics stay uniform.

## Member state iconography

`utils.get_state_pixmap(member, club)` maps membership state to the caver icons
in `images/` (`caver_green`, `caver_gold`, `caver_red`, `caver_gray_*`,
`caver_baned`, plus `star_icon` and `exclamation_icon`). Colors carry meaning
here — do not repurpose an existing icon for a new state and do not encode a new
state by color alone; pair it with a tooltip or a text column so it stays
readable for color-blind operators.

Pixmaps are cached and scaled by `_get_scaled_pixmap_from_cache`; load icons via
`utils.get_icon` instead of constructing `QIcon` from a path.

## Strings and localization

Every user-visible string in `views/` and `dialogs/` must be wrapped in
`self.tr(...)`. Translations live in `translate/sk_SK.ts` and
`translate/en_US.ts`, driven by the `SOURCES`/`TRANSLATIONS` lists in
`eSpeleoSociety.pro`; `main.py` installs the `QTranslator` based on the
preferred language setting.

When you add a new module containing translatable strings, add it to `SOURCES`
in `eSpeleoSociety.pro`, otherwise its strings are silently dropped from the
catalog. `python3 tools/preflight_check.py i18n` verifies this and also reports
unfinished translations — `translate/en_US.ts` currently has 253 of them, so the
English UI is largely untranslated. `ecp_card.py` is deliberately absent from
`SOURCES`: it is a Qt-free module used by the backend and by the preview tool,
so its Slovak labels are plain constants rather than `tr()` calls.

## Layout hygiene

- Do not hardcode widget pixel widths except for the navigation panel; use
  layouts and stretch factors so long Slovak strings and long club names fit.
- Slovak labels are typically 20-30% longer than the English equivalent; size
  test with the Slovak locale.
- Keep dialogs resizable — member and club dialogs contain address blocks that
  overflow at small default sizes.

## Do not couple UI to the database

Views currently reach into `db.DatabaseManager` directly. The documented target
architecture is API-only data access (`docs/api-oauth2-migration-plan.md`). Do
not add new direct SQL or new direct `DatabaseManager` calls in a view or a
dialog; route new reads and writes through the backend repository/API layer so
the migration does not grow.
