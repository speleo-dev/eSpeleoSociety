from datetime import date
from types import SimpleNamespace
import unittest

from email_notifications import (
    SmtpConfigError,
    build_ecp_issued_message,
    load_smtp_config,
    send_ecp_issued_email,
)


class FakeSmtp:
    instances = []

    def __init__(self, server, port, timeout=None):
        self.server = server
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.messages = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return None

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, message):
        self.messages.append(message)


class EmailNotificationsTest(unittest.TestCase):
    def setUp(self):
        FakeSmtp.instances.clear()

    def test_load_smtp_config_requires_fields(self):
        with self.assertRaises(SmtpConfigError):
            load_smtp_config({}.get)

        with self.assertRaises(SmtpConfigError):
            load_smtp_config({
                "smtp_server": "smtp.example.org",
                "smtp_port": "not-a-port",
                "smtp_user": "user",
                "smtp_password": "secret",
            }.get)

    def test_build_ecp_issued_message_contains_member_and_validity(self):
        config = load_smtp_config({
            "smtp_server": "smtp.example.org",
            "smtp_port": "587",
            "smtp_user": "issuer@example.org",
            "smtp_password": "secret",
        }.get)
        member = SimpleNamespace(
            title_prefix="Ing.",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="",
            email="ada@example.org",
        )
        issued_qr = SimpleNamespace(valid_until=date(2027, 6, 28))

        message = build_ecp_issued_message(config, member, issued_qr)

        self.assertEqual(message["To"], "ada@example.org")
        self.assertEqual(message["From"], "issuer@example.org")
        self.assertIn("eCP", message["Subject"])
        body = message.get_content()
        self.assertIn("Ada Lovelace", body)
        self.assertIn("2027-06-28", body)

    def test_send_ecp_issued_email_uses_starttls_and_authenticates(self):
        member = SimpleNamespace(
            title_prefix="",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="",
            email="ada@example.org",
        )
        issued_qr = SimpleNamespace(valid_until=date(2027, 6, 28))
        secrets = {
            "smtp_server": "smtp.example.org",
            "smtp_port": "587",
            "smtp_user": "issuer@example.org",
            "smtp_password": "secret",
        }

        send_ecp_issued_email(member, issued_qr, secrets.get, smtp_factory=FakeSmtp)

        self.assertEqual(len(FakeSmtp.instances), 1)
        smtp = FakeSmtp.instances[0]
        self.assertEqual((smtp.server, smtp.port), ("smtp.example.org", 587))
        self.assertTrue(smtp.started_tls)
        self.assertEqual(smtp.login_args, ("issuer@example.org", "secret"))
        self.assertEqual(len(smtp.messages), 1)
        self.assertEqual(smtp.messages[0]["To"], "ada@example.org")


if __name__ == "__main__":
    unittest.main()
