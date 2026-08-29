# Report chýbajúcich závislostí - eSpeleo

**Dátum:** 2026-07-21  
**Python verzia:** 3.13.11  
**Testované prostredie:** Windows, bez sieťového pripojenia pre pip

---

## Prehľad testov

| Metrika | Hodnota |
|---------|---------|
| **Celkom testov** | 61 |
| **Úspešných** | 49 ✅ |
| **Zlyhaných (import error)** | 12 ❌ |
| **Preskočených** | 1 ⏭️ |
| **Úspešnosť** | 80.3% |

---

## Chýbajúce Python balíky

### 1. `psycopg2-binary` ❌
**Požadovaný pre:**
- `test_audit_logging`
- `test_db_query_contracts`
- Všetky testy používajúce `db.py`

**Chyba:**
```
ModuleNotFoundError: No module named 'psycopg2'
File "espeleo\db.py", line 1, in <module>
    import psycopg2
```

**Použitie v projekte:**
- PostgreSQL databázové pripojenie
- Všetky DB operácie (members, clubs, eCP, fees)

**Inštalácia:**
```bash
.venv\Scripts\pip install psycopg2-binary
```

---

### 2. `cryptography` ❌
**Požadovaný pre:**
- `test_backend_dev_server`
- `test_ecp_issuance`
- `test_ecp_qr`
- `test_wallet_pass`

**Chyba:**
```
ModuleNotFoundError: No module named 'cryptography'
File "espeleo\config.py", line 3, in <module>
    from cryptography.hazmat.primitives import hashes
File "espeleo\ecp_qr.py", line 6, in <module>
    from cryptography.exceptions import InvalidSignature
```

**Použitie v projekte:**
- Šifrovanie secrets.properties
- Ed25519 podpisy pre eCP QR kódy
- Hash funkcie

**Inštalácia:**
```bash
.venv\Scripts\pip install cryptography
```

---

### 3. `PyJWT` ❌
**Požadovaný pre:**
- `test_backend_api`
- `test_backend_auth`
- `test_backend_wsgi`

**Chyba:**
```
ModuleNotFoundError: No module named 'jwt'
File "espeleo\backend\auth.py", line 3, in <module>
    import jwt
```

**Použitie v projekte:**
- JWT token validácia (RS256/HS256)
- OAuth2/OIDC autentifikácia
- Backend API autentifikácia

**Inštalácia:**
```bash
.venv\Scripts\pip install PyJWT
```

**Poznámka:** Balík sa volá `PyJWT`, importuje sa ako `jwt`

---

### 4. `Pillow` (PIL) ❌
**Požadovaný pre:**
- `test_face_detection`
- Nepriamo `test_ecp_issuance`
- Nepriamo `test_wallet_pass`

**Chyba:**
```
ModuleNotFoundError: No module named 'PIL'
File "espeleo\tests\test_face_detection.py", line 5, in <module>
    from PIL import Image
```

**Použitie v projekte:**
- Spracovanie portrétových fotiek
- eCP karty (JPG generovanie)
- Face detection preprocessing

**Inštalácia:**
```bash
.venv\Scripts\pip install Pillow
```

**Poznámka:** Balík sa volá `Pillow`, importuje sa ako `PIL`

---

### 5. `qrcode` ❌
**Požadovaný pre:**
- `test_utils_importability`
- Nepriamo `test_wallet_request`

**Chyba:**
```
ModuleNotFoundError: No module named 'qrcode'
File "espeleo\utils.py", line 6, in <module>
    import qrcode
```

**Použitie v projekte:**
- Generovanie QR kódov pre eCP
- Wallet pass QR kódy

**Inštalácia:**
```bash
.venv\Scripts\pip install qrcode
```

---

## Súhrn inštalácie

### Kompletná inštalácia všetkých chýbajúcich balíkov:

```bash
cd espeleo
.venv\Scripts\pip install psycopg2-binary cryptography PyJWT Pillow qrcode
```

