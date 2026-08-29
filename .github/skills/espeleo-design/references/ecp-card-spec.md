# eCP card, verification page and wallet spec

## Card anatomy

`ecp_card.build_ecp_card_assets(member, club, issued_qr, portrait_image)`
returns `(jpeg_bytes, pdf_bytes)` rendered on a single `1011x638` canvas.

```
+--------------------------------------------------------------+
| teal header band (0-112)         [ SSS logo, right aligned ]  |
| gold rule (112-124)                                           |
+--------------------------------------------------------------+
|  [portrait]        member name (34 bold)     [   QR    ]      |
|  72,166           club / status / member id  [ 735,154  ]     |
|  292,466          valid until (bold) / issued[ 960,379  ]     |
|                                              QR note (16)     |
|                                                               |
|  footnotes at x=56, y=552 and y=582                           |
+--------------------------------------------------------------+
```

Field order is deliberate: identity (name) first, then affiliation (club),
then entitlement (status, member id), then validity. Do not reorder without a
reason — printed cards are compared side by side in the field.

## Data sources

Values come from the signed claim, not from the database row:

```python
claim = issued_qr.payload.get("claim", {})
claim["status"], claim["member_id"], claim["valid_until"], claim["issued_at"]
```

This is intentional: what is printed must be exactly what is signed. If you
need a new field on the card, it must first exist in the claim built by
`ecp_qr.create_ecp_claim` — and adding a claim field is a signing-format change,
not a design change. Treat it as such (see the hard rules in `SKILL.md`).

## Layout invariants (enforced by tests)

`tests/test_ecp_card_layout.py` guards these. Do not weaken them.

1. **Nothing may be drawn into the QR box.** The text column is clipped to
   `TEXT_COLUMN_MAX_WIDTH` (381 px) via `_fit_text`, which shrinks the font and
   then ellipsizes. The QR is pasted *after* the text column so even a future
   overflow bug cannot corrupt the code. The test renders a long name and both
   compares the QR region against a short-name render and decodes the QR with
   OpenCV.

2. **All text must fit inside the canvas.** The QR note under the QR box is
   wrapped by `_wrap_text` against `QR_NOTE_MAX_WIDTH`.

3. **Dates are rendered as `YYYY-MM-DD`.** `_format_date` accepts `date`,
   `datetime` and ISO 8601 strings (including a trailing `Z`), and falls back to
   the raw string for anything unparseable.

4. **Status is never shown as a raw enum.** `_format_status` maps internal
   values through `STATUS_LABELS` and passes unknown values through unchanged.

5. **Fonts must resolve on Linux, Windows and macOS.** `_font_candidates`
   probes a bundled `images/fonts/` directory first, then DejaVu on Linux, then
   Arial/Segoe UI on Windows and macOS. To pin the rendering exactly across
   platforms, drop `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` into
   `images/fonts/` — they take priority.

When you add a field to the card, route it through `_fit_text` like the existing
rows in the `rows` list, never through a bare `draw.text`.

## Portrait pipeline

`face_detection.py` is Qt-free and owns all portrait geometry, so it is testable
without a display and reusable from the backend.

- `PORTRAIT_ASPECT_RATIO` is derived from `PORTRAIT_BOX` (220 / 300). Any crop
  produced by the app uses this ratio so the portrait fills the card frame
  instead of being letterboxed by `_fit_image`.
- `detect_faces(image) -> (boxes, message)` never raises and never blocks an
  upload. It selects a backend at runtime:
  Haar (`cv2.CascadeClassifier`, OpenCV 4) → YuNet (`cv2.FaceDetectorYN`,
  OpenCV 5, needs `models/face_detection_yunet_2023mar.onnx` or the
  `ESPELEO_FACE_MODEL` env var) → an actionable message.
  **OpenCV 5 removed `CascadeClassifier` and ships no cascade XML**, which is why
  `requirements.txt` pins `opencv-python-headless<5`.
- `compute_face_crop_box` frames head and shoulders (face ≈ 62 % of the crop
  height, ~22 % headroom above it), clamped into the image. Without a face it
  falls back to `compute_center_crop_box`.
- `prepare_portrait_upload(path, crop_box=None, auto_crop=False)` applies the
  crop before resizing to `MAX_PORTRAIT_SIZE` and always returns `face_box` and
  `suggested_crop` so the UI can pre-position its crop frame.
- `dialogs/portrait_crop_dialog.py` is the only Qt part: an aspect-locked,
  draggable frame with "Auto-crop to face" and "Center". It must stay a thin
  wrapper — put new geometry in `face_detection.py` and cover it with
  `tests/test_portrait_crop.py`.

## Remaining design debt

- **Card labels are hardcoded Slovak strings** (with correct diacritics).
  `ecp_card.py` is intentionally not a Qt module — it is imported by the backend
  and by `tools/preview_ecp_card.py` — so `self.tr(...)` is not available here.
  Localizing the card needs a Qt-free catalog (for example a small dict keyed by
  locale), not an entry in `eSpeleoSociety.pro`.
- **Vertical space is unbalanced.** The band between `y = 466` (portrait bottom)
  and `y = 552` (footnotes) is empty while the text column is crowded into
  `y = 168..404`. A redesign should use that band.
- **`STATUS_LABELS` only covers Slovak.** Extend it together with any card
  localization work.

## Verification page

`build_verification_page_html(...) -> bytes` returns a complete standalone HTML
document that is uploaded as a static object and/or published over FTP.

Rules:
- All dynamic values must go through `html.escape` — the page embeds member and
  club names supplied from the database.
- No external requests: no CDN CSS, no web fonts, no analytics, no remote
  images other than the already-uploaded card/QR/portrait URLs.
- The URL is tokenized and the page must remain non-indexable; keep the
  `noindex` intent intact.
- The page must degrade gracefully when `portrait_url` is `None`.
- Keep it a single self-contained file; it has no build step.

## Wallet passes

`wallet_pass.py` builds a Google Wallet generic object and an Apple PassKit
dictionary from the same `issued_qr`.

- `build_wallet_barcode` must keep encoding the same `qr_data` string as the
  printed card, so a scanner reads an identical value from paper and phone.
- Colors must mirror `brand.teal` exactly (see `design-tokens.md`).
- Google Wallet save links are signed JWTs (`create_google_wallet_jwt_save_url`)
  — never log the produced URL, it is a bearer credential.
- Field labels shown in the wallet should match the card labels; a member sees
  both.
