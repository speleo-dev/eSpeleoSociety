from dataclasses import dataclass

import jwt


DEFAULT_AUDIENCE = "espeleo-api"
DEFAULT_ISSUER = "espeleo-test"


class AuthError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AuthContext:
    subject: str
    roles: frozenset[str]
    club_ids: frozenset[int]

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _extract_bearer_token(headers: dict[str, str]) -> str:
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth_header.startswith("Bearer "):
        raise AuthError(401, "missing_bearer_token", "Missing OAuth2 bearer token.")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise AuthError(401, "missing_bearer_token", "Missing OAuth2 bearer token.")
    return token


def _normalise_roles(claims: dict) -> frozenset[str]:
    roles = set(claims.get("roles") or [])
    scope = claims.get("scope") or ""
    roles.update(scope.split())
    realm_access = claims.get("realm_access") or {}
    roles.update(realm_access.get("roles") or [])
    return frozenset(str(role) for role in roles if role)


def _normalise_club_ids(claims: dict) -> frozenset[int]:
    values = claims.get("club_ids") or claims.get("clubs") or []
    club_ids = set()
    for value in values:
        try:
            club_ids.add(int(value))
        except (TypeError, ValueError):
            continue
    return frozenset(club_ids)


def authenticate_bearer(
    headers: dict[str, str],
    jwt_secret: str,
    audience: str = DEFAULT_AUDIENCE,
    issuer: str = DEFAULT_ISSUER,
) -> AuthContext:
    token = _extract_bearer_token(headers)
    try:
        claims = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience=audience,
            issuer=issuer,
        )
    except jwt.PyJWTError as exc:
        raise AuthError(401, "invalid_bearer_token", "Invalid OAuth2 bearer token.") from exc

    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise AuthError(401, "invalid_bearer_token", "OAuth2 bearer token is missing subject.")

    return AuthContext(
        subject=subject,
        roles=_normalise_roles(claims),
        club_ids=_normalise_club_ids(claims),
    )


def require_any_role(context: AuthContext, allowed_roles: set[str]):
    if not context.roles.intersection(allowed_roles):
        raise AuthError(403, "forbidden", "Authenticated caller is not allowed to access this resource.")
