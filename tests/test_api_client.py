import unittest

from api_client import ApiClient, ApiClientError


class FakeResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = "" if payload is None else str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append({
            "method": method,
            "url": url,
            **kwargs,
        })
        return self.responses.pop(0)


class ApiClientTest(unittest.TestCase):
    def test_list_club_members_sends_bearer_token_and_query_params(self):
        session = FakeSession([
            FakeResponse(200, {"items": [], "nextCursor": None}),
        ])
        client = ApiClient(
            "https://api.example.test/api/v1",
            token_provider=lambda: "access-token-1",
            session=session,
            timeout=3,
        )

        payload = client.list_club_members(7, limit=25, cursor="cursor-1", filter_text="ada")

        self.assertEqual(payload, {"items": [], "nextCursor": None})
        self.assertEqual(session.requests[0]["method"], "GET")
        self.assertEqual(session.requests[0]["url"], "https://api.example.test/api/v1/clubs/7/members")
        self.assertEqual(session.requests[0]["params"], {
            "limit": 25,
            "cursor": "cursor-1",
            "filter": "ada",
        })
        self.assertEqual(session.requests[0]["headers"]["Authorization"], "Bearer access-token-1")
        self.assertEqual(session.requests[0]["timeout"], 3)

    def test_update_member_uses_patch_with_camel_case_payload(self):
        session = FakeSession([
            FakeResponse(200, {"id": 101, "firstName": "Ada", "status": "active"}),
        ])
        client = ApiClient("https://api.example.test/api/v1", token_provider="static-token", session=session)

        payload = client.update_member(101, firstName="Ada", status="active")

        self.assertEqual(payload["id"], 101)
        self.assertEqual(session.requests[0]["method"], "PATCH")
        self.assertEqual(session.requests[0]["url"], "https://api.example.test/api/v1/members/101")
        self.assertEqual(session.requests[0]["json"], {
            "firstName": "Ada",
            "status": "active",
        })

    def test_error_response_raises_structured_exception(self):
        session = FakeSession([
            FakeResponse(
                403,
                {
                    "error": {
                        "code": "forbidden",
                        "message": "No access.",
                        "requestId": "req_1",
                    },
                },
            ),
        ])
        client = ApiClient("https://api.example.test/api/v1", token_provider=lambda: "token", session=session)

        with self.assertRaises(ApiClientError) as raised:
            client.list_clubs()

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.code, "forbidden")
        self.assertEqual(raised.exception.message, "No access.")
        self.assertEqual(raised.exception.request_id, "req_1")


if __name__ == "__main__":
    unittest.main()
