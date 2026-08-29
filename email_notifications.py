from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
import smtplib
import ssl

from ecp_documents import DEFAULT_LEGAL_DOCUMENT_URL


class EmailNotificationError(RuntimeError):
    pass


class SmtpConfigError(EmailNotificationError):
    pass


class SmtpSendError(EmailNotificationError):
    pass


@dataclass(frozen=True)
class SmtpConfig:
    server: str
    port: int
    user: str
    password: str
    from_email: str


def _required_secret(get_secret, key: str) -> str:
    value = get_secret(key)
    if value is None or str(value).strip() == "":
        raise SmtpConfigError(f"Missing SMTP secret: {key}")
    return str(value).strip()


def load_smtp_config(get_secret) -> SmtpConfig:
    server = _required_secret(get_secret, "smtp_server")
    port_raw = _required_secret(get_secret, "smtp_port")
    user = _required_secret(get_secret, "smtp_user")
    password = _required_secret(get_secret, "smtp_password")
    from_email = (get_secret("smtp_from") or user).strip()

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise SmtpConfigError("SMTP port must be an integer.") from exc

    return SmtpConfig(
        server=server,
        port=port,
        user=user,
        password=password,
        from_email=from_email,
    )


def _display_name(member) -> str:
    parts = [
        getattr(member, "title_prefix", None),
        getattr(member, "first_name", None),
        getattr(member, "last_name", None),
        getattr(member, "title_suffix", None),
    ]
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def _format_valid_until(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def build_ecp_issued_message(
    config: SmtpConfig,
    member,
    issued_qr=None,
    verification_url: str | None = None,
    card_image: bytes | None = None,
    card_pdf: bytes | None = None,
    card_image_url: str | None = None,
    card_pdf_url: str | None = None,
    legal_document_url: str = DEFAULT_LEGAL_DOCUMENT_URL,
    google_wallet_url: str | None = None,
    apple_wallet_url: str | None = None,
) -> EmailMessage:
    from html import escape

    recipient = getattr(member, "email", None)
    if not recipient:
        raise SmtpConfigError("Member email is missing.")

    display_name = _display_name(member) or "Člen SSS"
    valid_until = _format_valid_until(getattr(issued_qr, "valid_until", None))
    claim = getattr(issued_qr, "payload", {}).get("claim", {}) if getattr(issued_qr, "payload", None) else {}
    club_name = claim.get("club_name") or "Slovenská speleologická spoločnosť"
    member_id = str(claim.get("member_id") or getattr(member, "member_id", ""))

    plain_lines = [
        f"Dobrý deň {display_name},",
        "",
        "bol Vám vystavený elektronický členský preukaz eCP Slovenskej speleologickej spoločnosti.",
    ]
    if valid_until:
        plain_lines.extend(["", f"Platnosť preukazu: do {valid_until}."])
    if verification_url:
        plain_lines.extend(["", "Online overenie preukazu:", verification_url])
    if card_image_url or card_pdf_url:
        plain_lines.extend(["", "Preukaz je dostupný aj online:"])
        if card_image_url:
            plain_lines.append(f"JPG: {card_image_url}")
        if card_pdf_url:
            plain_lines.append(f"PDF: {card_pdf_url}")
    if legal_document_url:
        plain_lines.extend(["", "Všeobecná výnimka a právny dokument:", legal_document_url])
    if google_wallet_url or verification_url:
        plain_lines.extend(["", f"Pridať do Google Wallet: {google_wallet_url or verification_url}"])
    if apple_wallet_url or verification_url:
        plain_lines.extend(["", f"Pridať do Apple Wallet: {apple_wallet_url or verification_url}"])
    plain_lines.extend([
        "",
        "V prípade otázok kontaktujte správcu alebo svoj klub.",
        "",
        "Slovenská speleologická spoločnosť",
    ])

    # Wallet links (fallback to verification URL if direct JWT link not provided)
    gw_link = google_wallet_url or (f"{verification_url}#google-wallet" if verification_url else "#")
    aw_link = apple_wallet_url or (f"{verification_url}#apple-wallet" if verification_url else "#")

    html_content = f"""<!DOCTYPE html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Elektronický členský preukaz eCP</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background-color: #f3f6f5; color: #1a2926; line-height: 1.5;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <table width="600" style="max-width: 600px; width: 100%; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(11,74,70,0.08); border: 1px solid #d7dfdc;" border="0" cellspacing="0" cellpadding="0">
          <!-- Header -->
          <tr>
            <td style="background-color: #0b4a46; padding: 24px 30px; text-align: left;">
              <h1 style="color: #ffffff; margin: 0 0 6px 0; font-size: 22px; font-weight: 700;">Slovenská speleologická spoločnosť</h1>
              <p style="color: #c0ded8; margin: 0; font-size: 14px;">Elektronický členský preukaz eCP</p>
            </td>
          </tr>
          <tr><td style="height: 4px; background-color: #d5a93f;"></td></tr>
          
          <!-- Status -->
          <tr>
            <td style="background-color: #e8f7ee; padding: 12px 30px; color: #1b873f; font-weight: 700; font-size: 14px; border-bottom: 1px solid #c2ebd0;">
              ✓ PLATNÝ ČLENSKÝ PREUKAZ
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 28px 30px;">
              <p style="font-size: 16px; margin: 0 0 16px 0;">Dobrý deň <strong>{escape(display_name)}</strong>,</p>
              <p style="font-size: 14px; color: #3d4f4c; margin: 0 0 20px 0;">
                bol Vám vystavený oficiálny elektronický členský preukaz Slovenskej speleologickej spoločnosti (eCP).
              </p>

              <!-- Card Details Box -->
              <table width="100%" style="background: #f8faf9; border: 1px solid #e1e8e6; border-radius: 8px; margin-bottom: 24px;" cellpadding="10" cellspacing="0">
                <tr>
                  <td width="35%" style="color: #667775; font-size: 13px; font-weight: 600;">Členské ID:</td>
                  <td style="font-weight: 700; font-size: 14px;">{escape(member_id)}</td>
                </tr>
                <tr>
                  <td style="color: #667775; font-size: 13px; font-weight: 600;">Klub:</td>
                  <td style="font-weight: 600; font-size: 14px;">{escape(club_name)}</td>
                </tr>
                <tr>
                  <td style="color: #667775; font-size: 13px; font-weight: 600;">Platnosť do:</td>
                  <td style="font-weight: 700; font-size: 14px; color: #0b4a46;">{escape(valid_until or '-')}</td>
                </tr>
              </table>

              <!-- Digital Wallet Section -->
              <div style="margin-bottom: 24px; padding: 18px 20px; background: #f0f7f6; border-radius: 8px; border: 1px solid #cce3e0; text-align: center;">
                <p style="margin: 0 0 12px 0; font-weight: 700; font-size: 14px; color: #0b4a46;">Uložte si preukaz do mobilnej peňaženky:</p>
                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="center" style="padding: 4px;">
                      <a href="{escape(gw_link)}" target="_blank" style="display: inline-block; background-color: #0b4a46; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 13px; margin: 4px;">
                        🟢 Pridať do Google Wallet
                      </a>
                      <a href="{escape(aw_link)}" target="_blank" style="display: inline-block; background-color: #1f2328; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 13px; margin: 4px;">
                         Pridať do Apple Wallet
                      </a>
                    </td>
                  </tr>
                </table>
              </div>

              <!-- Action Links -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 20px;">
                <tr>
                  <td align="center">
                    {f'<a href="{escape(verification_url)}" target="_blank" style="display: inline-block; background: #d5a93f; color: #10201f; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 700; font-size: 14px; margin-bottom: 12px;">🌐 Zobraziť preukaz online</a><br>' if verification_url else ''}
                    {f'<a href="{escape(card_image_url)}" target="_blank" style="color: #0b5f86; font-size: 13px; margin-right: 14px; text-decoration: none; font-weight: 600;">🖼️ Stiahnuť kartu (JPG)</a>' if card_image_url else ''}
                    {f'<a href="{escape(card_pdf_url)}" target="_blank" style="color: #0b5f86; font-size: 13px; text-decoration: none; font-weight: 600;">📄 Stiahnuť kartu (PDF)</a>' if card_pdf_url else ''}
                  </td>
                </tr>
              </table>

              <!-- Legal Notice -->
              <p style="font-size: 12px; color: #667775; border-top: 1px solid #e1e8e6; padding-top: 14px; margin: 20px 0 0 0;">
                Držiteľ tohto preukazu je oprávnený na výkon speleologickej činnosti. <br>
                <a href="{escape(legal_document_url)}" target="_blank" style="color: #0b5f86; text-decoration: underline;">Všeobecná výnimka MŽP SR pre pohyb mimo vyznačených chodníkov (PDF)</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #fafcfb; border-top: 1px solid #d7dfdc; padding: 16px 30px; text-align: center; font-size: 12px; color: #889996;">
              Tento e-mail bol vygenerovaný automaticky systémom eSpeleoSociety. &bull; <a href="https://sss.sk" style="color: #667775; text-decoration: underline;">sss.sk</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    message = EmailMessage()
    message["From"] = config.from_email
    message["To"] = recipient
    message["Subject"] = "Vystavený elektronický členský preukaz eCP"
    message.set_content("\n".join(plain_lines))
    message.add_alternative(html_content, subtype="html")

    if card_image:
        message.add_attachment(
            card_image,
            maintype="image",
            subtype="jpeg",
            filename="ecp-preukaz.jpg",
        )
    if card_pdf:
        message.add_attachment(
            card_pdf,
            maintype="application",
            subtype="pdf",
            filename="ecp-preukaz.pdf",
        )
    return message


def send_email(config: SmtpConfig, message: EmailMessage, smtp_factory=None):
    smtp_factory = smtp_factory or smtplib.SMTP
    try:
        if config.port == 465:
            with smtplib.SMTP_SSL(config.server, config.port, timeout=20) as smtp:
                smtp.login(config.user, config.password)
                smtp.send_message(message)
            return

        with smtp_factory(config.server, config.port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(config.user, config.password)
            smtp.send_message(message)
    except Exception as exc:
        raise SmtpSendError(f"SMTP send failed: {exc}") from exc


def send_ecp_issued_email(
    member,
    issued_qr,
    get_secret,
    smtp_factory=None,
    verification_url: str | None = None,
    card_image: bytes | None = None,
    card_pdf: bytes | None = None,
    card_image_url: str | None = None,
    card_pdf_url: str | None = None,
    legal_document_url: str = DEFAULT_LEGAL_DOCUMENT_URL,
):
    config = load_smtp_config(get_secret)
    message = build_ecp_issued_message(
        config,
        member,
        issued_qr=issued_qr,
        verification_url=verification_url,
        card_image=card_image,
        card_pdf=card_pdf,
        card_image_url=card_image_url,
        card_pdf_url=card_pdf_url,
        legal_document_url=legal_document_url,
    )
    send_email(config, message, smtp_factory=smtp_factory)
