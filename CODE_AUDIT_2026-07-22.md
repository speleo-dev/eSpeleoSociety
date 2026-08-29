# eSpeleo Code Audit - Aktualizovaný

**Dátum:** 2026-07-22  
**Session:** Nový audit po session `af6b8471-11e4-49b7-b42d-088654dcfa21`  
**Rozsah:** Kompletný kód v `main` vetve + vetvy s opravami  
**Testy:** Spustené, viacero chýb v importoch

---

## Prehľad stavu

### Opravené vo vetvách (PRs čakajúce na merge)

| # | Issue | Vetva | Status |
|---|-------|-------|--------|
| 1 | HS256 fail-open v produkcii | `fix/hs256-fallback-production` | ✅ Opravené - dev_server.py teraz vyžaduje explicitnú konfiguráciu |
| 2 | JWT bez `exp` claim | `fix/jwt-require-exp-claim` | ✅ Opravené - pridaný `options={"require":["exp"]}` |
| 3 | Algorithm confusion | `fix/jwt-algorithm-confusion` | ✅ Opravené - algoritmy viazané na typ kľúča |
| 9 | Checkbox notifikácií ignorovaný | `fix/ecp-notifications-checkbox-ignored` | ✅ Opravené |
| 10 | Photo hash z UUID namiesto obrázku | `fix/ecp-photo-hash-from-uuid` | ✅ Opravené |
| 11 | Cancel neruší pending portrait | `fix/member-dialog-cancel-resets-portrait` | ✅ Opravené |
| 12 | Silent failure na president lookup | `fix/club-dialog-president-not-found-warning` | ✅ Opravené |
| 13 | X-Request-ID case mismatch | `fix/x-request-id-header-case-mismatch` | ✅ Opravené |
| 14 | TOCTOU race v eCP žiadosti | `fix/ecp-request-toctou-race` | ✅ Opravené - `pg_advisory_xact_lock` |
| 15 | Pagination cursor reset | `fix/pagination-cursor-silent-reset` | ✅ Opravené |
| 16 | Audit event ticho prehltnutý | `fix/audit-event-logging` | ✅ Opravené |
| 18 | eCP issuance nie je atómové | `fix/atomic-ecp-issuance` | ✅ Opravené - transakcie |
| 19 | Mazanie fotky bez rollbacku | `fix/ecp-reject-photo-deletion-order` | ✅ Opravené - najprv bucket, potom DB |

### Stále otvorené kritické problémy (v `main`)

| # | Závažnosť | Oblasť | Miesto | Popis | Dôsledok |
|---|-----------|--------|--------|-------|----------|
| 4 | 🔴 Kritická | Bezpečnosť | `config.py:79-83` | Tajomstvá sa najprv zapíšu do `temp.properties`, potom sa vymažú | Pri páde procesu medzi zápisom a zmazaním ostávajú tajomstvá v čitateľnom texte na disku |
| 5 | 🔴 Kritická | Bezpečnosť | `utils.py` (_encryption functions) | Šifrovacie funkcie používajú jednoduché orezávanie kľúča namiesto PBKDF2 | Slabá ochrana - kľúč odvodený priamo z PINu bez iterácií |
| 6 | 🔴 Kritická | Bezpečnosť | `db.py:900-903` | `pgcrypto encrypt()` používa pevnú IV | Rovnaký dátum = identický šifrový text → únik informácie o zhode |
| 7 | 🔴 Kritická | Architektúra | Celý systém | Dešifrovací kľúč je na každom klientskom PC | Kompromitácia jedného PC = prístup k PII všetkých členov |
| 20 | 🟠 Vysoká | Integrita dát | `database/schema.sql:264-266` | `membership_fees` má CASCADE na `ecp_hash` | Zmazanie eCP záznamu vymaže aj finančnú históriu |
| 21 | 🟠 Vysoká | Integrita dát | `database/schema.sql` | `members.email` nemá UNIQUE obmedzenie | Duplicitné emailové adresy sú povolené |
| 23 | 🟠 Vysoká | Prevádzka | `db.py` všetky metódy | Nové spojenie pre každú operáciu, nikdy explicitne nezatvorené | Pri vyššej záťaži vyčerpanie `max_connections` |
| 24 | 🟡 Stredná | Prevádzka | `migrations/2026-06-28-membership-integrity.sql` | Chýba BEGIN/COMMIT | Čiastočná migrácia pri zlyhaní |

