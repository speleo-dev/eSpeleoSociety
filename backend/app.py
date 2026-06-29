from dataclasses import dataclass
import json
import uuid

from backend.audit import AuditEvent
from backend.auth import AuthError, authenticate_bearer, require_any_role
from backend.pagination import paginate_items, parse_limit
from backend.serializers import club_to_api, ecp_verification_to_api, member_to_api


API_VERSION = "v1"


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    body: str
    headers: dict[str, str]


def json_response(status_code: int, payload: dict) -> ApiResponse:
    return ApiResponse(
        status_code=status_code,
        body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


def error_response(status_code: int, code: str, message: str, request_id: str) -> ApiResponse:
    return json_response(
        status_code,
        {
            "error": {
                "code": code,
                "message": message,
                "requestId": request_id,
            }
        },
    )


class ApiApp:
    def __init__(
        self,
        repository,
        jwt_secret: str,
        issuer: str = "espeleo-test",
        audience: str = "espeleo-api",
        audit_sink=None,
    ):
        self.repository = repository
        self.jwt_secret = jwt_secret
        self.issuer = issuer
        self.audience = audience
        self.audit_sink = audit_sink or repository

    def handle_request(self, method: str, path: str, headers=None, query=None) -> ApiResponse:
        headers = headers or {}
        query = query or {}
        request_id = headers.get("X-Request-ID") or headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
        context = None
        error_code = None
        route = self._route_template(method, path)
        try:
            if method == "GET" and path == "/api/v1/health":
                response = json_response(200, {"status": "ok", "version": API_VERSION})
            else:
                ecp_verify_token = self._match_ecp_verify_path(method, path)
                if ecp_verify_token is not None:
                    response = self._verify_ecp_token(ecp_verify_token, request_id)
                else:
                    context = authenticate_bearer(
                        headers,
                        jwt_secret=self.jwt_secret,
                        audience=self.audience,
                        issuer=self.issuer,
                    )
                    if method == "GET" and path == "/api/v1/clubs":
                        response = self._list_clubs(query, context)
                    else:
                        club_members_id = self._match_club_members_path(method, path)
                        if club_members_id is not None:
                            response = self._list_club_members(club_members_id, query, context)
                        else:
                            response = error_response(404, "not_found", "Endpoint not found.", request_id)
                            error_code = "not_found"
        except AuthError as exc:
            error_code = exc.code
            response = error_response(exc.status_code, exc.code, exc.message, request_id)
        self._record_audit_event(request_id, method, route, response, context, error_code)
        return response

    def _record_audit_event(self, request_id: str, method: str, route: str, response: ApiResponse, context, error_code):
        recorder = getattr(self.audit_sink, "record_api_audit_event", None)
        if not recorder:
            return
        subject = context.subject if context else "anonymous"
        roles = tuple(sorted(context.roles)) if context else ()
        if response.status_code < 400:
            outcome = "success"
        elif response.status_code < 500:
            outcome = "client_error"
        else:
            outcome = "server_error"
        event = AuditEvent(
            request_id=request_id,
            method=method,
            route=route,
            status_code=response.status_code,
            subject=subject,
            roles=roles,
            outcome=outcome,
            error_code=error_code,
        )
        try:
            recorder(event)
        except Exception:
            pass

    def _route_template(self, method: str, path: str) -> str:
        if method == "GET" and path == "/api/v1/health":
            return "/api/v1/health"
        if method == "GET" and path == "/api/v1/clubs":
            return "/api/v1/clubs"
        if self._match_club_members_path(method, path) is not None:
            return "/api/v1/clubs/{club_id}/members"
        if self._match_ecp_verify_path(method, path) is not None:
            return "/api/v1/ecp/verify/{token}"
        return "unmatched"

    def _list_clubs(self, query: dict, context) -> ApiResponse:
        require_any_role(context, {"admin", "club_president"})
        limit = parse_limit(query.get("limit"))
        cursor = query.get("cursor")
        filter_text = query.get("filter") or query.get("q") or ""
        page, next_cursor = self.repository.list_clubs(
            limit=limit,
            cursor=cursor,
            filter_text=filter_text,
        )
        return json_response(
            200,
            {
                "items": [club_to_api(club) for club in page],
                "nextCursor": next_cursor,
            },
        )

    def _list_club_members(self, club_id: int, query: dict, context) -> ApiResponse:
        require_any_role(context, {"admin", "club_president"})
        if not context.has_role("admin") and club_id not in context.club_ids:
            raise AuthError(403, "forbidden", "Authenticated caller is not allowed to access this club.")
        limit = parse_limit(query.get("limit"))
        cursor = query.get("cursor")
        members = list(self.repository.fetch_members(club_id))
        page, next_cursor = paginate_items(members, limit, cursor)
        return json_response(
            200,
            {
                "items": [member_to_api(member) for member in page],
                "nextCursor": next_cursor,
            },
        )

    def _match_club_members_path(self, method: str, path: str) -> int | None:
        if method != "GET":
            return None
        prefix = "/api/v1/clubs/"
        suffix = "/members"
        if not path.startswith(prefix) or not path.endswith(suffix):
            return None
        raw_id = path[len(prefix):-len(suffix)]
        try:
            return int(raw_id)
        except ValueError:
            return None

    def _verify_ecp_token(self, token: str, request_id: str) -> ApiResponse:
        record = self.repository.fetch_ecp_verification_by_token(token)
        if not record:
            return error_response(404, "ecp_verification_not_found", "eCP verification token was not found.", request_id)
        return json_response(200, ecp_verification_to_api(record))

    def _match_ecp_verify_path(self, method: str, path: str) -> str | None:
        if method != "GET":
            return None
        prefix = "/api/v1/ecp/verify/"
        if not path.startswith(prefix):
            return None
        token = path[len(prefix):].strip("/")
        return token or None
