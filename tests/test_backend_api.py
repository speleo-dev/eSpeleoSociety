import base64
import json
import time
import unittest
from types import SimpleNamespace

import jwt

from backend.app import ApiApp
from backend.repository import DuplicatePendingEcpRequestError


class EmptyRepository:
    def fetch_clubs(self):
        return []


class ClubRepository:
    def __init__(self):
        self.list_calls = []
        self.member_list_calls = []
        self.profile_calls = []
        self.membership_checks = []
        self.updated_member_profiles = []
        self.created_ecp_requests = []
        self.reject_duplicate_ecp_request = False
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
            2: [
                SimpleNamespace(
                    member_id=201,
                    status="active",
                    title_prefix="",
                    first_name="Grace",
                    last_name="Hopper",
                    title_suffix="",
                    email="grace@example.sk",
                    phone="0902",
                    primary_club_id=2,
                    is_president=True,
                    ecp_hash="ecp-2",
                )
            ],
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
        self.member_profiles = {
            101: {
                "member_id": 101,
                "status": "active",
                "title_prefix": "",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "title_suffix": "",
                "display_name": "Ada Lovelace",
                "email": "ada@example.sk",
                "phone": "0901",
                "primary_club_id": 1,
                "primary_club_name": "Alpha",
                "portrait_url": "https://storage.example/portrait.jpg",
                "ecp_active": True,
                "ecp_valid_until": "2027-06-29",
                "ecp_verification_url": "https://storage.example/ecp_verify/token.html",
                "ecp_card_image_url": "https://storage.example/card.jpg",
                "ecp_card_pdf_url": "https://storage.example/card.pdf",
                "ecp_wallet_status": "issued",
                "pending_ecp_request_id": 55,
                "pending_ecp_request_status": "pending",
                "pending_ecp_request_date": "2026-06-29",
                "ecp_hash": "must-not-leak",
                "birth_date_encrypted": "must-not-leak",
                "street": "must-not-leak",
            }
        }

    def fetch_clubs(self):
        return self.clubs

    def list_clubs(self, limit: int, cursor=None, filter_text: str = ""):
        self.list_calls.append({
            "limit": limit,
            "cursor": cursor,
            "filter_text": filter_text,
        })
        items = self.clubs
        if filter_text:
            items = [
                club for club in items
                if filter_text.casefold() in f"{club.name} {club.city} {club.email}".casefold()
            ]
        page = items[:limit]
        next_cursor = "next-club-cursor" if len(items) > limit else None
        return page, next_cursor

    def fetch_members(self, club_id: int):
        return self.members_by_club.get(club_id, [])

    def list_club_members(self, club_id: int, limit: int, cursor=None, filter_text: str = ""):
        self.member_list_calls.append({
            "club_id": club_id,
            "limit": limit,
            "cursor": cursor,
            "filter_text": filter_text,
        })
        items = self.members_by_club.get(club_id, [])
        if filter_text:
            items = [
                member for member in items
                if filter_text.casefold() in f"{member.first_name} {member.last_name} {member.email}".casefold()
            ]
        page = items[:limit]
        next_cursor = "next-member-cursor" if len(items) > limit else None
        return page, next_cursor

    def member_belongs_to_any_club(self, member_id: int, club_ids):
        club_ids = set(club_ids)
        self.membership_checks.append({
            "member_id": member_id,
            "club_ids": club_ids,
        })
        return any(
            member.member_id == member_id and club_id in club_ids
            for club_id, members in self.members_by_club.items()
            for member in members
        )

    def update_member_profile(self, member_id: int, changes: dict):
        self.updated_member_profiles.append({
            "member_id": member_id,
            "changes": dict(changes),
        })
        for members in self.members_by_club.values():
            for member in members:
                if member.member_id == member_id:
                    for key, value in changes.items():
                        if key == "member_status":
                            member.status = value
                        elif hasattr(member, key):
                            setattr(member, key, value)
                    return member
        return None

    def fetch_member_portal_profile(self, member_id: int):
        self.profile_calls.append(member_id)
        return self.member_profiles.get(member_id)

    def create_member_ecp_request(self, member_id: int, photo_bytes: bytes, content_type: str, gdpr_consent=True, notifications_enabled=True):
        if self.reject_duplicate_ecp_request:
            raise DuplicatePendingEcpRequestError(55)
        request = {
            "request_id": 77,
            "member_id": member_id,
            "ecp_record_id": 88,
            "photo_hash": "photo-hash-1",
            "status": "pending",
            "request_date": "2026-06-29",
            "photo_url": "https://storage.example/ecp-request-photos/photo-hash-1.jpg",
        }
        self.created_ecp_requests.append({
            "member_id": member_id,
            "photo_bytes": photo_bytes,
            "content_type": content_type,
            "gdpr_consent": gdpr_consent,
            "notifications_enabled": notifications_enabled,
        })
        return request

    def fetch_ecp_verification_by_token(self, token: str):
        return self.ecp_verifications.get(token)


