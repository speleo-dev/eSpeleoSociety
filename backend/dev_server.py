import os
from wsgiref.simple_server import make_server

import config
import db
from backend.app import ApiApp
from backend.repository import DatabaseApiRepository
from backend.wsgi import make_wsgi_app


def create_wsgi_app_from_environment():
    pin = os.environ.get("ESPELEO_SECRETS_PIN")
    if pin:
        if not config.secret_manager.decrypt_file(pin):
            raise RuntimeError("Could not decrypt secrets file with ESPELEO_SECRETS_PIN.")

    jwt_secret = os.environ.get("ESPELEO_API_JWT_SECRET") or config.secret_manager.get_secret("api_jwt_secret")
    if not jwt_secret:
        raise RuntimeError("Missing ESPELEO_API_JWT_SECRET or api_jwt_secret secret.")

    if db.db_manager is None:
        db.db_manager = db.DatabaseManager()

    api_app = ApiApp(
        repository=DatabaseApiRepository(db.db_manager),
        jwt_secret=jwt_secret,
        issuer=os.environ.get("ESPELEO_API_ISSUER", "espeleo-test"),
        audience=os.environ.get("ESPELEO_API_AUDIENCE", "espeleo-api"),
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
