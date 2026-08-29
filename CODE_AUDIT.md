# Audit kódu — eSpeleo (branch `dev`)

Dátum: 2026-07-15
Rozsah: `backend/`, `dialogs/`, `database/`, `db.py`, `utils.py`, `config.py`, `sepa_processing.py`, `ecp_*.py` a súvisiaca dokumentácia.
Typ: **iba čítanie / analýza** — žiadny súbor, konfigurácia ani git stav neboli zmenené.

## Platnosť pre GitHub repozitár (`speleo-dev/eSpeleoSociety`, commit `6ac426e`)

Po prepnutí z GitLabu na GitHub som porovnal obsah pôvodne auditovaného stavu (GitLab `dev`, commit `a4fb0f5`) s aktuálnym `upstream/main` na GitHube (`6ac426e`) príkazom `git diff --stat`.

**Výsledok: obsah je bajt-identický.** Jediný rozdiel medzi oboma stavmi je zmazaný súbor `.gitlab-ci.yml` (GitLab-špecifická CI konfigurácia, na GitHube irelevantná). Žiaden zdrojový súbor (`backend/`, `dialogs/`, `database/`, `db.py`, `utils.py`, `config.py`, ...) sa nezmenil.

**Záver: všetkých 24 nájdených chýb (#1–24) platí na GitHub repozitári bezo zmeny** — rovnaké súbory, rovnaké riadky, rovnaké riziká.

Jediná výnimka je **#8 (zabudnutý GitLab token v `.git/config`)** — tá sa týkala lokálnej git konfigurácie tohto klonu, nie obsahu repozitára. Po prepnutí remote na GitHub a odstránení starého GitLab remote je toto konkrétne zistenie **vyriešené a už neplatí**. Odporúčanie zostáva vo všeobecnosti platné: nikdy neukladať token priamo do URL remote (čo sme teraz dodržali aj pri GitHub nastavení — token je v Git Credential Manageri, nie v `.git/config`).

Nález **#25** (zastaraný text v pláne o `photo_hash`/`ecp_record_id`) je taktiež bez zmeny platný — dokument aj kód sú identické ako pri pôvodnom audite.

Zoradené od najzávažnejšej po najmenej závažnú.

| # | Závažnosť | Oblasť | Miesto | Popis chyby | Dôsledok / riziko |
|---|-----------|--------|--------|--------------|--------------------|
| 1 | 🔴 Kritická | Bezpečnosť | `backend/dev_server.py:25-45` | HS256 dev-fallback je dostupný aj v produkcii — ak chýba `ESPELEO_OIDC_JWKS_URL`, backend sa ticho prepne na symetrický HS256 režim namiesto odmietnutia štartu. Naviac `issuer`/`audience` majú hardcoded default hodnoty (`auth.py:6-7`, `app.py:51-52`). | Nesprávne nakonfigurované nasadenie zlyhá "otvorene" — útočník poznajúci/uhádnuci tajný kľúč a default issuer/audience môže sfalšovať platný JWT a obísť autentifikáciu k API pre členov, kluby a eCP preukazy. |
| 2 | 🔴 Kritická | Bezpečnosť | `backend/auth.py:55-61` | Dekódovanie JWT nevynucuje prítomnosť `exp` (expirácia) cez `options={"require":["exp"]}`. | Token vydaný bez `exp` claimu platí navždy — únik/kompromitácia dev tokenu = trvalý neobmedzený prístup. |
| 3 | 🔴 Kritická | Bezpečnosť | `backend/auth.py:42-48` | Zoznam povolených algoritmov (`ESPELEO_OIDC_ALGORITHMS`) sa nekontroluje voči skutočne použitému typu kľúča (JWKS vs. symetrický). | Riziko algorithm-confusion útoku (RS256/HS256) — útočník podpíše token verejným kľúčom ako HMAC secretom. |
| 4 | 🔴 Kritická | Bezpečnosť | `config.py:68-96` (`encrypt_and_save_file`) | Tajomstvá (heslo DB, `crypt_key`, SMTP heslo, podpisovací kľúč eCP) sa najprv zapíšu nezašifrované do `temp.properties`, potom sa až vymažú. AES-CBC bez HMAC = žiadna ochrana integrity. | Pád/zabitie procesu medzi zápisom a zmazaním necháva tajomstvá v čitateľnom texte na disku natrvalo; súbor sa dá aj nepozorovane pozmeniť (padding-oracle). |
| 5 | 🔴 Kritická | Bezpečnosť | `utils.py` (`_encrypt_data`, `_decrypt_data`, `_encrypt_symmetric`...) | AES kľúč sa odvodzuje jednoduchým orezaním `crypt_key` na 16 bajtov namiesto poriadnej KDF (napr. PBKDF2). | Nízkoentropický šifrovací kľúč priamo z textu zadaného operátorom — slabá ochrana dátumov narodenia a platobných referencií členov. |
| 6 | 🔴 Kritická | Bezpečnosť | `db.py:865-884, 955-980` | Šifrovanie dátumov narodenia cez pgcrypto `encrypt(..., 'aes')` používa pevnú (nulovú) IV — deterministické šifrovanie. | Rovnaký dátum narodenia = identický šifrový text u rôznych členov → únik informácie o zhode; odporúčaná alternatíva je `pgp_sym_encrypt` s náhodnou IV. |
| 7 | 🔴 Kritická | Bezpečnosť | Architektúra (viacero súborov) | Dešifrovací `crypt_key`, ktorý odomyká PII všetkých členov, je uložený lokálne na každom desktop klientovi. | Kompromitácia jedného počítača administrátora = dešifrovanie osobných údajov všetkých členov v systéme. |
| 8 | 🔴 Kritická | Bezpečnosť | `.git/config` (remote `origin`) | Živý GitLab Personal Access Token je zabudovaný priamo v URL remote repozitára. | Ktokoľvek s prístupom k `.git/config` (napr. cez zdieľaný disk/backup) získa plný prístup k repozitáru; odporúčam presunúť do credential helpera / premennej prostredia. |
| 9 | 🟠 Vysoká | Bug | `dialogs/ecp_issuance_dialog.py:170` | Parameter `notifications_enabled=True` je natvrdo zapísaný, checkbox "Povoliť notifikácie" sa ignoruje. | Administrátor odškrtne notifikácie, no systém ich aj tak vždy označí ako povolené — checkbox nemá žiadny efekt. |
| 10 | 🟠 Vysoká | Bug | `dialogs/ecp_issuance_dialog.py:147` | `photo_hash` sa počíta z náhodného UUID (`hashlib.sha256(uuid.uuid4().bytes)`), nie z reálnych bajtov fotografie. | Rozbíja neskoršie vyhľadávanie/deduplikáciu fotiek podľa obsahu (`fetch_ecp_record_by_photo_hash`) — hash nemá žiadny vzťah k obrázku. |
| 11 | 🟠 Vysoká | Bug | `dialogs/member_management_dialog.py:454-485` (`cancel_changes`) | Zrušenie úprav (Cancel) obnoví textové polia, ale nie `pending_portrait_result`/náhľad portrétu. | Ak admin nahrá novú fotku a klikne Cancel, fotka ostane "vo fronte" — pri neskoršom Save sa nahrá fotka, ktorú admin považoval za zrušenú. |
| 12 | 🟠 Vysoká | Bug | `dialogs/club_management_dialog.py:304-317` | Ak `president_id` neexistuje medzi členmi, chyba sa iba vypíše do konzoly (`print`), meno predsedu sa ticho nastaví na `None` a uloženie sa nahlási ako úspešné. | Tichá strata dát bez upozornenia používateľa v UI. |
| 13 | 🟠 Vysoká | Bug | `backend/wsgi.py:19-27` vs. `backend/app.py:67` | WSGI adaptér prevádza hlavičku na `"X-Request-Id"` (title-case), no `app.py` hľadá presne `"X-Request-ID"` — nezhoda veľkosti písmen. | Klientom poslané request ID sa v reálnom nasadení vždy zahodí a vygeneruje sa nové → trasovanie/logovanie požiadaviek naprieč desktop↔backend je rozbité (unit testy to neodhalia, obchádzajú WSGI vrstvu). |
| 14 | 🟠 Vysoká | Bug/Concurrency | `backend/repository.py:334-403` | Kontrola "neexistuje čakajúca žiadosť" a následný insert nie sú v jednej transakcii/zámku (TOCTOU race). | Dvojklik alebo retry môže vytvoriť dve duplicitné čakajúce eCP žiadosti a dva nahraté súbory fotiek. |
| 15 | 🟠 Vysoká | Bug | `backend/pagination.py:24-68` | `decode_cursor`/`decode_id_cursor`/`decode_keyset_cursor` chytajú `except Exception` a pri poškodenom/upravenom kurzore ticho reštartujú stránkovanie od nuly. | Maskuje reálne chyby a spôsobuje zmätočné duplicitné stránkovanie namiesto zjavnej chybovej hlášky. |
| 16 | 🟠 Vysoká | Bug | `backend/app.py:131-134` (`_record_audit_event`) | Všetky výnimky z audit recordera sa ticho pohltia (`except Exception: pass`). | Ak audit DB nefunguje, každá požiadavka ticho stratí záznam v audit logu bez akéhokoľvek upozornenia — v rozpore s vlastnou požiadavkou migračného plánu na povinný audit trail. |
| 17 | 🟡 Stredná | Dizajn | `backend/pagination.py:71-76` | Nepoužívaná offset-based funkcia `paginate_items` je importovaná, ale žiadny endpoint ju reálne nepoužíva (oba zoznamy používajú SQL keyset kurzory). | Riziko, že sa v budúcnosti nový endpoint omylom napojí na túto nefiltrovanú, neefektívnu cestu namiesto správneho SQL stránkovania. |
| 18 | 🟡 Stredná | Integrita dát | `db.py:1060-1177` + dialógy vydávania eCP | Vydanie eCP (`insert_ecp → update_ecp_record_issuance → update_member_ecp_hash → update_ecp_request_status`) beží ako 4 nezávislé auto-commit transakcie, nie ako jedna atomická operácia. | Pri zlyhaní v strede sekvencie ostane eCP záznam označený ako vydaný, no člen naň nie je prepojený — nekonzistentný stav (už evidované ako neuzavreté v `fix.md`). |
| 19 | 🟡 Stredná | Integrita dát | `dialogs/ecp_approval_dialog.py` (`reject_request`) | Pri zamietnutí žiadosti sa najprv zmaže DB záznam a až potom fotka z bucketu, bez rollbacku. | Zlyhanie zmazania z bucketu necháva "osirenú" fotku v úložisku, o ktorej systém už nevie. |
| 20 | 🟡 Stredná | Integrita dát | `database/schema.sql:264-266` | `membership_fees` má `ON DELETE CASCADE` naviazané na `ecp_hash`; `db.py` má generickú funkciu `delete_ecp_record()`. | Zmazanie eCP záznamu môže nechtiac zmazať aj historické/finančné záznamy o poplatkoch. |
| 21 | 🟡 Stredná | Integrita dát | `database/schema.sql` (tabuľka `members`) | Stĺpec `email` nemá `UNIQUE` obmedzenie (na rozdiel od `clubs.email`), hoci sa email používa na doručovanie eCP. | Duplicitné emailové adresy členov sú ticho povolené. |
| 22 | 🟡 Stredná | Dokumentácia/Prevádzka | `database/README.md` | Dokumentuje iba 2 zo 4 migrácií — chýbajú `2026-06-29-club-directory-contacts.sql` a `2026-06-29-ecp-delivery-and-portraits.sql`. | Operátor, ktorý postupuje podľa README, tieto migrácie vynechá a narazí na chyby "stĺpec neexistuje" za behu. |
| 23 | 🟡 Stredná | Prevádzka | `db.py` (všetky `_fetch_all`, `_execute`, ...) | Každé volanie otvára nové PostgreSQL spojenie (`psycopg2.connect()`) a nikdy ho explicitne nezatvára (spolieha sa na GC). | Pri väčšej záťaži na zdieľanom hostingu (Websupport) riziko vyčerpania limitu `max_connections`. |
| 24 | 🟡 Stredná | Prevádzka | `database/migrations/2026-06-28-membership-integrity.sql` | Na rozdiel od ostatných troch migrácií chýba `BEGIN`/`COMMIT` obal. | Zlyhanie v strede migrácie necháva dáta zmenené bez ochranného unique indexu, ktorý mal byť vytvorený v rovnakej transakcii. |
| 25 | 🟢 Nízka / info | Dokumentácia | `docs/superpowers/plans/2026-06-18-sepa-ecp-stabilization.md:160` | Plán opisuje join `ecp_requests.photo_hash` → `ecp_records.photo_hash`, čo **už nesedí** so skutočnou schémou (stĺpec `photo_hash` v `ecp_requests` neexistuje). | **Overené: v kóde už opravené** (`db.py` správne joinuje cez `ecp_record_id`, viď `fix.md`). Ide iba o zastaraný text v staršom pláne — treba označiť ako historický/superseded, aby nezmiatol budúceho vývojára. |

## Poznámka k pokrytiu

6 `.sql` súborov nebolo spracovaných AST vrstvou grafu (chýba `tree_sitter_sql`), preto boli tieto súbory pri audite prečítané priamo agentom namiesto cez graf — audit tým nie je oslabený, len `graph.json`/`graph.html` vizualizácie SQL štruktúru podreprezentujú.

## Odporúčané poradie riešenia

1. Uzavrieť auth fail-open cestu (#1–3) pred akýmkoľvek produkčným nasadením.
2. Odstrániť plaintext-secrets-on-crash a slabú KDF (#4–5).
3. Zabaliť vydávanie eCP do skutočnej transakcie (#18) — je to kľúčový biznis proces.
4. Opraviť dva dialógové bugy, ktoré ticho klamú operátora (#9, #12).
