# Report: Pripojenie k PostgreSQL databáze na Websupport

**Dátum:** 2026-07-21  
**Testované z:** T-Systems sieť (lokálne prostredie)  
**Cieľ:** postgresql.r5.websupport.sk:5432

---

## Zhrnutie

❌ **Pripojenie nie je dostupné** z lokálnej T-Systems siete  
✅ **Konfigurácia je správna** - secrets.properties sa dešifruje  
⚠️ **Sieťové obmedzenie** - port 5432 je blokovaný alebo nie je prístupný

---

## Detailné výsledky testov

### 1. Dešifrovanie secrets.properties ✅

```
PIN: 00000000
Status: ÚSPEŠNÉ
```

**Načítané hodnoty:**
| Parameter | Hodnota |
|-----------|---------|
| DB Host | postgresql.r5.websupport.sk |
| DB Port | 5432 |
| DB Name | lacisss |
| DB User | AkwADqvz |
| DB Password | [NASTAVENÉ] |

**Poznámka:** Podľa `fix.md` bol názov databázy neskôr zmenený na `eSpeleoSoc`, ale secrets.properties stále obsahuje `lacisss`.

---

### 2. Sieťová dostupnosť ❌

**Test TCP pripojenia:**
```powershell
Test-NetConnection postgresql.r5.websupport.sk -Port 5432
```

**Výsledok:**
```
ComputerName: postgresql.r5.websupport.sk
RemotePort: 5432
TcpTestSucceeded: False

Pokusy o pripojenie:
- 37.9.175.189:5432 - FAILED (TimedOut)
- 37.9.175.188:5432 - FAILED (TimedOut)
- 37.9.175.187:5432 - FAILED (TimedOut)
- 2a00:4b40:aaaa:2008::7:5432 - FAILED (TimedOut)
- 2a00:4b40:aaaa:2008::5:5432 - FAILED (TimedOut)
- 2a00:4b40:aaaa:2008::6:5432 - FAILED (TimedOut)
```

---

## Možné príčiny

### 1. Firewall v sieti T-Systems
- Port 5432 (PostgreSQL) môže byť blokovaný na firewalle
- Externé databázové pripojenia sú často obmedzené v firemných sieťach

### 2. IP Whitelist na Websupport
- Websupport PostgreSQL môže akceptovať pripojenia len z whitelisted IP adries
- Lokálna T-Systems IP nie je povolená

### 3. Sieťové segmentácia
- Vývojová sieť nemá prístup k produkčnej databáze
- Bezpečnostné oddelenie databázovej infraštruktúry

---

## Alternatívne riešenia

### 1. Lokálny PostgreSQL (Odporúčané pre vývoj)

Nainštalovať PostgreSQL lokálne a použiť testovaciu databázu:

```bash
# Inštalácia PostgreSQL cez proxy
.venv\Scripts\pip install --proxy http://10.36.152.6:3128 psycopg2-binary

# Alebo stiahnuť PostgreSQL installer:
# https://www.postgresql.org/download/windows/

# Nastavenie testovacej databázy:
# 1. Vytvoriť databázu 'espeleo_test'
# 2. Spustiť schema.sql
# 3. Nastaviť ESPELEO_TEST_DATABASE_URL
```

### 2. SSH Tunnel

Ak máme prístup k serveru s povolenou IP:
```bash
ssh -L 5432:postgresql.r5.websupport.sk:5432 user@intermediate-server
# Potom pripojiť na localhost:5432
```

### 3. VPN pripojenie

Pripojiť sa cez VPN na sieť, z ktorej je databáza prístupná.

### 4. Docker PostgreSQL

```bash
docker run --name espeleo-postgres \
  -e POSTGRES_DB=espeleo \
  -e POSTGRES_USER=espeleo \
  -e POSTGRES_PASSWORD=espeleo \
  -p 5432:5432 \
  -d postgres:14
```

---

## Dopad na vývoj

### Čo funguje bez databázy:
✅ **117 unit testov** - všetky prechádzajú  
✅ **GUI development** - PyQt5 aplikácia sa dá spustiť  
✅ **Backend API** - testovateľné bez DB  
✅ **Logika aplikácie** - business logic testy  

### Čo vyžaduje databázu:
⚠️ **Integračné testy** - test_db_query_contracts.py  
⚠️ **Reálne dáta** - práca s produkčnými členmi/klubmi  
⚠️ **ECP issuance** - ukladanie do databázy  
⚠️ **SEPA import** - práca s transakciami  

---

## Odporúčaný postup

### Pre lokálny vývoj:
1. ✅ Pokračovať s 117 unit testami (bez DB)
2. ✅ Vývoj GUI a logiky
3. ⚠️ Mockovať DB operácie v testoch

### Pre integráciu s DB:
1. Nainštalovať lokálny PostgreSQL
2. Spustiť `database/schema.sql`
3. Nastaviť `ESPELEO_TEST_DATABASE_URL`
4. Spustiť integračné testy

### Pre produkčný prístup:
1. Vyriešiť sieťový prístup (VPN, SSH tunnel, whitelist)
2. Alebo nasadiť aplikáciu na server s prístupom k DB

---

## Záznam zo súboru fix.md

> "The desktop app crashed after saving setup values because the encrypted local configuration used database name `lacisss`, while the Websupport PostgreSQL server accepts the project database as `eSpeleoSoc`.
> Verified the encrypted `secrets.properties` can be decrypted with the local test PIN and contains DB host `db.r5.websupport.sk`, port `5432`, user value present, and password value present.
> Tested PostgreSQL connectivity against candidate database names without printing the password. `lacisss` failed with "database does not exist"; `eSpeleoSoc` connected successfully."

**Konflikt:** V súbore secrets.properties je stále `lacisss`, ale databáza na serveri je `eSpeleoSoc`.

---

## Akčné body

- [ ] Rozhodnúť sa: lokálny PostgreSQL vs. riešenie sieťového prístupu
- [ ] Ak lokálny: nainštalovať PostgreSQL a nastaviť testovaciu DB
- [ ] Ak sieťový: požiadať o otvorenie portu 5432 alebo VPN prístup
- [ ] Aktualizovať secrets.properties s správnym názvom databázy (`eSpeleoSoc`)

---

**Vytvorené:** 2026-07-21  
**Stav:** Čaká sa na rozhodnutie o spôsobe pripojenia k DB
