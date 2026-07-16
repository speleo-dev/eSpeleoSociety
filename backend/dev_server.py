import os
from wsgiref.simple_server import make_server

import config
import db
from backend.app import ApiApp
from backend.auth import DEFAULT_AUDIENCE, DEFAULT_ISSUER, JwtBearerVerifier
from backend.crypto import make_check_hash_factory
from backend.repository import DatabaseApiRepository
from backend.storage import make_gcs_upload_blob
from backend.wsgi import make_wsgi_app


def _env_or_secret(env_name: str, secret_name: str, secret_getter) -> str | None:
    return os.environ.get(env_name) or secret_getter(secret_name)


def _oidc_algorithms(secret_getter) -> list[str] | None:
    raw_value = os.environ.get("ESPELEO_OIDC_ALGORITHMS") or secret_getter("oidc_algorithms")
    if not raw_value:
        return None
    return [algorithm.strip() for algorithm in raw_value.split(",") if algorithm.strip()]


def _environment_mode() -> str:
    raw_mode = (os.environ.get("ESPELEO_ENV") or "production").strip().lower()
    if raw_mode not in ("production", "development"):
        raise RuntimeError(f"Invalid ESPELEO_ENV={raw_mode!r}; expected 'production' or 'development'.")
    return raw_mode


def build_token_verifier_from_environment(secret_getter=None) -> JwtBearerVerifier:
    secret_getter = secret_getter or config.secret_manager.get_secret
    env_mode = _environment_mode()
    issuer = _env_or_secret("ESPELEO_API_ISSUER", "api_issuer", secret_getter)
    audience = _env_or_secret("ESPELEO_API_AUDIENCE", "api_audience", secret_getter)
    jwks_url = _env_or_secret("ESPELEO_OIDC_JWKS_URL", "oidc_jwks_url", secret_getter)

    if env_mode == "production":
        if not jwks_url:
            raise RuntimeError(
                "ESPELEO_OIDC_JWKS_URL/oidc_jwks_url is required when ESPELEO_ENV=production. "
                "Refusing to start with an HS256 shared-secret fallback in production."
            )
        if not issuer or not audience:
            raise RuntimeError(
                "ESPELEO_API_ISSUER/api_issuer and ESPELEO_API_AUDIENCE/api_audience are required "
                "when ESPELEO_ENV=production. Refusing to use development default values."
            )
        return JwtBearerVerifier(
            jwks_url=jwks_url,
            audience=audience,
            issuer=issuer,
            algorithms=_oidc_algorithms(secret_getter),
        )

    # Development mode keeps permissive defaults for local/test convenience.
    issuer = issuer or DEFAULT_ISSUER
    audience = audience or DEFAULT_AUDIENCE
    if jwks_url:
        return JwtBearerVerifier(
            jwks_url=jwks_url,
            audience=audience,
            issuer=issuer,
            algorithms=_oidc_algorithms(secret_getter),
        )

    jwt_secret = _env_or_secret("ESPELEO_API_JWT_SECRET", "api_jwt_secret", secret_getter)
    if not jwt_secret:
        raise RuntimeError("Missing ESPELEO_OIDC_JWKS_URL/oidc_jwks_url or ESPELEO_API_JWT_SECRET/api_jwt_secret.")
    return JwtBearerVerifier(
        jwt_secret=jwt_secret,
        audience=audience,
        issuer=issuer,
    )


def create_wsgi_app_from_environment():
    pin = os.environ.get("ESPELEO_SECRETS_PIN")
    if pin:
        if not config.secret_manager.decrypt_file(pin):
            raise RuntimeError("Could not decrypt secrets file with ESPELEO_SECRETS_PIN.")

    token_verifier = build_token_verifier_from_environment()

    if db.db_manager is None:
        db.db_manager = db.DatabaseManager()

    api_app = ApiApp(
        repository=DatabaseApiRepository(
            db.db_manager,
            upload_blob=make_gcs_upload_blob(config.secret_manager.get_secret),
            check_hash_factory=make_check_hash_factory(config.secret_manager.get_secret),
        ),
        token_verifier=token_verifier,
    )
    return make_wsgi_app(api_app)


def main():
    host = os.environ.get("ESPELEO_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ESPELEO_API_PORT", "8080"))
    application = create_wsgi_app_from_environment()
    with make_server(host, port, application) as server:
        print(f"eSpeleoSociety API listening on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
