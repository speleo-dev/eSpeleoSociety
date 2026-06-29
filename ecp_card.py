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


def public_gcs_url(bucket_name: str, blob_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"


def _format_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _member_display_name(member) -> str:
    parts = [
        getattr(member, "title_prefix", None),
        getattr(member, "first_name", None),
        getattr(member, "last_name", None),
        getattr(member, "title_suffix", None),
    ]
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


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
    draw.text((56, 78), "Elektronicky clensky preukaz", fill="#dbe8e4", font=_font(19))

    portrait_size = (PORTRAIT_BOX[2] - PORTRAIT_BOX[0], PORTRAIT_BOX[3] - PORTRAIT_BOX[1])
    portrait = _load_portrait(portrait_image, portrait_size)
    card.paste(portrait, (PORTRAIT_BOX[0], PORTRAIT_BOX[1]))
    draw.rectangle(PORTRAIT_BOX, outline="#6f7d82", width=2)

    qr = Image.open(BytesIO(issued_qr.qr_png)).convert("RGB")
    qr = qr.resize((QR_BOX[2] - QR_BOX[0], QR_BOX[3] - QR_BOX[1]), Image.Resampling.NEAREST)
    card.paste(qr, (QR_BOX[0], QR_BOX[1]))
    draw.rectangle(QR_BOX, outline="#0b4a46", width=2)

    display_name = _member_display_name(member) or "Clen"
    club_name = getattr(club, "name", "") or ""
    claim = issued_qr.payload.get("claim", {})

    draw.text((330, 168), display_name, fill="#10201f", font=_font(34, True))
    draw.text((330, 216), f"Klub: {club_name}", fill="#243533", font=_font(22))
    draw.text((330, 258), f"Status: {claim.get('status', '')}", fill="#243533", font=_font(22))
    draw.text((330, 300), f"Clenske ID: {claim.get('member_id', '')}", fill="#243533", font=_font(22))
    draw.text((330, 342), f"Platnost do: {_format_date(claim.get('valid_until'))}", fill="#243533", font=_font(22, True))
    draw.text((330, 384), f"Vydane: {_format_date(claim.get('issued_at'))}", fill="#526260", font=_font(18))

    draw.text((735, 404), "Rovnaky QR plati pre JPG, PDF aj Wallet.", fill="#243533", font=_font(16))
    draw.text((56, 552), "Offline QR obsahuje iba minimalne podpisane udaje a online kontrolny link.", fill="#526260", font=_font(17))
    draw.text((56, 582), "Online detail je tokenizovana staticka stranka bez verejneho indexovania.", fill="#526260", font=_font(17))

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
    qr_url: str,
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
    portrait_html = ""
    if portrait_url:
        portrait_html = f'<img class="portrait" src="{escape(portrait_url)}" alt="Portret clena">'

    payload_json = escape(json.dumps(issued_qr.payload, sort_keys=True, ensure_ascii=False))
    html = f"""<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <meta name="referrer" content="no-referrer">
  <title>eCP kontrola - {escape(_member_display_name(member) or 'clen')}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background: #f4f7f6; color: #14211f; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 32px 20px; }}
    header {{ background: #0b4a46; color: white; padding: 24px 28px; border-radius: 8px 8px 0 0; }}
    section {{ background: white; border: 1px solid #d7dfdc; border-top: 0; padding: 24px 28px; }}
    .grid {{ display: grid; grid-template-columns: 220px 1fr; gap: 24px; align-items: start; }}
    .portrait {{ width: 220px; max-height: 300px; object-fit: cover; border: 1px solid #9dacaa; }}
    dl {{ display: grid; grid-template-columns: 180px 1fr; gap: 10px 18px; margin: 0; }}
    dt {{ font-weight: 700; color: #475956; }}
    dd {{ margin: 0; }}
    a {{ color: #0b5f86; }}
    .assets {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }}
    .payload {{ word-break: break-word; color: #526260; font-size: 12px; }}
    @media (max-width: 700px) {{ .grid, dl {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(_member_display_name(member) or 'Clen')}</h1>
      <p>Online kontrola elektronickeho clenskeho preukazu eCP</p>
    </header>
    <section class="grid">
      <div>{portrait_html}</div>
      <div>
        <dl>
          <dt>Clenske ID</dt><dd>{escape(str(claim.get('member_id', '')))}</dd>
          <dt>Klub</dt><dd>{escape(getattr(club, 'name', '') or '')}</dd>
          <dt>Status</dt><dd>{escape(str(claim.get('status', '')))}</dd>
          <dt>Platnost do</dt><dd>{escape(str(claim.get('valid_until', '')))}</dd>
          <dt>Vydane</dt><dd>{escape(str(claim.get('issued_at', '')))}</dd>
          <dt>Podpisovy kluc</dt><dd>{escape(str(issued_qr.key_id))}</dd>
          <dt>Hash payloadu</dt><dd>{escape(issued_qr.payload_hash)}</dd>
        </dl>
        <div class="assets">
          <a href="{escape(qr_url)}" rel="noopener noreferrer">QR PNG</a>
          <a href="{escape(card_image_url)}" rel="noopener noreferrer">Preukaz JPG</a>
          <a href="{escape(card_pdf_url)}" rel="noopener noreferrer">Preukaz PDF</a>
        </div>
      </div>
    </section>
    <section>
      <h2>Dokumenty</h2>
      <ul>{document_links}</ul>
      <p>Primarny dokument: <a href="{escape(legal_document_url)}" rel="noopener noreferrer">vynimka.pdf</a></p>
    </section>
    <section>
      <h2>Podpisany QR payload</h2>
      <p class="payload">{payload_json}</p>
    </section>
  </main>
</body>
</html>"""
    return html.encode("utf-8")
