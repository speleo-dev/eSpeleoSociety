# eSpeleo Security Hardening - Phase 1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** Fix critical auth fail-open vulnerabilities (#1-3) before production

**Architecture:** Fail-closed auth: JWKS required in prod, explicit HS256 only for dev, algorithm validation enforced

**Tech Stack:** Python 3.x, PyJWT, WSGI, PostgreSQL

## Global Constraints
- Python 3.10+, PyJWT 2.8+
- All code must have type hints
- Tests must cover new branches
- No production credentials in code
- Follow existing code style in backend/

---

## Task 1: JWKS Required in Production

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/dev_server.py`
- Test: `tests/test_backend_auth.py`

**Issue:** HS256 dev-fallback available in production when JWKS URL missing

**Interfaces:**
- Consumes: `ESPELEO_OIDC_JWKS_URL` env var
- Produces: `JwtBearerVerifier` raises `ValueError` in prod without JWKS

- [ ] **Step 1: Add production environment detection**

```python
# backend/auth.py - add to JwtBearerVerifier.__init__
import os

is_production = os.environ.get('ESPELEO_ENV', '').lower() == 'production'
if is_production and not jwks_client and not jwks_url:
    raise ValueError("JWKS URL required in production. Set ESPELEO_OIDC_JWKS_URL")
```

- [ ] **Step 2: Write test for production JWKS enforcement**

```python
# tests/test_backend_auth.py
import os
import pytest
from backend.auth import JwtBearerVerifier

def test_production_requires_jwks_url():
    """Fail closed: production without JWKS must raise."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv('ESPELEO_ENV', 'production')
        mp.setenv('ESPELEO_API_JWT_SECRET', '')
        mp.delenv('ESPELEO_OIDC_JWKS_URL', raising=False)
        with pytest.raises(ValueError, match="JWKS URL required"):
            JwtBearerVerifier(jwt_secret=None, jwks_url=None)

def test_development_allows_hs256_fallback():
    """Dev mode allows HS256 without JWKS."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv('ESPELEO_ENV', 'development')
        mp.delenv('ESPELEO_OIDC_JWKS_URL', raising=False)
        verifier = JwtBearerVerifier(jwt_secret="dev-secret")
        assert verifier.algorithms == ('HS256',)
```

- [ ] **Step 3: Run tests - expect first to fail**

```bash
python -m pytest tests/test_backend_auth.py::test_production_requires_jwks_url -v
# Expected: FAIL (ValueError not raised yet)
```

- [ ] **Step 4: Implement production check in auth.py**

```python
# backend/auth.py - in JwtBearerVerifier.__init__
def __init__(
    self,
    jwt_secret: str | None = None,
    jwks_url: str | None = None,
    algorithms: tuple[str, ...] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
):
    self.is_production = os.environ.get('ESPELEO_ENV', '').lower() == 'production'
    self.jwks_client = None
    
    if jwks_url:
        self.jwks_client = jwt.PyJWKClient(jwks_url)
        self.algorithms = algorithms or ('RS256', 'ES256')
    elif self.is_production:
        raise ValueError(
            "JWKS URL required in production. "
            "Set ESPELEO_OIDC_JWKS_URL environment variable."
        )
    else:
        # Development fallback
        if not jwt_secret:
            raise ValueError("jwt_secret required when JWKS not configured")
        self.jwt_secret = jwt_secret
        self.algorithms = algorithms or ('HS256',)
```

- [ ] **Step 5: Run tests - verify pass**

```bash
python -m pytest tests/test_backend_auth.py::test_production_requires_jwks_url tests/test_backend_auth.py::test_development_allows_hs256_fallback -v
# Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/auth.py tests/test_backend_auth.py
git commit -m "security(auth): require JWKS in production, fail closed

Fixes audit finding #1: HS256 dev-fallback no longer available in prod.
Production now requires ESPELEO_OIDC_JWKS_URL environment variable."
```

---

## Task 2: Enforce JWT exp Claim

**Files:**
- Modify: `backend/auth.py`
- Test: `tests/test_backend_auth.py`

**Issue:** JWT without exp claim accepted forever

**Interfaces:**
- Consumes: JWT token string
- Produces: ValidationError if exp missing

- [ ] **Step 1: Write test for exp requirement**

```python
# tests/test_backend_auth.py
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

