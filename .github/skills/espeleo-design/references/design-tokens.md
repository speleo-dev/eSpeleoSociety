# eSpeleoSociety design tokens

Extracted from the current implementation. When a value below conflicts with
code you are reading, the code is the drift — prefer the token and migrate the
call site.

## Brand palette (card, verification page, wallet)

| Token | Hex | Used for |
|---|---|---|
| `brand.teal` | `#0b4a46` | card header band, QR frame outline, wallet background, page accents |
| `brand.gold` | `#d5a93f` | 12 px accent rule under the card header, highlight |
| `brand.teal.ink` | `#dbe8e4` | subtitle text on teal |
| `surface.card` | `#f7faf9` | card body background |
| `surface.page` | `#f3f6f5` | verification page background |
| `surface.muted` | `#fafcfb`, `#e1e8e6`, `#d7dfdc` | panels, dividers on the page |
| `text.strong` | `#10201f` | member display name |
| `text.body` | `#243533` | card field text |
| `text.muted` | `#526260` | issued-at line, legal footnotes |
| `text.page` | `#1a2926` | verification page body text |
| `border.neutral` | `#6f7d82` | portrait frame outline |
| `placeholder.bg` | `#e1e6e8` | portrait placeholder fill |
| `placeholder.fit` | `#eef2f3` | letterbox fill behind a fitted portrait |
| `placeholder.ink` | `#607078` | "PHOTO" placeholder label |
| `status.ok` | `#1b873f` on `#e8f7ee` / `#c2ebd0` | valid / success states |
| `status.warn` | `#FF9800` | warning states |

Wallet equivalents (`wallet_pass.py`) must stay numerically identical to
`brand.teal`: Google `hexBackgroundColor: "#0b4a46"`, Apple
`backgroundColor: "rgb(11, 74, 70)"`, `labelColor: "rgb(190, 220, 215)"`,
`foregroundColor: "rgb(255, 255, 255)"`. Changing one without the other splits
the brand across platforms.

## Desktop UI palette (legacy, being migrated)

| Token | Hex | Used for |
|---|---|---|
| `ui.header` | `#011F4B` | `QHeaderView::section` background (`utils.get_table_header_stylesheet`) |
| `ui.header.border` | `#B3CDE0` | table header section border |
| `ui.button.top` / `ui.button.bottom` | `#f6f7fa` / `#dadbde` | `QPushButton` vertical gradient (`main.py` global stylesheet) |
| `ui.button.border` | `#8f8f91` | button border, radius 6 px, padding 5 px, min-width 50 px |
| `ui.divider` | `#B0B0B0` | status bar top border |
| `ui.row.alt` | `#E8E8E8` | alternating table rows (most frequent hex in the codebase) |
| `ui.row.highlight` | `#E8D888` | highlighted rows |
| `ui.link` | `#0b5f86` | link-styled labels |

This legacy set is navy/gray and does not match the teal/gold brand. Target
state: table headers and primary buttons adopt `brand.teal`, accents adopt
`brand.gold`, neutrals stay.

## Typography

- **Card:** DejaVu Sans / DejaVu Sans Bold via `ecp_card._font(size, bold)`.
  Sizes in use: 36 bold (product title), 34 bold (member name), 22 (fields),
  22 bold (validity), 19 (subtitle), 18 (issued at), 17 (footnotes), 16 (QR
  note), 18 bold (portrait placeholder).
- **Verification page:** `'Segoe UI', Roboto, Helvetica, Arial, sans-serif`,
  line-height 1.5, 20 px page padding. System fonts only, never a web font.
- **Desktop UI:** inherit the Qt system font. Do not set a font family in a
  stylesheet; only adjust size and weight when necessary.

## Geometry (card)

Defined at the top of `ecp_card.py`:

```python
CARD_SIZE    = (1011, 638)     # ~ISO ID-1 aspect at print resolution
PORTRAIT_BOX = (72, 166, 292, 466)   # 220 x 300
QR_BOX       = (735, 154, 960, 379)  # 225 x 225
```

Derived layout constants used by `build_ecp_card_assets`:

- header band: `y 0-112`, gold rule `y 112-124`
- logo: max 140x80, right aligned with 40 px right margin, 16 px top margin
- text column: starts at `x = 330`, rows at `y = 168, 216, 258, 300, 342, 384`
- footnote block: `x = 56`, `y = 552` and `y = 582`
- PDF export: `resolution=150.0`; JPEG export: `quality=92, optimize=True`

**Safe areas.** The right column between the QR box and the card edge is only
`1011 - 735 = 276 px` wide. The left text column between `x = 330` and the QR
box is `735 - 330 = 405 px` wide. Any string placed there must be measured
(`ImageDraw.textlength`) and either wrapped or shrunk — see the clipping defect
in `ecp-card-spec.md`.
