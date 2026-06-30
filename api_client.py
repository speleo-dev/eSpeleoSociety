import uuid

import requests


class ApiClientError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str, request_id: str | None = None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.request_id = request_id
        self.payload = payload


class ApiClient:
    def __init__(self, base_url: str, token_provider, session=None, timeout: int | float = 10):
        self.base_url = str(base_url).rstrip("/")
        self.token_provider = token_provider
        self.session = session or requests.Session()
        self.timeout = timeout

    def list_clubs(self, limit: int = 50, cursor: str | None = None, filter_text: str = ""):
        return self._request(
            "GET",
            "/clubs",
            params={"limit": limit, "cursor": cursor, "filter": filter_text or None},
        )

    def list_club_members(self, club_id: int, limit: int = 50, cursor: str | None = None, filter_text: str = ""):
        return self._request(
            "GET",
            f"/clubs/{club_id}/members",
            params={"limit": limit, "cursor": cursor, "filter": filter_text or None},
        )

    def get_my_profile(self):
        return self._request("GET", "/me")

    def request_my_ecp(self, photo_base64: str, content_type: str, gdpr_consent: bool = True, notifications_enabled: bool = True):
        return self._request(
            "POST",
            "/me/ecp-requests",
            json={
                "photoBase64": photo_base64,
                "contentType": content_type,
                "gdprConsent": gdpr_consent,
                "notificationsEnabled": notifications_enabled,
            },
        )

    def update_member(self, member_id: int, **fields):
        return self._request("PATCH", f"/members/{member_id}", json=fields)

    def _request(self, method: str, path: str, params=None, json=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "X-Request-ID": f"req_{uuid.uuid4().hex}",
        }
        token = self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.session.request(
            method,
            url,
            headers=headers,
            params=self._compact(params or {}),
            json=json,
            timeout=self.timeout,
        )
        payload = self._decode_json(response)
        if response.status_code >= 400:
            error = payload.get("error") if isinstance(payload, dict) else None
            error = error or {}
            raise ApiClientError(
                status_code=response.status_code,
                code=error.get("code") or "api_error",
                message=error.get("message") or f"API request failed with HTTP {response.status_code}.",
                request_id=error.get("requestId") or response.headers.get("X-Request-ID"),
                payload=payload,
            )
        return payload

    def _access_token(self) -> str:
        if callable(self.token_provider):
            return str(self.token_provider() or "").strip()
        return str(self.token_provider or "").strip()

    def _compact(self, values: dict) -> dict:
        return {key: value for key, value in values.items() if value is not None}

    def _decode_json(self, response):
        try:
            return response.json()
        except ValueError:
            return {}
