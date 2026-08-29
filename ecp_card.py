from datetime import date, datetime
from html import escape
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ecp_documents import DEFAULT_LEGAL_DOCUMENT_URL, default_legal_documents


CARD_SIZE = (1011, 638)
PORTRAIT_BOX = (72, 166, 292, 466)
QR_BOX = (735, 154, 960, 379)

TEXT_COLUMN_X = 330
TEXT_COLUMN_GAP = 24
TEXT_COLUMN_MAX_WIDTH = QR_BOX[0] - TEXT_COLUMN_X - TEXT_COLUMN_GAP
CARD_SIDE_MARGIN = 40
QR_NOTE_MAX_WIDTH = CARD_SIZE[0] - QR_BOX[0] - CARD_SIDE_MARGIN

STATUS_LABELS = {
    "active": "Aktívny",
    "inactive": "Neaktívny",
    "suspended": "Pozastavený",
    "expired": "Vypršaný",
    "banned": "Zablokovaný",
    "pending": "Čakajúci",
}


def public_gcs_url(bucket_name: str, blob_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"


def _format_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(candidate).date().isoformat()
    except ValueError:
        pass
    try:
        return date.fromisoformat(candidate[:10]).isoformat()
    except ValueError:
        return text


def _format_status(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return STATUS_LABELS.get(text.lower(), text)


def _member_display_name(member) -> str:
    parts = [
        getattr(member, "title_prefix", None),
        getattr(member, "first_name", None),
        getattr(member, "last_name", None),
        getattr(member, "title_suffix", None),
    ]
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def _font_candidates(bold: bool) -> list[str]:
    bundled_dir = Path(__file__).parent / "images" / "fonts"
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        str(bundled_dir / name),
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"/usr/share/fonts/dejavu/{name}",
        f"C:/Windows/Fonts/{name}",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    return candidates


def _font(size: int, bold: bool = False):
    for candidate in _font_candidates(bold):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no size argument
        return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    return draw.textlength(text, font=font)


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    size: int,
    bold: bool = False,
    min_size: int = 12,
) -> tuple[str, "ImageFont.ImageFont"]:
    """Shrink then ellipsize ``text`` so it never exceeds ``max_width``.

    Overflow here is not cosmetic: the text column sits directly left of the QR
    box, so an unbounded string is painted across the QR modules and makes the
    card unscannable.
    """
    text = "" if text is None else str(text)
    font = _font(size, bold)
    if not text:
        return text, font

    current_size = size
    while current_size > min_size and _text_width(draw, text, font) > max_width:
        current_size -= 1
        font = _font(current_size, bold)

    if _text_width(draw, text, font) <= max_width:
        return text, font

    ellipsis = "..."
    truncated = text
    while truncated and _text_width(draw, truncated + ellipsis, font) > max_width:
        truncated = truncated[:-1]
    return (truncated + ellipsis) if truncated else ellipsis, font


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font) -> list[str]:
    words = str(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_image(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(target_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", target_size, "#eef2f3")
    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def _load_portrait(portrait_image: bytes | None, target_size: tuple[int, int]) -> Image.Image:
    if portrait_image:
        try:
            with Image.open(BytesIO(portrait_image)) as image:
                return _fit_image(image, target_size)
        except Exception:
            pass
    placeholder = Image.new("RGB", target_size, "#e1e6e8")
    draw = ImageDraw.Draw(placeholder)
    draw.text((target_size[0] // 2, target_size[1] // 2), "PHOTO", anchor="mm", fill="#607078", font=_font(18, True))
    return placeholder


def build_ecp_card_assets(member, club, issued_qr, portrait_image: bytes | None = None) -> tuple[bytes, bytes]:
    card = Image.new("RGB", CARD_SIZE, "#f7faf9")
    draw = ImageDraw.Draw(card)

    draw.rectangle((0, 0, CARD_SIZE[0], 112), fill="#0b4a46")
    draw.rectangle((0, 112, CARD_SIZE[0], 124), fill="#d5a93f")
    draw.text((56, 34), "eSpeleoSociety eCP", fill="white", font=_font(36, True))
    draw.text((56, 78), "Elektronický členský preukaz", fill="#dbe8e4", font=_font(19))

    # SSS Logo in header
    logo_path = Path(__file__).parent / "images" / "Logo_sss.png"
    if not logo_path.exists():
        logo_path = Path("images/Logo_sss.png")
    if logo_path.exists():
        try:
            with Image.open(logo_path) as logo_img:
                logo_img = logo_img.convert("RGBA")
                logo_img.thumbnail((140, 80), Image.Resampling.LANCZOS)
                card.paste(logo_img, (CARD_SIZE[0] - logo_img.width - CARD_SIDE_MARGIN, 16), logo_img)
        except Exception:
            pass

    portrait_size = (PORTRAIT_BOX[2] - PORTRAIT_BOX[0], PORTRAIT_BOX[3] - PORTRAIT_BOX[1])
    portrait = _load_portrait(portrait_image, portrait_size)
    card.paste(portrait, (PORTRAIT_BOX[0], PORTRAIT_BOX[1]))
    draw.rectangle(PORTRAIT_BOX, outline="#6f7d82", width=2)

    display_name = _member_display_name(member) or "Člen"
    club_name = getattr(club, "name", "") or ""
    claim = issued_qr.payload.get("claim", {})

    rows = [
        (168, display_name, 34, True, "#10201f"),
        (216, f"Klub: {club_name}", 22, False, "#243533"),
        (258, f"Stav: {_format_status(claim.get('status'))}", 22, False, "#243533"),
        (300, f"Členské ID: {claim.get('member_id', '')}", 22, False, "#243533"),
        (342, f"Platnosť do: {_format_date(claim.get('valid_until'))}", 22, True, "#243533"),
        (384, f"Vydané: {_format_date(claim.get('issued_at'))}", 18, False, "#526260"),
    ]
    for y, text, size, bold, fill in rows:
        fitted, font = _fit_text(draw, text, TEXT_COLUMN_MAX_WIDTH, size, bold)
        draw.text((TEXT_COLUMN_X, y), fitted, fill=fill, font=font)

    # Drawn after the text column so a text overflow can never corrupt the QR.
    qr = Image.open(BytesIO(issued_qr.qr_png)).convert("RGB")
    qr = qr.resize((QR_BOX[2] - QR_BOX[0], QR_BOX[3] - QR_BOX[1]), Image.Resampling.NEAREST)
    card.paste(qr, (QR_BOX[0], QR_BOX[1]))
    draw.rectangle(QR_BOX, outline="#0b4a46", width=2)

    qr_note_font = _font(16)
    qr_note_y = QR_BOX[3] + 25
    for line in _wrap_text(draw, "Rovnaký QR platí pre JPG, PDF aj Wallet.", QR_NOTE_MAX_WIDTH, qr_note_font):
        draw.text((QR_BOX[0], qr_note_y), line, fill="#243533", font=qr_note_font)
        qr_note_y += 22

    draw.text((56, 552), "Offline QR obsahuje iba minimálne podpísané údaje a online kontrolný link.", fill="#526260", font=_font(17))
    draw.text((56, 582), "Online detail je tokenizovaná statická stránka bez verejného indexovania.", fill="#526260", font=_font(17))

    image_buffer = BytesIO()
    card.save(image_buffer, format="JPEG", quality=92, optimize=True)
    image_bytes = image_buffer.getvalue()

    pdf_buffer = BytesIO()
    card.save(pdf_buffer, format="PDF", resolution=150.0)
    pdf_bytes = pdf_buffer.getvalue()
    return image_bytes, pdf_bytes


def build_verification_page_html(
    member,
    club,
    issued_qr,
    qr_url: str | None,
    card_image_url: str,
    card_pdf_url: str,
    portrait_url: str | None = None,
    legal_document_url: str = DEFAULT_LEGAL_DOCUMENT_URL,
) -> bytes:
    claim = issued_qr.payload.get("claim", {})
    documents = claim.get("legal_documents") or default_legal_documents()
    document_links = "\n".join(
        f'<li><a href="{escape(doc.get("url", ""))}" rel="noopener noreferrer">{escape(doc.get("name", "Dokument"))}</a></li>'
        for doc in documents
    )
    import base64
    
    # Load SSS Logo as base64
    sss_logo_b64 = ""
    logo_path = Path(__file__).parent / "images" / "Logo_sss.png"
    if not logo_path.exists():
        logo_path = Path("images/Logo_sss.png")
    if logo_path.exists():
        try:
            sss_logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        except Exception:
            pass

    portrait_html = f'<img class="portrait" src="{escape(portrait_url)}" alt="Portrét člena">' if portrait_url else ""
    qr_b64 = base64.b64encode(issued_qr.qr_png).decode("ascii") if getattr(issued_qr, "qr_png", None) else ""
    qr_img_html = f'<img class="qr-img" src="data:image/png;base64,{qr_b64}" alt="eCP QR kód">' if qr_b64 else ""

    payload_json = escape(json.dumps(issued_qr.payload, indent=2, sort_keys=True, ensure_ascii=False))
    display_name = escape(_member_display_name(member) or "Člen SSS")
    club_name = escape(getattr(club, "name", "") or claim.get("club_name", "") or "Bez klubu")
    valid_until_str = escape(str(claim.get("valid_until", "")))
    member_id_str = escape(str(claim.get("member_id", "")))
    status_str = escape(str(claim.get("status", "active")).capitalize())
    issued_at_str = escape(str(claim.get("issued_at", ""))[:10])

    logo_img_tag = f'<img class="sss-logo" src="data:image/png;base64,{sss_logo_b64}" alt="SSS Logo">' if sss_logo_b64 else ''

    html = f"""<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <meta name="referrer" content="no-referrer">
  <title>eCP Preukaz - {display_name}</title>
  <style>
    :root {{
      --primary: #0b4a46;
      --primary-dark: #073330;
      --gold: #d5a93f;
      --bg: #f3f6f5;
      --card-bg: #ffffff;
      --text: #1a2926;
      --text-muted: #536662;
      --success: #1b873f;
      --border: #d3dfdc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .container {{
      max-width: 780px;
      margin: 24px auto;
      padding: 0 16px;
    }}
    .card {{
      background: var(--card-bg);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(11, 74, 70, 0.08);
      border: 1px solid var(--border);
    }}
    .header {{
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 20px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .header-brand {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .sss-logo {{
      width: 58px;
      height: 52px;
      object-fit: contain;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    }}
    .header h1 {{
      margin: 0 0 2px 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .header p {{
      margin: 0;
      color: #c0ded8;
      font-size: 13px;
    }}
    .club-badge-slot {{
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.2);
      padding: 8px 14px;
      border-radius: 8px;
      text-align: right;
      font-size: 12px;
      max-width: 220px;
    }}
    .club-badge-title {{
      display: block;
      color: var(--gold);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 10px;
      letter-spacing: 0.5px;
    }}
    .club-badge-name {{
      font-weight: 600;
      color: white;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }}
    .gold-bar {{
      height: 6px;
      background: var(--gold);
    }}
    .status-banner {{
      background: #e8f7ee;
      border-bottom: 1px solid #c2ebd0;
      color: var(--success);
      padding: 12px 24px;
      font-weight: 700;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .body-grid {{
      padding: 24px;
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 20px;
      align-items: start;
    }}
    .portrait-wrap {{
      width: 130px;
      height: 165px;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid var(--border);
      background: #e9eff0;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .portrait-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .details-table {{
      margin: 0;
      display: grid;
      grid-template-columns: 110px 1fr;
      gap: 10px 14px;
      font-size: 14px;
    }}
    .details-table dt {{
      color: var(--text-muted);
      font-weight: 600;
    }}
    .details-table dd {{
      margin: 0;
      font-weight: 600;
      color: var(--text);
    }}
    .qr-wrap {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }}
    .qr-img {{
      width: 125px;
      height: 125px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 4px;
      background: white;
    }}
    .qr-label {{
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 600;
    }}
    .actions-bar {{
      padding: 16px 24px;
      background: #fafcfb;
      border-top: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 16px;
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
      border-radius: 8px;
      transition: background 0.15s;
    }}
    .btn-primary {{
      background: var(--primary);
      color: white;
    }}
    .btn-primary:hover {{
      background: var(--primary-dark);
    }}
    .btn-secondary {{
      background: white;
      color: var(--primary);
      border: 1px solid var(--primary);
    }}
    .btn-secondary:hover {{
      background: #eef5f4;
    }}
    .btn-wallet {{
      background: #1f2328;
      color: white;
    }}
    .btn-wallet:hover {{
      background: #000000;
    }}
    .doc-section {{
      padding: 18px 24px;
      border-top: 1px solid var(--border);
    }}
    .doc-section h2 {{
      font-size: 15px;
      margin: 0 0 8px 0;
      color: var(--primary);
    }}
    .doc-link {{
      color: #0b5f86;
      text-decoration: none;
      font-weight: 500;
    }}
    .doc-link:hover {{ text-decoration: underline; }}
    details {{
      padding: 14px 24px;
      background: #fafcfb;
      border-top: 1px solid var(--border);
      font-size: 12px;
      color: var(--text-muted);
    }}
    details summary {{
      cursor: pointer;
      font-weight: 600;
      color: var(--primary);
    }}
    pre {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      overflow-x: auto;
      font-size: 11px;
      color: #333;
    }}
    @media (max-width: 680px) {{
      .header {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .club-badge-slot {{
        text-align: left;
        max-width: 100%;
        width: 100%;
      }}
      .body-grid {{
        grid-template-columns: 1fr;
        justify-items: center;
        text-align: center;
      }}
      .details-table {{
        grid-template-columns: 1fr;
        gap: 6px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="header">
        <div class="header-brand">
          {logo_img_tag}
          <div>
            <h1>{display_name}</h1>
            <p>Slovenská speleologická spoločnosť &bull; Elektronický preukaz eCP</p>
          </div>
        </div>
        <div class="club-badge-slot">
          <span class="club-badge-title">Klub / Skupina</span>
          <span class="club-badge-name">{club_name}</span>
        </div>
      </div>
      <div class="gold-bar"></div>
      <div class="status-banner">
        <span>✓</span> PLATNÝ ČLENSKÝ PREUKAZ (AKTÍVNE ČLENSTVO)
      </div>
      <div class="body-grid">
        <div class="portrait-wrap">
          {portrait_html or '<div style="color:#78888b; font-size:12px; font-weight:600;">BEZ FOTKY</div>'}
        </div>
        <div>
          <dl class="details-table">
            <dt>Členské ID:</dt><dd>{member_id_str}</dd>
            <dt>Klub:</dt><dd>{club_name}</dd>
            <dt>Stav:</dt><dd>{status_str}</dd>
            <dt>Platnosť do:</dt><dd style="color:var(--primary); font-size:15px;">{valid_until_str}</dd>
            <dt>Vystavené:</dt><dd>{issued_at_str}</dd>
          </dl>
        </div>
        <div class="qr-wrap">
          {qr_img_html}
          <span class="qr-label">Overovací QR kód</span>
        </div>
      </div>
      <div class="actions-bar">
        <a class="btn btn-primary" href="{escape(card_image_url)}" target="_blank" rel="noopener noreferrer">Stiahnuť preukaz (JPG)</a>
        <a class="btn btn-secondary" href="{escape(card_pdf_url)}" target="_blank" rel="noopener noreferrer">Stiahnuť preukaz (PDF)</a>
      </div>
      <div class="doc-section">
        <h2>Právne dokumenty a výnimky</h2>
        <p style="margin:0 0 8px 0; font-size:14px;">
          Držiteľ tohto preukazu je oprávnený na výkon speleologickej činnosti podľa platnej výnimky:
        </p>
        <p style="margin:0;">
          📄 <a class="doc-link" href="{escape(legal_document_url)}" target="_blank" rel="noopener noreferrer">Všeobecná výnimka MŽP SR pre pohyb mimo vyznačených chodníkov (PDF)</a>
        </p>
      </div>
      <details>
        <summary>Kryptografické overenie podpisu (Ed25519 & Hash)</summary>
        <p style="margin:8px 0 4px 0;"><strong>Podpisový kľúč:</strong> {escape(str(issued_qr.key_id))}</p>
        <p style="margin:0 0 8px 0;"><strong>SHA-256 Hash:</strong> {escape(issued_qr.payload_hash)}</p>
        <pre>{payload_json}</pre>
      </details>
    </div>
  </div>
</body>
</html>"""
    return html.encode("utf-8")