class AuditSink:
    def __init__(self):
        self.events = []

    def record_api_audit_event(self, event):
        self.events.append(event)


def make_token(secret: str, **claims) -> str:
    payload = {
        "sub": "admin-1",
        "aud": "espeleo-api",
        "iss": "espeleo-test",
        "exp": int(time.time()) + 3600,
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
        audit_sink = AuditSink()
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret, audit_sink=audit_sink)

        response = app.handle_request(
            "GET",
            "/api/v1/clubs",
            headers={"Authorization": f"Bearer {token}"},
            query={"limit": "1", "filter": "nit"},
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["items"][0]["name"], "Alpha")
        self.assertIsNone(payload["nextCursor"])
        self.assertEqual(app.repository.list_calls, [{
            "limit": 1,
            "cursor": None,
            "filter_text": "nit",
        }])
        self.assertEqual(len(audit_sink.events), 1)
        self.assertEqual(audit_sink.events[0].route, "/api/v1/clubs")
        self.assertEqual(audit_sink.events[0].status_code, 200)
        self.assertEqual(audit_sink.events[0].subject, "admin-1")
        self.assertEqual(audit_sink.events[0].roles, ("admin",))

    def test_club_president_can_list_members_only_for_assigned_club(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="president-1", roles=["club_president"], club_ids=[1])
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        allowed = app.handle_request(
            "GET",
            "/api/v1/clubs/1/members",
            headers={"Authorization": f"Bearer {token}"},
            query={"limit": "1", "cursor": "member-cursor", "filter": "ada"},
        )
        denied = app.handle_request(
            "GET",
            "/api/v1/clubs/2/members",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(json.loads(allowed.body)["items"][0]["firstName"], "Ada")
        self.assertEqual(app.repository.member_list_calls, [{
            "club_id": 1,
            "limit": 1,
            "cursor": "member-cursor",
            "filter_text": "ada",
        }])
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(json.loads(denied.body)["error"]["code"], "forbidden")

    def test_admin_can_patch_member_profile(self):
        secret = "unit-test-secret"
        token = make_token(secret, roles=["admin"])
        repository = ClubRepository()
        audit_sink = AuditSink()
        app = ApiApp(repository=repository, jwt_secret=secret, audit_sink=audit_sink)

        response = app.handle_request(
            "PATCH",
            "/api/v1/members/101",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({
                "firstName": "Augusta",
                "status": "inactive",
                "phone": "0909",
                "discountedMembership": True,
            }),
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["firstName"], "Augusta")
        self.assertEqual(payload["status"], "inactive")
        self.assertEqual(payload["phone"], "0909")
        self.assertEqual(repository.updated_member_profiles, [{
            "member_id": 101,
            "changes": {
                "first_name": "Augusta",
                "member_status": "inactive",
                "phone": "0909",
                "discounted_membership": True,
            },
        }])
        self.assertEqual(audit_sink.events[0].route, "/api/v1/members/{member_id}")

    def test_club_president_can_patch_only_own_club_member(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="president-1", roles=["club_president"], club_ids=[1])
        repository = ClubRepository()
        app = ApiApp(repository=repository, jwt_secret=secret)

        allowed = app.handle_request(
            "PATCH",
            "/api/v1/members/101",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({"email": "ada.new@example.sk"}),
        )
        denied = app.handle_request(
            "PATCH",
            "/api/v1/members/201",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({"email": "grace.new@example.sk"}),
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(json.loads(allowed.body)["email"], "ada.new@example.sk")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(json.loads(denied.body)["error"]["code"], "forbidden")
        self.assertEqual(repository.membership_checks, [
            {"member_id": 101, "club_ids": {1}},
            {"member_id": 201, "club_ids": {1}},
        ])
        self.assertEqual(len(repository.updated_member_profiles), 1)

    def test_patch_member_rejects_unknown_fields(self):
        secret = "unit-test-secret"
        token = make_token(secret, roles=["admin"])
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "PATCH",
            "/api/v1/members/101",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({"ecpHash": "must-not-be-writable"}),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.body)["error"]["code"], "unknown_member_update_field")

    def test_member_can_fetch_own_portal_profile(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        audit_sink = AuditSink()
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret, audit_sink=audit_sink)

        response = app.handle_request(
            "GET",
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["id"], 101)
        self.assertEqual(payload["displayName"], "Ada Lovelace")
        self.assertEqual(payload["primaryClub"], {"id": 1, "name": "Alpha"})
        self.assertTrue(payload["hasEcp"])
        self.assertEqual(payload["ecp"]["validUntil"], "2027-06-29")
        self.assertEqual(payload["pendingEcpRequest"]["id"], 55)
        self.assertNotIn("ecpHash", payload)
        self.assertNotIn("birthDate", payload)
        self.assertNotIn("street", payload)
        self.assertEqual(app.repository.profile_calls, [101])
        self.assertEqual(audit_sink.events[0].route, "/api/v1/me")

    def test_member_profile_requires_member_identity_claim(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-without-link", roles=["member"])
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "GET",
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.body)["error"]["code"], "member_identity_required")

    def test_member_can_create_ecp_request_with_photo_upload(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        audit_sink = AuditSink()
        repository = ClubRepository()
        app = ApiApp(repository=repository, jwt_secret=secret, audit_sink=audit_sink)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({
                "photoBase64": "cG9ydHJhaXQ=",
                "contentType": "image/jpeg",
                "gdprConsent": True,
                "notificationsEnabled": False,
            }),
        )

        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.body)
        self.assertEqual(payload["id"], 77)
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["ecpRecordId"], 88)
        self.assertEqual(repository.created_ecp_requests, [{
            "member_id": 101,
            "photo_bytes": b"portrait",
            "content_type": "image/jpeg",
            "gdpr_consent": True,
            "notifications_enabled": False,
        }])
        self.assertEqual(audit_sink.events[0].route, "/api/v1/me/ecp-requests")

    def test_ecp_request_rejects_missing_photo(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({}),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.body)["error"]["code"], "photo_required")

    def test_ecp_request_rejects_non_object_json_body(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps([]),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.body)["error"]["code"], "invalid_request_body")

    def test_ecp_request_requires_explicit_gdpr_consent(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({
                "photoBase64": "cG9ydHJhaXQ=",
                "contentType": "image/jpeg",
                "gdprConsent": False,
            }),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.body)["error"]["code"], "gdpr_consent_required")

    def test_ecp_request_rejects_oversized_photo(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        app = ApiApp(repository=ClubRepository(), jwt_secret=secret)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({
                "photoBase64": base64.b64encode(b"x" * ((5 * 1024 * 1024) + 1)).decode("ascii"),
                "contentType": "image/jpeg",
                "gdprConsent": True,
            }),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.body)["error"]["code"], "photo_too_large")

    def test_ecp_request_rejects_duplicate_pending_request(self):
        secret = "unit-test-secret"
        token = make_token(secret, sub="member-101", roles=["member"], member_id=101)
        repository = ClubRepository()
        repository.reject_duplicate_ecp_request = True
        app = ApiApp(repository=repository, jwt_secret=secret)

        response = app.handle_request(
            "POST",
            "/api/v1/me/ecp-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            body=json.dumps({
                "photoBase64": "cG9ydHJhaXQ=",
                "contentType": "image/jpeg",
                "gdprConsent": True,
            }),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.body)["error"]["code"], "ecp_request_already_pending")
        self.assertEqual(repository.created_ecp_requests, [])

    def test_ecp_verify_token_returns_public_detail_without_contact_data(self):
        audit_sink = AuditSink()
        app = ApiApp(repository=ClubRepository(), jwt_secret="unit-test-secret", audit_sink=audit_sink)

        response = app.handle_request("GET", "/api/v1/ecp/verify/token-123456789", headers={})

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["displayName"], "Ada Lovelace")
        self.assertIn("vynimka.pdf", payload["legalDocumentUrl"])
        self.assertNotIn("email", payload)
        self.assertNotIn("phone", payload)
        self.assertNotIn("street", payload)
        self.assertEqual(audit_sink.events[0].route, "/api/v1/ecp/verify/{token}")
        self.assertNotIn("token-123456789", repr(audit_sink.events[0]))
        self.assertEqual(audit_sink.events[0].subject, "anonymous")


if __name__ == "__main__":
    unittest.main()
