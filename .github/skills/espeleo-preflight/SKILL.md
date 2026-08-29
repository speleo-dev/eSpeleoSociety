---
name: espeleo-preflight
description: Verify eSpeleoSociety changes before commit, PR or merge - runs the unit suite plus project-specific checks for translations, API contract coverage, migration safety, UI/database layering and leaked secrets. Use before committing, when asked to "skontroluj", "over zmeny", "run the checks", "je to pripravene na merge", or after finishing any code change in this repository.
---

# eSpeleoSociety Pre-flight

Run this before every commit, PR and merge. Two commands cover the repository.

## 1. Unit suite

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Verified baseline: **160 tests, 1 skipped, all passing, ~2 seconds.** Anything
below that count or any failure is a regression introduced by the current
change — do not rationalise it as a pre-existing problem without checking
`git stash`.

The single skip is `test_schema_sql_can_apply_to_configured_postgres`, which
only runs when `ESPELEO_TEST_DATABASE_URL` points at a disposable database:

```bash
ESPELEO_TEST_DATABASE_URL=postgresql://user:pass@localhost/espeleo_test \
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_database_schema_sql -v
```

Run that variant whenever you touch `database/schema.sql` or a migration.

Targeted runs while iterating:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_backend_api tests.test_backend_auth -v
```

## 2. Project-specific checks

```bash
python3 tools/preflight_check.py
```

Checks, all of which unit tests do not cover:

| Check | What it enforces |
|---|---|
| `i18n` | translation catalogs are valid XML; every module using `self.tr(...)` is listed in `SOURCES` in `eSpeleoSociety.pro`; reports unfinished translations |
| `api` | every `/api/v1/...` route in `backend/app.py` is documented in `docs/api/openapi.yaml`, and vice versa |
| `migrations` | every file in `database/migrations/` is wrapped in `BEGIN; ... COMMIT;` |
| `layering` | `views/` and `dialogs/` never execute SQL directly (protects the API migration) |
| `secrets` | no `temp.properties`, `github-token.txt`, `.env` or PEM private key blocks in the tree |

Run a subset while iterating: `python3 tools/preflight_check.py api migrations`.

All five checks currently pass. The only remaining warning is that
`translate/en_US.ts` has 253 unfinished translations, so the English UI is
largely untranslated — that is a content task, not a blocker.

## 3. Change-specific gates

Pick the rows that match what you touched.

| You changed | Also do this |
|---|---|
| `backend/` routes, auth, serializers | update `docs/api/openapi.yaml` in the same commit; re-run `preflight_check.py api` |
| crypto, secrets, JWT, PII, GCS, FTP | run the `security-review` skill before opening the PR |
| `database/schema.sql` or a migration | run the `espeleo-migrations` skill |
| a view, dialog, the card, wallet or the verification page | run the `espeleo-design` skill and re-render the card preview |
| `requirements.txt` | confirm the CI job in `.github/workflows/tests.yml` still installs everything the tests import |
| user-visible strings | `self.tr(...)` + update both `translate/*.ts` |

## 4. Reporting

State the verified numbers, not impressions: test count, which pre-flight checks
passed, and what you did not verify (for example, the PostgreSQL integration
test if no disposable database was available). If a check fails and you chose
not to fix it, say so explicitly and why.

## Notes

- The README documents `.venv/bin/python`; on machines without a virtualenv the
  dependencies are installed system-wide and plain `python3` works. Use whichever
  interpreter actually resolves the imports.
- CI (`.github/workflows/tests.yml`) runs the unit suite on Python 3.11 and then
  `tools/preflight_check.py`.
