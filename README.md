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

### Konfiguracia (adresar `config/`)

Vsetka konfiguracia specificka pre pouzivatela/pocitac je v adresari `config/`,
ktory je **cely v `.gitignore`** - nikdy sa necommituje:

| Subor | Obsah |
|---|---|
| `config/secrets.properties` | zasifrovane tajomstva (DB, GCP, eCP podpisovy kluc), odomyka sa PIN-om |
| `config/config.properties` | nastavenia aplikacie (jazyk, bankove udaje, ...) |
| `config/table_layouts.json` | sirky, poradie, skryte stlpce a zoradenie tabuliek |

Staticke zdroje potrebne pre cerstvy klon (`translate/`, `docs/api/openapi.yaml`,
`.github/workflows/`) zostavaju na svojom mieste a su naďalej verzovane.

Pri prvom spusteni po tejto zmene sa `secrets.properties` a `config.properties`
z korena projektu **automaticky presunu** do `config/` (`app_paths.py`), takze
sa nestratia nastavenia ani PIN.

> `config/` zamerne **nie je** Python balik. `config/__init__.py` by zatienil
> modul `config.py` a rozbil kazdy `from config import secret_manager`.
> Strazi to `tools/preflight_check.py` aj `tests/test_config_layout.py`.

### Export secrets do TXT/CSV

Tlacidlo **"Export to TXT/CSV..."** v setup dialogu vypise vsetky tajomstva
vratane maskovanych poli v citatelnej podobe. Pred exportom si znovu vypyta
PIN a subor zapise s pravami `0600`. Ide o **plaintext** - drz ho mimo repozitara
a po pouziti ho zmaz.

### Google Cloud Storage credentials (nahravanie fotiek/log)

Pole `JSON credentials` v setup dialogu (`setup.py`) prijima **obsah** GCP
service account kluca (JSON subor stiahnuty z Google Cloud Console ->
IAM & Admin -> Service Accounts -> Keys -> Add key -> JSON), nie iba cestu k
nemu. Pouzi tlacidlo **"Import JSON key file..."** a vyber stiahnuty `.json`
subor - jeho obsah sa ulozi priamo v zasifrovanom `config/secrets.properties`, takze
uz nemoze zmiznut pri prenose na iny pocitac (predosla nezhoda: povodne sa
ukladala iba cesta/nazov suboru, ktory bez fyzickeho .json vedla k
`DefaultCredentialsError` / "credentials file was not found").

Stara forma (cesta k `.json` suboru na disku) stale funguje kvoli spatnej
kompatibilite, ale odporuca sa import obsahu.

## Tabulky (zoznam klubov, clenov, eCP ziadosti, ...)

Vsetky tabulky maju rovnake, standardne spravanie (`ui_table.py` + `table_layout.py`):

- **sirka stlpca** - potiahnutim deliaca ciara v hlavicke; dvojklik na nu prisposobi stlpec obsahu,
- **poradie stlpcov** - potiahnutim hlavicky stlpca,
- **zoradenie** - klik na hlavicku (cisla a datumy sa radia spravne, nie ako text),
- **skryvanie stlpcov** - tlacidlo **"Columns ▾"** alebo pravy klik na hlavicku;
  tam je aj *Fit columns to contents* a *Reset table layout*,
- **zapamatanie** - rozlozenie kazdej tabulky sa uklada do `config/table_layouts.json`.

Sirsie tabulky (kluby, clenovia) maju menej podstatne stlpce (ulica, PSC, telefon,
web) **skryte v predvolenom nastavani**, aby sa tabulka zmestila na obrazovku a
stlpec *Actions* bol dostupny bez horizontalneho skrolovania. Zapnut sa daju
jednym klikom v menu *Columns*.

Stlpce su v kode adresovane **stabilnym klucom**, nie poziciou, takze zmena
poradia alebo skrytie stlpca nikdy neposle upravu do nespravneho pola.

## Testy
```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

PostgreSQL integracny test sa spusti iba vtedy, ked je nastavena premenna `ESPELEO_TEST_DATABASE_URL` na disposable databazu.

## Vyvojarske nastroje

```bash
python3 tools/preflight_check.py          # kontroly prekladov, API kontraktu, migracii, vrstiev a tajomstiev
python3 tools/preview_ecp_card.py         # offline render eCP karty, PDF, QR a overovacej stranky
```

`preview_ecp_card.py` nepotrebuje databazu, Google Cloud, FTP ani nakonfigurovane secrets - podpisovy kluc si vygeneruje jednorazovo, takze sa da vzhlad preukazu iterovat okamzite.

## Agent skills

Repozitar obsahuje skills pre Copilot CLI v `.github/skills/`:

| Skill | Kedy sa pouziva |
|---|---|
| `espeleo-design` | zmeny UI, eCP preukazu, overovacej stranky a wallet passov |
| `espeleo-preflight` | overenie zmien pred commitom, PR a merge |
| `espeleo-migrations` | zmeny databazovej schemy a migracie |
| `espeleo-context` | lacna navigacia v kode (lean-ctx + graphify), setrenie tokenov |