### Alternatívne - kompletná inštalácia z requirements.txt:

```bash
cd espeleo
.venv\Scripts\pip install -r requirements.txt
```

**Obsah requirements.txt:**
```
PyQt5
Babel
cryptography
google-cloud-storage
Pillow
psycopg2-binary
pycryptodome
qrcode
requests
opencv-python-headless
PyJWT
```

---

## Testy ktoré fungujú bez dodatočných balíkov ✅

Tieto testy **prešli úspešne** aj bez chýbajúcich balíkov:

1. **test_api_client** (4 testy)
   - API client komunikácia
   - Error handling
   - Bearer tokeny
   - PATCH requesty

2. **test_backend_repository** (11 testov)
   - ✅ **TOCTOU race fix** - `test_create_member_ecp_request_rejects_race_found_only_after_lock`
   - eCP request vytváranie
   - SQL pagination a filtering
   - Audit logging
   - Member profile updates

3. **test_club_filtering** (2 testy)
   - Filtrovanie klubov
   - Normalizácia textu

4. **test_database_schema_sql** (8 testov)
   - Databázové migrácie
   - Schéma tabuliek

5. **test_ecp_flow_wiring** (2 testy)
   - Wallet barcode flow
   - eCP delivery bundle

6. **test_email_notifications** (4 testy)
   - SMTP konfigurácia
   - Odosielanie emailov
   - Attachment handling

7. **test_inline_editing** (4 testy)
   - Parsovanie adries
   - Parsovanie mien
   - Dátumy

8. **test_member_search_filter** (2 testy)
   - Fast search
   - Normalizácia textu

9. **test_sepa_processing** (2 testy)
   - Spracovanie SEPA platieb
   - Klasifikácia transakcií

10. **test_setup_secrets** (2 testy)
    - Setup dialóg
    - Zber secrets

11. **test_sss_club_import** (4 testy)
    - Parsovanie SSS directory
    - Spracovanie mien

---

## Kritické komponenty bez ktorých nemôžeme pracovať

| Priorita | Balík | Dôvod |
|----------|-------|-------|
| 🔴 **Kritická** | `psycopg2-binary` | Bez DB pripojenia nefunguje väčšina funkcionalít |
| 🔴 **Kritická** | `cryptography` | Potrebné pre eCP podpisy a šifrovanie |
| 🟡 **Vysoká** | `PyJWT` | Potrebné pre backend API autentifikáciu |
| 🟡 **Vysoká** | `Pillow` | Potrebné pre eCP karty a portréty |
| 🟢 **Stredná** | `qrcode` | Potrebné pre eCP QR kódy |

---

## Odporúčané kroky

### Pre lokálny vývoj (bez DB):
1. Nainštalovať: `cryptography`, `PyJWT`, `Pillow`, `qrcode`
2. Spustiť testy: `python -m unittest discover -s tests -v`
3. Očakávaný výsledok: ~55 testov úspešných

### Pre plnú funkčnosť (s DB):
1. Nainštalovať všetky balíky: `pip install -r requirements.txt`
2. Nastaviť `ESPELEO_TEST_DATABASE_URL` pre PostgreSQL testy
3. Spustiť testy
4. Očakávaný výsledok: 61 testov úspešných

---

## Poznámka k sieťovému obmedzeniu

Pip inštalácia zlyháva na timeout kvôli obmedzenému sieťovému pripojeniu. Možné riešenia:

1. **Použiť offline wheel súbory** - stiahnuť `.whl` súbory na inom PC
2. **Použiť interný PyPI mirror** - ak je dostupný v sieti T-Systems
3. **Nainštalovať mimo proxy obmedzenia** - doma alebo na inom PC
4. **Použiť Anaconda** - môže mať predinštalované balíky

---

**Vytvorené:** 2026-07-21  
**Stav:** Čaká sa na inštaláciu balíkov
