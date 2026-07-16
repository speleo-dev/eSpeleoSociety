import os
import unittest
from unittest.mock import patch

from backend.dev_server import build_token_verifier_from_environment


class BackendDevServerTest(unittest.TestCase):
    def test_build_token_verifier_prefers_oidc_jwks_when_configured(self):
        with patch.dict(os.environ, {
            "ESPELEO_OIDC_JWKS_URL": "https://idp.example.test/realms/espeleo/protocol/openid-connect/certs",
            "ESPELEO_API_ISSUER": "https://idp.example.test/realms/espeleo",
            "ESPELEO_API_AUDIENCE": "espeleo-api",
            "ESPELEO_OIDC_ALGORITHMS": "RS256,ES256",
        }, clear=True):
            verifier = build_token_verifier_from_environment(secret_getter=lambda _name: None)

        self.assertIsNotNone(verifier.jwks_client)
        self.assertEqual(verifier.audience, "espeleo-api")
        self.assertEqual(verifier.issuer, "https://idp.example.test/realms/espeleo")
        self.assertEqual(verifier.algorithms, ("RS256", "ES256"))

    def test_build_token_verifier_keeps_hs256_fallback_for_dev(self):
        with patch.dict(os.environ, {
            "ESPELEO_ENV": "development",
            "ESPELEO_API_JWT_SECRET": "dev-secret",
        }, clear=True):
            verifier = build_token_verifier_from_environment(secret_getter=lambda _name: None)

        self.assertIsNone(verifier.jwks_client)
        self.assertEqual(verifier.jwt_secret, "dev-secret")
        self.assertEqual(verifier.algorithms, ("HS256",))

    def test_build_token_verifier_rejects_hmac_algorithm_when_jwks_configured(self):
        with patch.dict(os.environ, {
            "ESPELEO_OIDC_JWKS_URL": "https://idp.example.test/realms/espeleo/protocol/openid-connect/certs",
            "ESPELEO_API_ISSUER": "https://idp.example.test/realms/espeleo",
            "ESPELEO_API_AUDIENCE": "espeleo-api",
            "ESPELEO_OIDC_ALGORITHMS": "HS256",
        }, clear=True):
            with self.assertRaises(ValueError):
                build_token_verifier_from_environment(secret_getter=lambda _name: None)


if __name__ == "__main__":
    unittest.main()
