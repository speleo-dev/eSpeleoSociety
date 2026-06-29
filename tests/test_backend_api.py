import json
import unittest
from types import SimpleNamespace

import jwt

from backend.app import ApiApp


class EmptyRepository:
    def fetch_clubs(self):
        return []


class ClubRepository:
    def __init__(self):
        self.clubs = [
            SimpleNamespace(
                club_id=1,
                name="Alpha",
                street="Street 1",
                city="Nitra",
                zip_code="94901",
                country="SK",
                email="alpha@example.sk",
                phone="0901",
                webpage="https://alpha.example.sk",
                president_name="Ada",
                member_count=7,
            ),
            SimpleNamespace(
                club_id=2,
                name="Beta",
                street="Street 2",
                city="Bratislava",
                zip_code="81101",
                country="SK",
                email="beta@example.sk",
                phone="0902",
                webpage="",
                president_name="Grace",
                member_count=3,
            ),
        ]
        self.members_by_club = {
            1: [
                SimpleNamespace(
                    member_id=101,
                    status="active",
                    title_prefix="",
                    first_name="Ada",
                    last_name="Lovelace",
                    title_suffix="",
                    email="ada@example.sk",
                    phone="0901",
                    primary_club_id=1,
                    is_president=True,
                    ecp_hash="ecp-1",
                )
            ],
            2: [],
        }
        self.ecp_verifications = {
            "token-123456789": {
                "member_id": 101,
                "display_name": "Ada Lovelace",
                "club_name": "Alpha",
                "status": "active",
                "valid_until": "2027-06-29",
                "portrait_url": "https://storage.example/portrait.jpg",
                "card_image_url": "https://storage.example/card.jpg",
                "card_pdf_url": "https://storage.example/card.pdf",
                "legal_document_url": "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
                "qr_payload_hash": "a" * 64,
                "email": "ada@example.sk",
                "phone": "0901",
                "street": "Street 1",
            }
        }

    def fetch_clubs(self):
        return self.clubs

    def fetch_members(self, club_id: int):
        return self.members_by_club.get(club_id, [])

    def fetch_ecp_verification_by_token(self, token: str):
        return self.ecp_verifications.get(token)


def make_token(secret: str, **claims) -> str:
    payload = {
        "sub": "admin-1",
        "aud": "espeleo-api",
        "iss": "espeleo-test",
        **claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class BackendApiTest(unittest.TestCase):
    def test_health_endpoint_is_public(self):
        app = ApiApp(repository=EmptyRepository(), jwt_secret="unit-test-secret")

        response = app.handle_request("GET", "/api/v1/health", headers={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body), {"status": "ok", "version": "v1"})

    def test_list_clubs_requires_bearer_token(self):
        app = ApiApp(repository=ClubRepository(), jwt_secret="unit-test-secret")

        response = app.handle_request("GET", "/api/v1/clubs", headers={})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.body)["error"]["code"], "missing_bearer_token")

    def test_admin_can_list_clubs_with_cursor_pagination(self):
        secret = "unit-test-secret"
        token = make_token(secret, roles=["admin"])
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "GET",
            "/api/v1/clubs",
            headers={"Authorization": f"Bearer {token}"},
            query={"limit": "1"},
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["items"][0]["name"], "Alpha")
        self.assertIsNotNone(payload["nextCursor"])

    def test_club_president_can_list_members_only_for_assigned_club(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="president-1", roles=["club_president"], club_ids=[1])
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        allowed = app.handle_request(
            "GET",
            "/api/v1/clubs/1/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        denied = app.handle_request(
            "GET",
            "/api/v1/clubs/2/members",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(json.loads(allowed.body)["items"][0]["firstName"], "Ada")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(json.loads(denied.body)["error"]["code"], "forbidden")

    def test_ecp_verify_token_returns_public_detail_without_contact_data(self):
        app = ApiApp(repository=ClubRepository(), jwt_secret="unit-test-secret")

        response = app.handle_request("GET", "/api/v1/ecp/verify/token-123456789", headers={})

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["displayName"], "Ada Lovelace")
        self.assertIn("vynimka.pdf", payload["legalDocumentUrl"])
        self.assertNotIn("email", payload)
        self.assertNotIn("phone", payload)
        self.assertNotIn("street", payload)


if __name__ == "__main__":
    unittest.main()
