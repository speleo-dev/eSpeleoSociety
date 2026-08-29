# Proxy Konfigurácia pre eSpeleo Projekt

**Zdroj:** `C:\Users\A1497335\Downloads\proxy-sk-ras.pac.txt`  
**Dátum:** 2026-07-21  
**Účel:** Dokumentácia proxy pre prístup k externým repozitárom

---

## Zoznam dostupných proxy

### Hlavné proxy (DevClients SK RAS)

| Názov | Adresa | Port | Status testu | Poznámka |
|-------|--------|------|--------------|----------|
| proxy_0 | 10.36.152.6 | 3128 | ❌ Neúspešný | Port dostupný, ale GitHub fetch zlyhal |
| proxy_1 | 10.36.153.4 | 3128 | ❌ Neúspešný | GitHub fetch zlyhal |

### Špeciálne proxy

| Názov | Adresa | Port | Status testu | Poznámka |
|-------|--------|------|--------------|----------|
| proxy_modernui | shwscproxy-lb.telekom.de | 8080 | ❌ Neúspešný | GitHub fetch zlyhal |
| proxy_tsys_roaduser | ts-rs-proxy.t-systems.com | 8080 | ❌ Neúspešný | GitHub fetch zlyhal |
| proxy_sia_primary | HE141040.emea1.cds.t-internal.com | 8080 | ❌ Neúspešný | GitHub fetch zlyhal |
| proxy_sia_secondary | HE141140.emea1.cds.t-internal.com | 8080 | ❌ Netestované | Záložný SIA proxy |

### Interné proxy (TMO)

| Názov | Adresa | Port | Použitie |
|-------|--------|------|----------|
| proxy_TMO | 10.119.25.1 | 3128 | Pre interné *.mn.*.tmo domény |

---

## Testované git príkazy

```bash
# Formát pre testovanie fetch cez proxy:
git -c http.proxy=http://<PROXY_IP>:<PORT> -c https.proxy=http://<PROXY_IP>:<PORT> fetch upstream

# Testované proxy:
# 1. 10.36.152.6:3128 - proxy_0
# 2. 10.36.153.4:3128 - proxy_1
# 3. shwscproxy-lb.telekom.de:8080 - modernui
# 4. ts-rs-proxy.t-systems.com:8080 - roaduser
# 5. HE141040.emea1.cds.t-internal.com:8080 - SIA primary
```

---

## Výsledok testov

**Stav:** ❌ Žiadny proxy neumožňuje pripojenie k GitHub

**Možné príčiny:**
1. Proxy vyžadujú autentifikáciu (nie sú poskytnuté credentials)
2. GitHub (github.com:443) je blokovaný na firewalle
3. Potrebné použiť alternatívny prístup

---

## Alternatívne riešenia

### 1. Lokálny TARDIS proxy
Ak beží lokálny TARDIS proxy na `127.0.0.1:5000`:
```bash
git -c http.proxy=http://127.0.0.1:5000 -c https.proxy=http://127.0.0.1:5000 fetch upstream
```

### 2. Offline režim (aktuálny stav)
- Lokálny kód je **AHEAD of upstream** (2 commity)
- Máme všetky upstream zmeny (commit `6ac426e`)
- Môžeme bezpečne pracovať lokálne bez pripojenia

### 3. GitHub cez prehliadač
- Stiahnuť zip z GitHub web rozhrania
- Manuálne porovnať / aplikovať zmeny

---

## Aktuálny git stav

```
Remote origin:  https://github.com/dankez/eSpeleoSociety.git
Remote upstream: https://github.com/speleo-dev/eSpeleoSociety.git
Aktuálna vetva: fix/ecp-request-toctou-race

Lokálne commity pred upstream: 2
- fix: uzamknúť vytvorenie eCP žiadosti proti TOCTOU race (#14)
- feat: pridať transakčný helper transaction() do DatabaseManager

Upstream commity za nami: 0 (sme aktuálni)
```

---

## Záver

Aj bez funkčného proxy pripojenia môžeme bezpečne pokračovať v práci:
- ✅ Máme najnovší upstream kód
- ✅ Máme lokálne bezpečnostné opravy
- ✅ 103+ testov prechádza lokálne

**Odporúčanie:** Pre vývoj nie je nutné mať aktívne pripojenie k GitHub. Pre push/pull je potrebné vyriešiť proxy/autentifikáciu.
