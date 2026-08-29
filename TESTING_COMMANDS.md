# Manuálne testovanie eSpeleo - Príkazy

## 1. Spustenie automatických testov

```bash
# Vstup do adresára
cd C:\Users\A1497335\ai-projekty\eSpeleo\espeleo

# Aktivácia virtuálneho prostredia
.venv\Scripts\activate.ps1

# Spustenie všetkých testov
python -m unittest discover -s tests -v

# Alebo len špecifické testy
python -m unittest tests.test_ecp_qr -v
python -m unittest tests.test_backend_repository -v
python -m unittest tests.test_config_secrets -v
```

## 2. Manuálne testy Fázy 4

```bash
# Spustenie manuálnych testov
python test_manual_phase4.py
```

## 3. Kontrola regresií R1 a R2

### R1: Photo hash z obsahu obrázka

```bash
# Skontroluj kód
grep -n "photo_hash" dialogs/ecp_issuance_dialog.py

# Očakávaný výstup (OK):
# photo_hash_val = hashlib.sha256(image_data).hexdigest()

# Zlý výstok (FAIL):
# photo_hash_val = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
```

### R2: Notifications checkbox

```bash
# Skontroluj kód
grep -n "notifications_enabled" dialogs/ecp_issuance_dialog.py

# Očakávaný výstup (OK):
# notifications_enabled=self.notifications_checkbox.isChecked()

# Zlý výstup (FAIL):
# notifications_enabled=True
```

## 4. Kontrola bezpečnostných opráv

### #4: Žiadny temp.properties

```bash
# Skontroluj kód
grep -n "temp.properties" config.py

# Očakávaný výstup (OK):
# Nič - temp.properties sa už nepoužíva

# Alebo komentár:
# # Serialize configparser to string in memory (avoid temp file on disk)

# Zlý výstup (FAIL):
# with open("temp.properties", "w") as configfile:
```

### #5: PBKDF2 namiesto orezávania

```bash
# Skontroluj kód
grep -n "PBKDF2\|_derive_key" utils.py

# Očakávaný výstup (OK):
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# def _derive_key_with_salt(password: str, salt: bytes) -> bytes:
# iterations=100000

# Zlý výstup (FAIL):
# key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]
```

## 5. Test kompilácie

```bash
# Skontroluj či všetky súbory kompilujú
python -m compileall -q .

# Očakávaný výstup (OK):
# (žiadny výstup = žiadne chyby)
```

## 6. Git kontrola

```bash
# Stav zmien
git status

# Diff zmien
git diff

# Zoznam zmien
git diff --stat

# Log commitov
git log --oneline -5
```

## 7. Kontrola súborov

```bash
# Veľkosť kľúčových súborov
Get-ChildItem *.py | Select-Object Name, @{N="SizeKB";E={[math]::Round($_.Length/1KB,2)}}

# Počet riadkov kódu
(Get-ChildItem -Recurse -Filter *.py | Get-Content | Measure-Object).Count
```

## 8. Test importov

```bash
# Test či hlavné moduly idú importovať
python -c "import config; print('config OK')"
python -c "import utils; print('utils OK')"
python -c "import db; print('db OK')"
python -c "from dialogs.ecp_issuance_dialog import EcpIssuanceDialog; print('dialogs OK')"
python -c "from backend.auth import JwtBearerVerifier; print('backend OK')"
```

## 9. Rýchly smoke test

```bash
# Vytvor smoke test script
@"
import sys
sys.path.insert(0, '.')

try:
    import config
    print('✅ config.py')
    
    import utils
    print('✅ utils.py')
    
    from config import secret_manager
    secret_manager.secrets['crypt_key'] = 'test'
    
    # Test šifrovania
    encrypted = utils._encrypt_data('test')
    decrypted = utils._decrypt_data(encrypted)
    assert decrypted == 'test'
    print('✅ Encrypt/decrypt')
    
    print('\n🎉 Všetko funguje!')
except Exception as e:
    print(f'❌ Chyba: {e}')
    import traceback
    traceback.print_exc()
"@ | python
```

## 10. Kontrola pred PR

```bash
# 1. Testy prechádzajú
python -m unittest discover -s tests -v 2>&1 | Select-String -Pattern "OK|FAILED|ERROR"

# 2. Žiadne syntax errory
python -m compileall -q .

# 3. Git je čistý (okrem našich zmien)
git status

# 4. Máme commit
git log --oneline -3

# 5. Vetva existuje
git branch -v
```

## 11. Manuálny test UI (ak je k dispozícii displej)

```bash
# Spustenie aplikácie (vyžaduje PIN alebo setup)
python main.py

# Testovacie kroky:
# 1. Otvor eCP issuance dialog
# 2. Vyber fotku
# 3. Odškrtni "Povoliť notifikácie"
# 4. Klikni Vydaj
# 5. Skontroluj či notifikácie boli zakázané
```

## 12. Test databázy (ak je k dispozícii DB)

```bash
# Test pripojenia na DB
python -c "
import db
from config import secret_manager
# Nastav testovacie credentials alebo použi existujúce
print('DB manager created')
"
```

---

## Očakávané výsledky

✅ **Všetko OK ak:**
- 110 testov prejde
- Žiadne syntax errory
- Manuálne testy prejdú
- Importy fungujú

❌ **Problém ak:**
- Testy padajú
- Syntax errory
- Import errory
- Manuálne testy zlyhávajú