def test_token_without_exp_rejected():
    """Token without exp claim must be rejected."""
    verifier = JwtBearerVerifier(jwt_secret="test-secret")
    token = pyjwt.encode(
        {"sub": "user123", "aud": "espeleo-api"},
        "test-secret",
        algorithm="HS256"
    )
    with pytest.raises(Exception):  # ExpiredSignatureError or similar
        verifier.verify(token)

def test_token_with_exp_accepted():
    """Token with valid exp claim accepted."""
    verifier = JwtBearerVerifier(jwt_secret="test-secret")
    token = pyjwt.encode(
        {
            "sub": "user123",
            "aud": "espeleo-api",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        "test-secret",
        algorithm="HS256"
    )
    claims = verifier.verify(token)
    assert claims["sub"] == "user123"
```

- [ ] **Step 2: Implement exp enforcement**

```python
# backend/auth.py - in verify method
def verify(self, token: str) -> dict:
    """Verify JWT and enforce exp claim presence."""
    options = {
        "require": ["exp"],  # Require expiration
        "verify_exp": True,
    }
    
    if self.jwks_client:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        return pyjwt.decode(
            token,
            signing_key.key,
            algorithms=self.algorithms,
            audience=self.audience,
            issuer=self.issuer,
            options=options
        )
    else:
        return pyjwt.decode(
            token,
            self.jwt_secret,
            algorithms=self.algorithms,
            options=options
        )
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_backend_auth.py -k "exp" -v
# Expected: PASS
```

- [ ] **Step 4: Commit**

```bash
git add backend/auth.py tests/test_backend_auth.py
git commit -m "security(auth): enforce JWT exp claim

Fixes audit finding #2: tokens without exp are now rejected.
Adds require=['exp'] to decode options."
```

---

## Task 3: Algorithm Confusion Protection

**Files:**
- Modify: `backend/auth.py`
- Test: `tests/test_backend_auth.py`

**Issue:** Algorithm list not validated against key type (JWKS vs symmetric)

**Interfaces:**
- Consumes: algorithms tuple, jwks_client/jwt_secret
- Produces: ValueError if mismatch

- [ ] **Step 1: Write algorithm validation test**

```python
# tests/test_backend_auth.py
def test_asymmetric_algorithms_with_symmetric_key_rejected():
    """RS256/ES256 algorithms with HS256 secret must fail."""
    with pytest.raises(ValueError, match="asymmetric"):
        JwtBearerVerifier(
            jwt_secret="symmetric-secret",
            algorithms=("RS256",)
        )

def test_symmetric_algorithm_with_jwks_rejected():
    """HS256 algorithm with JWKS must fail."""
    with pytest.raises(ValueError, match="symmetric"):
        JwtBearerVerifier(
            jwks_url="https://example.com/.well-known/jwks.json",
            algorithms=("HS256",)
        )

def test_matching_algorithms_accepted():
    """Matching algorithms accepted."""
    # Symmetric with HS256
    v1 = JwtBearerVerifier(jwt_secret="secret", algorithms=("HS256",))
    assert v1.algorithms == ("HS256",)
    
    # Asymmetric with JWKS
    v2 = JwtBearerVerifier(
        jwks_url="https://example.com/.well-known/jwks.json",
        algorithms=("RS256",)
    )
    assert v2.algorithms == ("RS256",)
```

- [ ] **Step 2: Implement algorithm validation**

```python
# backend/auth.py - add validation method
ASYMETRIC_ALGORITHMS = {'RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512', 'PS256', 'PS384', 'PS512'}
SYMMETRIC_ALGORITHMS = {'HS256', 'HS384', 'HS512'}

def _validate_algorithms(self, algorithms: tuple[str, ...], has_jwks: bool) -> None:
    """Ensure algorithms match key type to prevent algorithm confusion attacks."""
    algo_set = set(algorithms)
    
    if has_jwks:
        # JWKS uses asymmetric keys
        if algo_set & SYMMETRIC_ALGORITHMS:
            symmetric = algo_set & SYMMETRIC_ALGORITHMS
            raise ValueError(
                f"Symmetric algorithms {symmetric} not allowed with JWKS. "
                f"Use asymmetric algorithms like RS256."
            )
    else:
        # Symmetric secret uses symmetric algorithms
        if algo_set & ASYMETRIC_ALGORITHMS:
            asymmetric = algo_set & ASYMETRIC_ALGORITHMS
            raise ValueError(
                f"Asymmetric algorithms {asymmetric} not allowed with symmetric secret. "
                f"Use symmetric algorithms like HS256."
            )
```

- [ ] **Step 3: Call validation in __init__**

```python
# backend/auth.py - in __init__, after setting algorithms
self._validate_algorithms(self.algorithms, self.jwks_client is not None)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_backend_auth.py -k "algorithm" -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py tests/test_backend_auth.py
git commit -m "security(auth): prevent algorithm confusion attacks

Fixes audit finding #3: validate algorithms match key type.
JWKS requires asymmetric algorithms, symmetric secret requires HS*.
Prevents RS256/HS256 confusion attacks."
```

---

## Task 4: Remove Hardcoded Defaults

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/app.py`
- Modify: `backend/dev_server.py`
- Test: `tests/test_backend_auth.py`

**Issue:** Hardcoded issuer/audience defaults

**Interfaces:**
- Consumes: env vars or explicit params
- Produces: No defaults - must be explicit

- [ ] **Step 1: Write test for required params**

```python
# tests/test_backend_auth.py
def test_no_default_issuer():
    """No default issuer allowed."""
    verifier = JwtBearerVerifier(
        jwt_secret="secret",
        issuer=None,
        audience="espeleo-api"
    )
    assert verifier.issuer is None  # Explicitly None, not default

def test_explicit_issuer_used():
    """Explicit issuer must be used in validation."""
    verifier = JwtBearerVerifier(
        jwt_secret="secret",
        issuer="https://auth.example.com",
        audience="espeleo-api"
    )
    assert verifier.issuer == "https://auth.example.com"
```

- [ ] **Step 2: Remove hardcoded defaults**

```python
# backend/auth.py - remove default values
# BEFORE:
# issuer: str = "espeleo-test"
# audience: str = "espeleo-api"

# AFTER - no defaults, must be explicit
def __init__(
    self,
    jwt_secret: str | None = None,
    jwks_url: str | None = None,
    algorithms: tuple[str, ...] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
):
```

- [ ] **Step 3: Update dev_server.py to be explicit**

```python
# backend/dev_server.py - add explicit dev values
verifier = JwtBearerVerifier(
    jwt_secret=jwt_secret,
    jwks_url=jwks_url,
    audience=os.environ.get('ESPELEO_API_AUDIENCE', 'espeleo-dev'),
    issuer=os.environ.get('ESPELEO_API_ISSUER', 'espeleo-dev-issuer')
)
```

- [ ] **Step 4: Run full auth test suite**

```bash
python -m pytest tests/test_backend_auth.py -v
# Expected: All PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/app.py backend/dev_server.py tests/test_backend_auth.py
git commit -m "security(auth): remove hardcoded issuer/audience defaults

Fixes audit finding #1 (part): no hardcoded defaults.
All auth parameters must be explicitly configured.
Dev server uses explicit dev values or env vars."
```

---

## Phase 1 Verification

- [ ] **Step 6: Full test run**

```bash
python -m pytest tests/test_backend_auth.py -v
# Expected: 10+ tests PASS
```

- [ ] **Step 7: Security checklist**

```bash
# Verify fail-closed behavior
python -c "
import os
os.environ['ESPELEO_ENV'] = 'production'
os.environ['ESPELEO_API_JWT_SECRET'] = ''
try:
    from backend.auth import JwtBearerVerifier
    JwtBearerVerifier()
    print('FAIL: should have raised')
except ValueError as e:
    print(f'OK: {e}')
"
# Expected: "OK: JWKS URL required in production"
```

- [ ] **Step 8: Update documentation**

```markdown
# Add to docs/api/backend-api.md under "Production Deployment"

## Security Requirements

- `ESPELEO_ENV=production` requires `ESPELEO_OIDC_JWKS_URL`
- JWT tokens must include `exp` claim
- Algorithm must match key type (RS256 with JWKS, HS256 with secret)
- No hardcoded issuer/audience - configure explicitly
```

- [ ] **Step 9: Final commit**

```bash
git add docs/api/backend-api.md
git commit -m "docs(api): document production security requirements

Add security requirements section covering:
- JWKS requirement in production
- JWT exp enforcement
- Algorithm validation
- No hardcoded defaults"
```

---

## Summary

**Fixed audit findings:** #1, #2, #3

**Changed files:**
- `backend/auth.py` - fail-closed auth, exp enforcement, algorithm validation
- `backend/dev_server.py` - explicit dev configuration
- `tests/test_backend_auth.py` - comprehensive security tests
- `docs/api/backend-api.md` - production security docs

**Tests added:** 8+ new security tests

**Breaking changes:**
- Production now requires `ESPELEO_OIDC_JWKS_URL`
- JWTs without `exp` claim rejected
- No default issuer/audience values
