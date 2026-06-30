import unittest
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.auth import JwtBearerVerifier, authenticate_bearer


class FakeJwksClient:
    def __init__(self, key):
        self.key = key
        self.tokens = []

    def get_signing_key_from_jwt(self, token):
        self.tokens.append(token)
        return SimpleNamespace(key=self.key)


class BackendAuthTest(unittest.TestCase):
    def test_jwks_verifier_accepts_rs256_oidc_token_and_resource_roles(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        token = jwt.encode(
            {
                "sub": "oidc-user-1",
                "aud": "espeleo-api",
                "iss": "https://idp.example.test/realms/espeleo",
                "resource_access": {
                    "espeleo-api": {
                        "roles": ["admin"],
                    },
                },
                "clubs": ["7"],
                "memberId": "42",
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "unit-test-key"},
        )
        jwks_client = FakeJwksClient(public_key)
        verifier = JwtBearerVerifier(
            jwks_client=jwks_client,
            audience="espeleo-api",
            issuer="https://idp.example.test/realms/espeleo",
        )

        context = authenticate_bearer(
            {"Authorization": f"Bearer {token}"},
            token_verifier=verifier,
        )

        self.assertEqual(context.subject, "oidc-user-1")
        self.assertEqual(context.roles, frozenset({"admin"}))
        self.assertEqual(context.club_ids, frozenset({7}))
        self.assertEqual(context.member_id, 42)
        self.assertEqual(jwks_client.tokens, [token])

    def test_hs256_secret_validation_remains_available_for_dev(self):
        token = jwt.encode(
            {
                "sub": "dev-user-1",
                "aud": "espeleo-api",
                "iss": "espeleo-test",
                "roles": ["club_president"],
                "club_ids": [3],
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        context = authenticate_bearer(
            {"Authorization": f"Bearer {token}"},
            jwt_secret="unit-test-secret",
        )

        self.assertEqual(context.subject, "dev-user-1")
        self.assertEqual(context.roles, frozenset({"club_president"}))
        self.assertEqual(context.club_ids, frozenset({3}))

    def test_roles_claim_string_is_not_split_into_characters(self):
        token = jwt.encode(
            {
                "sub": "dev-user-2",
                "aud": "espeleo-api",
                "iss": "espeleo-test",
                "roles": "admin",
            },
            "unit-test-secret",
            algorithm="HS256",
        )

        context = authenticate_bearer(
            {"Authorization": f"Bearer {token}"},
            jwt_secret="unit-test-secret",
        )

        self.assertEqual(context.roles, frozenset({"admin"}))


if __name__ == "__main__":
    unittest.main()
