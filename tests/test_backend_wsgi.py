import json
import unittest

from backend.app import ApiApp
from backend.wsgi import make_wsgi_app


class EmptyRepository:
    def fetch_clubs(self):
        return []


class BackendWsgiTest(unittest.TestCase):
    def test_wsgi_adapter_serves_api_response(self):
        application = make_wsgi_app(ApiApp(repository=EmptyRepository(), jwt_secret="unit-test-secret"))
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(application({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/health",
            "QUERY_STRING": "",
        }, start_response))

        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(captured["headers"]["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body.decode("utf-8")), {"status": "ok", "version": "v1"})


if __name__ == "__main__":
    unittest.main()
