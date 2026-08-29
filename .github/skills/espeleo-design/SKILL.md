---
name: espeleo-design
description: Design and review visual output of eSpeleoSociety - the PyQt5 desktop UI, the eCP card (JPG/PDF), the public verification page and the Google/Apple Wallet passes. Use when creating or changing any view, dialog, stylesheet, card layout, verification page HTML or wallet pass, or when asked to "navrhni UI", "uprav preukaz", "zmen vzhlad", "design the card", "restyle the view".
---

# eSpeleoSociety Design Skill

This project renders member identity in four surfaces that must look like one
product:

| Surface | Code | Technology |
|---|---|---|
| Desktop admin UI | `main.py`, `views/*.py`, `dialogs/*.py`, `navigation_panel.py` | PyQt5 stylesheets |
| eCP card JPG + PDF | `ecp_card.py:build_ecp_card_assets` | Pillow, absolute pixel coordinates |
| Public verification page | `ecp_card.py:build_verification_page_html` | inline HTML/CSS string |
| Wallet passes | `wallet_pass.py` | Google Wallet JSON, Apple PassKit dict |

**Rule zero: never design blind.** The card surfaces render deterministically
offline. Render first, look at the result, then change code.

## Step 1 - Render the current state

```bash
python3 tools/preview_ecp_card.py --out /tmp/ecp-preview
```

This generates a real card JPG, PDF, QR PNG and verification HTML from
synthetic data using a throwaway Ed25519 key. No database, no Google Cloud
bucket, no FTP and no configured secrets are required.

Useful flags: `--name`, `--club`, `--member-id`, `--status`, `--portrait <file>`.

Then **view the produced image** (`/tmp/ecp-preview/ecp_card.jpg`) before and
after every card change. Pixel layouts cannot be reviewed by reading code —
overflow and clipping are invisible in the source.

Always test at least these cases, because they are what breaks layouts:
- longest realistic name (title prefix + long surname + title suffix) — this
  once overwrote the QR code and made cards unscannable; it is now clipped by
  `_fit_text` and guarded by `tests/test_ecp_card_layout.py`
- long club name
- missing portrait (placeholder path)
- a `--status` value other than `active`

For the desktop UI there is no offline renderer; run `python3 main.py` or the
targeted view, and prefer changing a shared stylesheet helper over a local
`setStyleSheet` call.

## Step 2 - Use the design tokens, do not invent colors

The palette, spacing and the card geometry are documented in
`references/design-tokens.md`. Read it before picking any color or coordinate.

Critical known state: **the product currently has two conflicting palettes.**
The desktop UI uses navy `#011F4B` table headers and neutral gray gradient
buttons, while the card, verification page and wallet passes use cave teal
`#0b4a46` with gold `#d5a93f`. Teal/gold is the brand identity — it matches the
SSS logo and both wallet passes. When touching UI chrome, move it toward the
teal/gold tokens rather than adding another one-off color.

Styling is currently scattered across ~78 `setStyleSheet` call sites in 13
files. Do not add a 79th ad-hoc style: extend the shared helper pattern in
`utils.py` (see `get_table_header_stylesheet`) or the global stylesheet in
`main.py`, and reference a token.

## Step 3 - Respect the layout contracts

`references/ecp-card-spec.md` holds the card geometry, safe text areas, known
layout defects and the rules for the verification page and wallet passes.
`references/pyqt-ui-patterns.md` holds the desktop UI conventions.

## Step 4 - Verify

After any change to a design surface:

1. Re-render the preview and view the image again.
2. Confirm no text is clipped at the card edges and no field overlaps the QR or
   portrait boxes.
3. Run the affected tests:
   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ecp_card_layout tests.test_ecp_issuance tests.test_ecp_qr tests.test_wallet_pass -v
   ```
4. If you added or changed a user-visible string in a `views/` or `dialogs/`
   file, wrap it in `self.tr(...)` and update `translate/sk_SK.ts` and
   `translate/en_US.ts` (see `eSpeleoSociety.pro` for the `TRANSLATIONS` list).

## Hard rules

- **No new PII on the card or in the QR.** The offline QR intentionally carries
  a minimal signed claim plus a verification link. Never add birth date,
  address, email or phone to the card, the QR payload or the wallet pass.
- **Never change the QR payload structure for cosmetic reasons.** The payload is
  signed and verified by `ecp_qr.verify_ecp_payload`; changing field names or
  ordering invalidates already issued cards.
- **The same QR must remain valid across JPG, PDF and Wallet.** The card states
  this to the member. One issuance produces one QR used by all surfaces.
- **The verification page must stay a static, tokenized, non-indexed page.** Do
  not add trackers, external fonts, CDN assets or analytics to it.
- **Never hardcode a filesystem font path without a fallback chain.** See the
  font defect in `references/ecp-card-spec.md`.
