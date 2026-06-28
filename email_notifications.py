from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
import smtplib
import ssl


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


def build_ecp_issued_message(config: SmtpConfig, member, issued_qr=None) -> EmailMessage:
    recipient = getattr(member, "email", None)
    if not recipient:
        raise SmtpConfigError("Member email is missing.")

    display_name = _display_name(member) or "clen"
    valid_until = _format_valid_until(getattr(issued_qr, "valid_until", None))

    lines = [
        f"Dobry den {display_name},",
        "",
        "bol Vam vystaveny elektronicky clensky preukaz eCP.",
    ]
    if valid_until:
        lines.extend(["", f"Platnost preukazu: do {valid_until}."])
    lines.extend([
        "",
        "V pripade otazok kontaktujte spravcu alebo svoj klub.",
        "",
        "eSpeleoSociety",
    ])

    message = EmailMessage()
    message["From"] = config.from_email
    message["To"] = recipient
    message["Subject"] = "Vystaveny elektronicky clensky preukaz eCP"
    message.set_content("\n".join(lines))
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


def send_ecp_issued_email(member, issued_qr, get_secret, smtp_factory=None):
    config = load_smtp_config(get_secret)
    message = build_ecp_issued_message(config, member, issued_qr=issued_qr)
    send_email(config, message, smtp_factory=smtp_factory)