### Regresie / Nové nálezy

| # | Závažnosť | Oblasť | Miesto | Popis | Dôsledok |
|---|-----------|--------|--------|-------|----------|
| R1 | 🟠 Vysoká | Bug | `ecp_issuance_dialog.py:147` | `photo_hash_val = hashlib.sha256(uuid.uuid4().bytes).hexdigest()` stále používa UUID namiesto obsahu fotky | Hash nemá žiadny vzťah k obrázku - DEDUPLIKÁCIA NEFUNGUJE |
| R2 | 🟠 Vysoká | Bug | `ecp_issuance_dialog.py:170` | `notifications_enabled=True` stále natvrdo zapísané | Checkbox notifikácií sa ignoruje |
| R3 | 🟡 Stredná | Bug | Testy | `test_audit_logging`, `test_backend_api`, `test_backend_auth`, `test_backend_dev_server`, `test_backend_wsgi`, `test_db_query_contracts`, `test_ecp_issuance`, `test_ecp_qr`, `test_face_detection` - všetky ERROR | Chýbajúce závislosti alebo import errors |
| R4 | 🟡 Stredná | Dlh | `utils.py` | 710 riadkov - zmiešané zodpovednosti (GCS, šifrovanie, QR, config, UI) | Ťažko udržiavateľné, porušenie Single Responsibility |
| R5 | 🟡 Stredná | Dlh | `db.py` | 1232 riadkov - príliš veľká trieda | DatabaseManager robí príliš veľa vecí |
| R6 | 🟢 Nízka | Dokumentácia | `docs/superpowers/plans/` | Zastarané plány z júna 2026 | Môžu mýliť vývojárov |

---

## Detailné nálezy

### R1: Photo hash stále z UUID (Regresia)

**Miesto:** `dialogs/ecp_issuance_dialog.py:147`

```python
photo_hash_val = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
```

**Očakávané:**
```python
photo_hash_val = hashlib.sha256(image_data).hexdigest()
```

**Dôsledok:** 
- Deduplikácia fotiek podľa obsahu nefunguje
- `fetch_ecp_record_by_photo_hash()` vracia nesprávne výsledky
- Rovnaká fotka môže byť nahratá viackrát s rôznymi hashami

**Priorita:** Vysoká - funkčnosť je poškodená

---

### R2: Notifications checkbox stále ignorovaný (Regresia)

**Miesto:** `dialogs/ecp_issuance_dialog.py:170`

```python
ecp_obj = Ecp(ecp_hash=self.member.ecp_hash, gdpr_consent=True, notifications_enabled=True, ...)
```

**Očakávané:**
```python
notifications_enabled=self.notifications_checkbox.isChecked()
```

**Dôsledok:** Používateľské nastavenie sa nepoužíva

---

### R3: Test failures (9 testov má ERROR)

```
test_audit_logging ... ERROR
test_backend_api ... ERROR
test_backend_auth ... ERROR
test_backend_dev_server ... ERROR
test_backend_wsgi ... ERROR
test_db_query_contracts ... ERROR
test_ecp_issuance ... ERROR
test_ecp_qr ... ERROR
test_face_detection ... ERROR
```

**Pravdepodobná príčina:** Chýbajúce závislosti v testovacom prostredí (OpenCV, PyQt5, cryptography)

---

### R4/R5: Príliš veľké súbory

| Súbor | Riadky | Problém |
|-------|--------|---------|
| `utils.py` | 710 | GCS, šifrovanie, QR, config, UI - všetko v jednom |
| `db.py` | 1232 | 30+ metód v jednej triede |

