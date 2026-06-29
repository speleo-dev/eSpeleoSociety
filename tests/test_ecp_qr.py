import copy
from datetime import date, datetime, timezone
import unittest

from ecp_qr import (
    create_ecp_claim,
    generate_ecp_signing_key_pair,
    sign_ecp_claim,
    verify_ecp_payload,
)


class EcpQrTest(unittest.TestCase):
    def test_signed_ecp_payload_contains_basic_info_and_verifies_offline(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        claim = create_ecp_claim(
            member_id=123,
            display_name="Ada Lovelace",
            club_name="Speleo Club",
            status="active",
            valid_until=date(2027, 12, 31),
            paid_year=2027,
            issued_at=datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc),
        )

        payload = sign_ecp_claim(claim, private_key_pem, key_id="test-key")

        self.assertEqual(payload["claim"]["display_name"], "Ada Lovelace")
        self.assertEqual(payload["claim"]["club_name"], "Speleo Club")
        self.assertTrue(verify_ecp_payload(payload, public_key_pem, now=date(2026, 6, 18)))

    def test_ecp_claim_can_include_protected_online_verification_without_contact_data(self):
        claim = create_ecp_claim(
            member_id=123,
            display_name="Ada Lovelace",
            club_name="Speleo Club",
            status="active",
            valid_until=date(2027, 12, 31),
            verification_url="https://storage.example/ecp_verify/random-token.html",
            legal_documents=[{
                "name": "Vseobecna vynimka",
                "url": "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
            }],
        )

        self.assertEqual(claim["verification_url"], "https://storage.example/ecp_verify/random-token.html")
        self.assertEqual(claim["legal_documents"][0]["url"], "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf")
        self.assertNotIn("birth_date", claim)
        self.assertNotIn("email", claim)
        self.assertNotIn("phone", claim)
        self.assertNotIn("street", claim)

    def test_signed_ecp_payload_rejects_tampering(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        claim = create_ecp_claim(
            member_id=123,
            display_name="Ada Lovelace",
            club_name="Speleo Club",
            status="active",
            valid_until=date(2027, 12, 31),
        )
        payload = sign_ecp_claim(claim, private_key_pem, key_id="test-key")

        tampered = copy.deepcopy(payload)
        tampered["claim"]["status"] = "blocked"

        self.assertFalse(verify_ecp_payload(tampered, public_key_pem, now=date(2026, 6, 18)))

    def test_signed_ecp_payload_rejects_expired_claims(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        claim = create_ecp_claim(
            member_id=123,
            display_name="Ada Lovelace",
            club_name="Speleo Club",
            status="active",
            valid_until=date(2025, 12, 31),
        )
        payload = sign_ecp_claim(claim, private_key_pem, key_id="test-key")

        self.assertFalse(verify_ecp_payload(payload, public_key_pem, now=date(2026, 6, 18)))


if __name__ == "__main__":
    unittest.main()
