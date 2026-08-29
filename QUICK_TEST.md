# Rýchle testovacie príkazy

## Základné testy (spustiť vždy pred commitom)

```powershell
# 1. Vstup do adresára
cd C:\Users\A1497335\ai-projekty\eSpeleo\espeleo

# 2. Aktivácia virtuálneho prostredia
.venv\Scripts\activate.ps1

# 3. Všetky unit testy (110 testov)
python -m unittest discover -s tests

# 4. Manuálne testy Fázy 4
python test_manual_phase4.py

# 5. Kompilácia (žiadne syntax errory)
python -m compileall -q .
```

## Kontrola konkrétnych opráv

```powershell
# R1: Photo hash z obsahu (nie UUID)
Select-String -Path "dialogs/ecp_issuance_dialog.py" -Pattern "hashlib.sha256\(image_data\)"

# R2: Notifications checkbox
Select-String -Path "dialogs/ecp_issuance_dialog.py" -Pattern "notifications_checkbox.isChecked\(\)"

# #4: Žiadny temp.properties
Select-String -Path "config.py" -Pattern "temp.properties"
# Očakávaný výsledok: Žiadny výsledok (nič sa nenájde)

# #5: PBKDF2
Select-String -Path "utils.py" -Pattern "PBKDF2HMAC"
```

## Git príkazy

```powershell
# Stav
git status
git log --oneline -5
git branch -v

# Diff
git diff
git diff --stat
```

## Očakávané výsledky

✅ **OK:**
- 110 tests OK
- All manual tests PASS
- No syntax errors
- No temp.properties in code
- PBKDF2HMAC found in utils.py

❌ **FAIL:**
- Any test FAIL/ERROR
- Syntax errors from compileall
- temp.properties found in config.py
- Old weak KDF ([:16]) in utils.py