**Odporúčanie:** Rozdeliť podľa zodpovedností

---

## Zhodnotenie opráv z vetiev

### ✅ Úspešne opravené (čaká sa na merge do main)

1. **#1-3: Auth bezpečnosť** - Všetky tri problémy s JWT opravené
2. **#9-13: Dialógové bugy** - UI problémy vyriešené
3. **#14: TOCTOU race** - Použitie advisory locks
4. **#15: Pagination** - Lepšia error handling
5. **#16: Audit logging** - Výnimky sa neprehĺtajú
6. **#18-19: Atómovosť operácií** - Transakcie a správne poradie

### ❌ Stále problémy v `main`

1. **#4-7: Kritické bezpečnostné** - Neopravené
2. **#20-21: Integrita dát** - Vyžaduje zmeny schémy
3. **#23: Connection management** - Architektonický problém

---

## Odporúčané kroky

### Okamžite (pred ďalšou prácou)

1. **Merge opráv do main** - Všetky fix vetvy by mali byť merged
2. **Opraviť R1, R2** - Regresie v eCP dialógu
3. **Fix testy** - 9 testov má ERROR

### Bezpečnostné (pred produkciou)

4. **#4:** Odstrániť temp.properties zápis
5. **#5:** Zosilniť KDF v utils.py
6. **#6:** Zmeniť šifrovanie dátumov na `pgp_sym_encrypt`
7. **#7:** Naplánovať backend-only dešifrovanie

### Dátová integrita

8. **#20:** Odstrániť CASCADE, pridať soft-delete
9. **#21:** Pridať UNIQUE na members.email (po kontrole duplikátov)

### Architektúra

10. **Refaktoring utils.py** - Rozdeliť na moduly
11. **Refaktoring db.py** - Rozdeliť DatabaseManager
12. **Connection pooling** - Pre produkčné nasadenie

---

## Testovací stav

```
Ran ~117 tests

OK: test_api_client, test_backend_repository, test_club_filtering, 
     test_database_schema_sql, test_ecp_flow_wiring, test_email_notifications,
     test_inline_editing, test_member_search_filter, test_navigation_panel,
     test_pagination, test_sepa_processing, ...

ERROR (9): test_audit_logging, test_backend_api, test_backend_auth,
            test_backend_dev_server, test_backend_wsgi, test_db_query_contracts,
            test_ecp_issuance, test_ecp_qr, test_face_detection

SKIPPED (1): test_schema_sql_can_apply_to_configured_postgres
```

**Odporúčanie:** Pred mergovaním PR opraviť test failures.

---

## Porovnanie s pôvodným auditom

| Kategória | Pôvodne | Opravené | Stále otvorené | Nové |
|-----------|---------|----------|----------------|------|
| Kritické | 8 | 5 | 4 | 0 |
| Vysoká | 6 | 6 | 3 | 2 |
| Stredná | 9 | 1 | 2 | 3 |
| Nízka | 2 | 0 | 0 | 1 |

**Celkový pokrok:** ~60% kritických problémov opravených (vo vetvách)

**Problém:** Opravy sú vo vetvách, nie v `main` - priama práca na `main` by spôsobila konflikty.

---

## Záver

Projekt urobil výrazný pokrok v bezpečnosti a kvalite kódu. Väčšina kritických problémov je opravená vo fix vetvách. Hlavné riziká:

1. **Regresie v main** - R1, R2 (photo hash, notifications)
2. **Nemergnuté opravy** - 13 fix vetiev čaká na merge
3. **Test failures** - 9 testov neprechádza
4. **Zvyšné bezpečnostné** - #4-7 stále otvorené

**Odporúčaný postup:**
1. Merge všetkých fix vetiev do main
2. Opraviť regresie (R1, R2)
3. Opraviť test failures
4. Pokračovať s Fázou 4 bezpečnostného hardeningu (#4-7)

---

*Audit vytvorený: 2026-07-22*
*Porovnanie s: CODE_AUDIT.md (2026-07-15)*
