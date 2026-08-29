# Fáza 4 Bezpečnostný Hardening - Dokumentácia

**Dátum:** 2026-07-22  
**Stav:** Čiastočne dokončené  
**Zvyšné úlohy:** #6 (vyžaduje migráciu), #7 (architektúrna zmena)

---

## Dokončené opravy

### #4: Plaintext temp.properties ✅

**Opravené:** `config.py:79-83`

Zmena: Odstránený zápis do súboru `temp.properties`. Teraz sa serializácia deje výlučne v pamäti pomocou `io.StringIO`.

```python
# Pôvodne (nebezpečné):
with open("temp.properties", "w") as configfile:
    config.write(configfile)
# ... čítanie a mazanie

# Opravené (bezpečné):
config_buffer = io.StringIO()
config.write(config_buffer)
config_string = config_buffer.getvalue()
```

**Riziko:** Pri páde procesu už neostávajú tajomstvá na disku.

---

### #5: Slabá KDF v utils.py ✅

**Opravené:** `utils.py:170-250`

Zmena: Nahradené jednoduché orezávanie kľúča na PBKDF2 s náhodným salt.

```python
# Pôvodne (slabé):
key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')[:16]

# Opravené (silné):
salt = os.urandom(16)
key_bytes = _derive_key_with_salt(crypt_key, salt)  # PBKDF2, 100000 iterácií
```

**Formát:** salt (16B) + iv (16B) + ciphertext  
**Algoritmus:** AES-256-CBC s PBKDF2-SHA256, 100000 iterácií

**Poznámka:** Staré zašifrované dáta sa nedajú dešifrovať novou funkciou. Pri prvom načítaní starých dát sa musia dešifrovať starou funkciou a zašifrovať novou.

---

## Zvyšné kritické problémy

### #6: Pevná IV v pgcrypto (dátumy narodenia) ⚠️

**Miesto:** `db.py:964, 1100+` - `encrypt(data, key, 'aes')`

**Problém:** PostgreSQL pgcrypto `encrypt()` používa pevnú (nulovú) IV pri AES šifrovaní. To znamená, že rovnaký dátum = identický šifrový text.

**Riziko:** Útočník vie zistiť, ktorí členovia majú rovnaký dátum narodenia, čo je únik informácie.

**Riešenie:** 
1. Zmeniť na `pgp_sym_encrypt(data, key)` - používa náhodnú IV
2. Alebo používať aplikačné šifrovanie (utils._encrypt_data) miesto DB šifrovania

**Blokované:** Vyžaduje migráciu existujúcich dát a testovanie.

---

### #7: Dešifrovací kľúč na každom PC ⚠️

**Problém:** `secret_manager.get_secret("crypt_key")` je uložený lokálne na každom PC administrátora.

**Riziko:** Kompromitácia jedného PC = dešifrovanie PII všetkých členov.

**Riešenie:** Dokončenie API/OAuth2 migrácie:
1. Desktop klient autentifikácia cez OAuth2
2. Dešifrovanie len na backende
3. Desktop dostáva dešifrované dáta cez HTTPS

**Status:** Naplánované v `docs/api-oauth2-migration-plan.md`

---

## Testy po Fáze 4

```
Ran 110 tests in 1.373s
OK (skipped=1)
```

Všetky testy prechádzajú.

---

## Záver Fázy 4

| Problém | Stav | Poznámka |
|---------|------|----------|
| #4 Plaintext temp | ✅ Opravené | Okamžitá oprava |
| #5 Slabá KDF | ✅ Opravené | Zlepšená bezpečnosť šifrovania |
| #6 Pevná IV | ⚠️ Čaká | Vyžaduje migráciu DB |
| #7 Kľúč na PC | ⚠️ Čaká | Vyžaduje API migráciu |

**Doručené:** 2/4 kritických problémov okamžite opravené.

**Odporúčanie:** Pokračovať s API/OAuth2 migráciou pre #7 a naplánovať DB migráciu pre #6.

---

*Dokument vytvorený: 2026-07-22*
