# eSpeleoSociety

eSpeleoSociety je PyQt desktopovy administracny klient pre spravu clenov, klubov, clenskych poplatkov, eCP ziadosti a elektronickych jaskyniarskych preukazov.

Projekt je momentalne v prechodnom stave: desktop klient stale pristupuje priamo do PostgreSQL a pouziva lokalne zasifrovane secrets. Cielova architektura je hruby administracny klient plus API/OAuth2 backend, ktory ako jediny vidi databazu, Google Cloud a podpisovacie kluce.

## Kde zacat

- [Technicky manual](docs/technical-manual.md) vysvetluje architekturu, databazove tabulky, workflow, konfiguraciu, testy, bezpecnost a roadmapu.
- [API/OAuth2 migration plan](docs/api-oauth2-migration-plan.md) popisuje cielovu backend architekturu.
- [Signed Offline eCP QR](docs/ecp-signing.md) popisuje offline overitelne QR pre eCP.
- [Database Bootstrap](database/README.md) popisuje lokalnu PostgreSQL schemu a migracie.
- [Fix Log](fix.md) sumarizuje doteraz vykonane opravy a aktualny stav.

## Spustenie

```bash
.venv/bin/python main.py
```

Ak neexistuje zasifrovany subor secrets, aplikacia najprv otvori setup dialog pre DB, Google Cloud a eCP podpisovacie nastavenia.

## Testy

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

PostgreSQL integracny test sa spusti iba vtedy, ked je nastavena premenna `ESPELEO_TEST_DATABASE_URL` na disposable databazu.
