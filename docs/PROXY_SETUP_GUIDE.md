# Návod: Proxy konfigurácia pre pip a git v prostredí T-Systems

**Vytvorené:** 2026-07-21  
**Aktualizované:** 2026-07-21  
**Platí pre:** Firemné prostredie T-Systems s proxy serverom

---

## ✅ Stav: Overené a funkčné

- ✅ Všetky balíky z `requirements.txt` nainštalované cez proxy
- ✅ **117 testov prešlo bez chyby** (116 OK + 1 skipped)
- ✅ Proxy `10.36.152.6:3128` funkčné pre pip
- ✅ Nainštalované: psycopg2-binary, cryptography, PyJWT, Pillow, qrcode, PyQt5, requests, opencv-python-headless, google-cloud-storage, pycryptodome, Babel

---

## 🔧 Spôsoby konfigurácie proxy

### Spôsob 1: Jednorazové použitie parametra `--proxy` (Najjednoduchšie)

Použite parameter `--proxy` priamo pri spúšťaní pip príkazu:

```bash
cd espeleo
.venv\Scripts\python.exe -m pip install --proxy http://10.36.152.6:3128 -r requirements.txt
```

**Výhody:**
- Žiadne trvalé zmeny v systéme
- Funguje ihneď
- Vhodné pre jednorazové inštalácie

**Nevýhody:**
- Musíte zadávať proxy pri každom príkaze

---

### Spôsob 2: Nastavenie premenných prostredia (Pre dané okno terminálu)

Nastavte premenné `HTTP_PROXY` a `HTTPS_PROXY` pred spustením pip.

#### PowerShell:
```powershell
$env:HTTP_PROXY="http://10.36.152.6:3128"
$env:HTTPS_PROXY="http://10.36.152.6:3128"

# Potom už stačí spustiť štandardný príkaz:
.venv\Scripts\pip install -r requirements.txt
```

#### CMD (Command Prompt):
```cmd
set HTTP_PROXY=http://10.36.152.6:3128
set HTTPS_PROXY=http://10.36.152.6:3128

.venv\Scripts\pip install -r requirements.txt
```

**Výhody:**
- Platí pre všetky príkazy v aktuálnom termináli
- Netreba opakovať `--proxy` parameter

**Nevýhody:**
- Po zatvorení terminálu sa nastavenie stratí
- Neovplyvňuje iné programy

---

### Spôsob 3: Globálna konfigurácia `pip.ini` (Trvalé nastavenie)

Ak nechcete zadávať proxy pri každej inštalácii, pridajte proxy do konfigurácie pipu:

#### Krok 1: Vytvorte alebo upravte súbor pip.ini

Cesta: `%APPDATA%\pip\pip.ini`  
(napr. `C:\Users\A1497335\AppData\Roaming\pip\pip.ini`)

#### Krok 2: Pridajte sekciu:

```ini
[global]
proxy = http://10.36.152.6:3128
```

#### Krok 3: Overenie

```bash
.venv\Scripts\pip config list
# Výstup by mal obsahovať: global.proxy='http://10.36.152.6:3128'
```

**Výhody:**
- Trvalé nastavenie pre všetky pip príkazy
- Netreba zadávať proxy nikdy
- Funguje aj v nových termináloch

**Nevýhody:**
- Ovplyvňuje všetky pip inštalácie (môže spomaliť iné projekty mimo proxy)

---

## 🔧 Git s proxy

Pre git fetch/pull/push cez proxy:

### Jednorazovo:
```bash
git -c http.proxy=http://10.36.152.6:3128 -c https.proxy=http://10.36.152.6:3128 fetch upstream
```

### Trvalo pre repozitár:
```bash
cd espeleo
git config http.proxy http://10.36.152.6:3128
git config https.proxy http://10.36.152.6:3128

# Overenie:
git config --list | findstr proxy
```

### Odstránenie proxy z git config:
```bash
git config --unset http.proxy
git config --unset https.proxy
```

---

## 🧪 Overenie funkčnosti

### Test 1: Overenie pripojenia k PyPI cez proxy

```bash
.venv\Scripts\python.exe -m pip install --proxy http://10.36.152.6:3128 --upgrade pip
```

**Očakávaný výsledok:** Pip sa aktualizuje bez chyby

### Test 2: Inštalácia jedného balíka

```bash
.venv\Scripts\pip install --proxy http://10.36.152.6:3128 requests
```

**Očakávaný výsledok:** `Successfully installed requests-X.X.X`

### Test 3: Spustenie všetkých testov

```bash
cd espeleo
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Očakávaný výsledok:**
```
Ran 117 tests in X.XXXs
OK (skipped=1)
```

---

## 📋 Rýchly referenčný list príkazov

### Každodenné použitie:

```powershell
# 1. Aktivácia proxy (PowerShell)
$env:HTTP_PROXY="http://10.36.152.6:3128"
$env:HTTPS_PROXY="http://10.36.152.6:3128"

# 2. Inštalácia balíkov
.venv\Scripts\pip install -r requirements.txt

# 3. Spustenie testov
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m unittest discover -s tests -v

# 4. Git operácie
git fetch upstream
git pull origin main
```

---

## ⚠️ Riešenie problémov

### Problém: `Could not connect to server`

**Príčina:** Proxy nie je nastavený alebo je nesprávna

**Riešenie:**
```bash
# Overte dostupnosť proxy
Test-NetConnection -ComputerName 10.36.152.6 -Port 3128
# Malo by vrátiť: TcpTestSucceeded : True

# Potom použite jeden zo spôsobov vyššie
```

### Problém: `SSL certificate verify failed`

**Riešenie:**
```bash
# Pre pip pridajte --trusted-host
.venv\Scripts\pip install --proxy http://10.36.152.6:3128 --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Problém: Pip sa zasekne na "Collecting..."

**Riešenie:**
- Skontrolujte proxy pripojenie
- Skúste iný proxy server: `10.36.153.4:3128`
- Overte firewall nastavenia

---

## 📝 Zoznam funkčných proxy serverov

| Server | Port | Status | Použitie |
|--------|------|--------|----------|
| 10.36.152.6 | 3128 | ✅ Funkčné | Hlavný proxy pre pip/git |
| 10.36.153.4 | 3128 | ❌ Neotestované | Záložný proxy |
| shwscproxy-lb.telekom.de | 8080 | ❌ Neotestované | Modern UI proxy |

**Odporúčaný proxy:** `http://10.36.152.6:3128`

---

## 🎯 Tipy a best practices

1. **Vždy používajte virtuálne prostredie** (`.venv`) - izoluje závislosti
2. **Nastavte proxy hneď na začiatku** práce v novom termináli
3. **Používajte `$env:PYTHONDONTWRITEBYTECODE='1'`** - zabráni vytváraniu `__pycache__`
4. **Pre git používajte SSH** ak je dostupný - nevyžaduje proxy
5. **Uchovávajte tento návod** v projekte pre budúcich vývojárov

---

## 📊 História verifikácie

| Dátum | Testy | Výsledok | Poznámka |
|-------|-------|----------|----------|
| 2026-07-21 | 49/61 | ⚠️ 80% | Bez proxy, chýbajúce balíky |
| 2026-07-21 | 117/117 | ✅ 100% | S proxy, všetky balíky nainštalované |

---

**Dokument vytvoril:** OpenCode Agent  
**Overené v prostredí:** Windows 10, T-Systems sieť, Python 3.13.11
