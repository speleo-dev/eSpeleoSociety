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
    member_id: int | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles


class JwtBearerVerifier:
    def __init__(
        self,
        jwt_secret: str | None = None,
        audience: str = DEFAULT_AUDIENCE,
        issuer: str = DEFAULT_ISSUER,
        jwks_url: str | None = None,
        algorithms: list[str] | tuple[str, ...] | None = None,
        jwks_client=None,
    ):
        self.jwt_secret = jwt_secret
        self.audience = audience
        self.issuer = issuer
        self.jwks_client = jwks_client or (jwt.PyJWKClient(jwks_url) if jwks_url else None)
        if self.jwks_client:
            self.algorithms = tuple(algorithms or ("RS256",))
        else:
            if not jwt_secret:
                raise ValueError("jwt_secret is required when JWKS is not configured.")
            self.algorithms = tuple(algorithms or ("HS256",))

    def decode(self, token: str) -> dict:
        try:
            key = self.jwt_secret
            if self.jwks_client:
                key = self.jwks_client.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
            )
        except Exception as exc:
            raise AuthError(401, "invalid_bearer_token", "Invalid OAuth2 bearer token.") from exc


def _extract_bearer_token(headers: dict[str, str]) -> str:
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth_header.startswith("Bearer "):
        raise AuthError(401, "missing_bearer_token", "Missing OAuth2 bearer token.")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise AuthError(401, "missing_bearer_token", "Missing OAuth2 bearer token.")
    return token


def _claim_values(value) -> list:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def _normalise_roles(claims: dict) -> frozenset[str]:
    roles = set(_claim_values(claims.get("roles")))
    scope = claims.get("scope") or ""
    roles.update(scope.split())
    realm_access = claims.get("realm_access") or {}
    roles.update(_claim_values(realm_access.get("roles")))
    resource_access = claims.get("resource_access") or {}
    if isinstance(resource_access, dict):
        for resource in resource_access.values():
            if isinstance(resource, dict):
                roles.update(_claim_values(resource.get("roles")))
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


def _normalise_member_id(claims: dict) -> int | None:
    for key in ("member_id", "memberId"):
        try:
            return int(claims[key])
        except (KeyError, TypeError, ValueError):
            continue
    return None


def authenticate_bearer(
    headers: dict[str, str],
    jwt_secret: str | None = None,
    audience: str = DEFAULT_AUDIENCE,
    issuer: str = DEFAULT_ISSUER,
    token_verifier: JwtBearerVerifier | None = None,
    jwks_url: str | None = None,
    algorithms: list[str] | tuple[str, ...] | None = None,
) -> AuthContext:
    token = _extract_bearer_token(headers)
    if token_verifier is None:
        token_verifier = JwtBearerVerifier(
            jwt_secret=jwt_secret,
            audience=audience,
            issuer=issuer,
            jwks_url=jwks_url,
            algorithms=algorithms,
        )
    claims = token_verifier.decode(token)

    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise AuthError(401, "invalid_bearer_token", "OAuth2 bearer token is missing subject.")

    return AuthContext(
        subject=subject,
        roles=_normalise_roles(claims),
        club_ids=_normalise_club_ids(claims),
        member_id=_normalise_member_id(claims),
    )


def require_any_role(context: AuthContext, allowed_roles: set[str]):
    if not context.roles.intersection(allowed_roles):
        raise AuthError(403, "forbidden", "Authenticated caller is not allowed to access this resource.")
