# eSpeleoSociety Technical Manual

## Reader and Purpose

Tento manual je pre noveho technickeho spravcu, autora projektu alebo vyvojara, ktory potrebuje rychlo pochopit myslienku, strukturu a aktualny stav systemu. Po precitani by mal vediet:

- co system robi a kde su jeho hranice,
- ako su rozdelene desktop UI, databazova vrstva, modely, utility, eCP podpisovanie a testy,
- co znamena kazda databazova tabulka,
- ake workflow su uz funkcne,
- co je iba prechodne riesenie alebo placeholder,
- ako pokracovat smerom k API/OAuth2 backendu a portalom.

Manual opisuje aktualny stav repozitara po stabilizacnych opravach. Nie je to produktovy navod pre koncoveho pouzivatela.

## Executive Summary

eSpeleoSociety je administracny system pre jaskyniarsku organizaciu. Dnes je implementovany ako PyQt desktopovy klient, ktory sluzi na spravu klubov, clenov, clenskych poplatkov, notifikacii, SEPA importu a elektronickych clenskych preukazov eCP.

Aktualny klient je hruby klient:

- vykresluje cele administracne UI,
- cita a zapisuje PostgreSQL priamo,
- uklada lokalne sifrovane secrets,
- nahrava fotky, loga a QR obrazky do Google Cloud Storage,
- generuje podpisane offline overitelne eCP QR kody.

Cielovy stav je iny:

- desktop zostane hruby administracny klient,
- PostgreSQL nebude viditelny mimo backend runtime,
- klient sa bude pripajat na HTTPS API,
- autentifikacia prebehne cez OAuth2/OIDC,
- backend bude vlastnit DB pristup, Google Cloud pristup, Google Wallet integraciu, podpisovanie eCP a autorizacne rozhodnutia,
- pribudne webovy portal pre clenov a predsedov klubov.

Najdolezitejsia aktualna hranica: priame DB pripojenie a privatny eCP podpisovaci kluc v desktope su prechodne riesenie. Dalsia velka etapa ich ma presunut do backendu.

## What Works Today

Prakticky pouzitelne casti dnes:

- desktop aplikacia vie nastartovat a otvorit setup alebo PIN dialog,
- admin vie zobrazit kluby,
- admin vie zobrazit clenov klubu,
- admin vie hladat clenov globalne,
- admin vie vytvorit a upravit klub,
- admin vie vytvorit a upravit clena,
- admin vie menit klubove prislusnosti clena,
- admin vie oznacit clensky poplatok ako zaplateny,
- admin vie importovat SEPA camt.053 vypis a ulozit validne platby,
- admin vie vytvorit notifikacnu spravu,
- admin vie vydat eCP priamo z clenskeho dialogu,
- admin vie schvalit alebo zamietnut pending eCP ziadost,
- eCP issuance generuje podpisany offline overitelny QR payload,
- eCP QR obrazok sa nahrava do GCS,
- eCP QR metadata sa ukladaju do databazy,
- test suite pokryva stabilizovane oblasti bez potreby produkcnych secrets.

Casti, ktore dnes este nefunguju ako finalny produkt:

- realna Google Wallet issuance,
- portal pre clena,
- portal pre predsedu klubu,
- API/OAuth2 backend,
- backend-only DB network izolacia,
- plny payment ledger a duplikatna ochrana bankovych importov,
- plne strukturovany audit s realnym actorom.

## Product Concept

System ma podporit obcianske zdruzenie alebo zvaz, ktory eviduje:

- jaskyniarov ako clenov,
- kluby alebo skupiny,
- prislusnost clena k jednym alebo viacerym klubom,
- primarny klub clena,
- predsedu klubu,
- clenske poplatky,
- ziadosti o elektronicky preukaz,
- fotky a metadata eCP,
- elektronicky preukaz ako QR obrazok,
- neskor aj Google Wallet pass,
- spravy alebo notifikacie pre clenov.

eCP ma byt overitelny aj offline. Preto QR kod nesmie byt iba nahodny token do databazy. Musi obsahovat minimalne zakladne udaje a podpis, ktory overovacia aplikacia vie skontrolovat verejnym klucom aj bez internetu.

## Current Architecture

Aktualna aplikacia ma tieto vrstvy:

| Vrstva | Uloha | Aktualny stav |
| --- | --- | --- |
| PyQt desktop shell | Start aplikacie, hlavne okno, navigacia, prepnutie obrazoviek | Implementovane |
| Views | Zoznam klubov, clenovia klubu, globalne hladanie, eCP ziadosti, SEPA import, notifikacie, nastavenia, reporting | Vacsinou implementovane, reporting je prazdny placeholder |
| Dialogy | Sprava klubu, sprava clena, vydanie eCP, schvalenie eCP ziadosti, setup secrets | Implementovane |
| Modely | Jednoduche Python objekty pre Club, Member, Membership, Ecp, EcpRequest | Implementovane |
| DatabaseManager | SQL dotazy, mapovanie riadkov na modely, zapis audit logov | Implementovane, ale priamo sa pripaja na PostgreSQL |
| Utility | Konfiguracia, sifrovanie datumov, GCS upload, QR helpery, SEPA XML parsing, status messages | Implementovane, niektore casti zavisia od externych secrets |
| SEPA processing | Cista logika klasifikacie transakcii bez PyQt/DB zavislosti | Implementovane a testovane |
| eCP QR podpisovanie | Ed25519 payload, QR PNG, upload handoff, DB metadata | Implementovane a testovane |
| Google Wallet | Odoslanie passu do Wallet | Placeholder |
| API backend | HTTPS API a OAuth2/OIDC | Zatial iba dokumentovany plan |
| Portaly | Portal clena a portal predsedu klubu | Neimplementovane |

## Startup Flow

Pri starte aplikacia robi tieto kroky:

1. Inicializuje PyQt aplikaciu, preklady, styl tlacidiel, font a ikonu.
2. Zisti preferovany jazyk z aplikacnej konfiguracie.
3. Ak neexistuje sifrovany secrets subor, otvori setup dialog.
4. Ak secrets subor existuje, vyziada PIN a pokusi sa ho odsifrovat.
5. Nacita aplikacne konfiguracie a podporovane locale.
6. Vytvori globalny `DatabaseManager`.
7. Vytvori hlavne okno s lavym navigacnym panelom a pravym obsahovym panelom.
8. Zobrazi hlavne okno maximalizovane.

Startup zlyha alebo skonci, ak:

- pouzivatel nezada PIN,
- secrets sa nepodari odsifrovat,
- setup dialog neulozi secrets,
- databazove secrets nie su pouzitelne pre PostgreSQL pripojenie.

## Configuration Model

System pouziva dva typy konfiguracie.

### Encrypted Secrets

Secrets su ulozene lokalne v sifrovanom subore. Subor sa sifruje PINom cez PBKDF2 a AES-CBC. Obsahuje citlive hodnoty:

| Secret | Uloha |
| --- | --- |
| `db_host` | PostgreSQL host |
| `db_port` | PostgreSQL port |
| `db_name` | Nazov databazy |
| `db_user` | DB pouzivatel |
| `db_password` | DB heslo |
| `credentials_json` | Google service account credentials |
| `project_id` | Google Cloud project |
| `bucket_name` | GCS bucket pre fotky, loga a QR obrazky |
| `logo_pic` | Nazov objektu loga organizacie |
| `crypt_key` | Symetricky kluc pre niektore lokalne/DB kryptograficke operacie |
| `ecp_signing_key_id` | Identifikator eCP podpisovacieho kluca |
| `ecp_signing_private_key_b64` | Base64 PEM privatny Ed25519 kluc pre podpis eCP QR |

Dolezita poznamka: DB heslo, service account JSON a privatny eCP podpisovaci kluc nemaju dlhodobo zostat v desktop klientovi. Patri to do backend secret managementu.

### Application Settings

Necitlive nastavenia su ulozene v beznom properties subore. Pouzivaju sa na:

- preferovanu krajinu,
- preferovany jazyk,
- menu clenskych poplatkov,
- standardnu vysku poplatku,
- zlavnenu vysku poplatku,
- datum platnosti clenstva v roku,
- obnovovacie okno,
- IBAN organizacie pre kontrolu SEPA vypisu.

Tieto nastavenia sa daju menit cez obrazovku nastaveni.

## User Interface Structure

### Main Window

Hlavne okno ma dva hlavne panely:

- navigacny panel vlavo,
- obsahovy panel vpravo.

Obsahovy panel je stacked widget. Navigacia prepina aktivnu obrazovku.

### Clubs List

Zoznam klubov zobrazuje:

- nazov klubu,
- adresu,
- krajinu,
- email,
- telefon,
- predsedu,
- pocet clenov,
- akciu na zobrazenie clenov.

Umoznuje zalozit novy klub a otvorit clenov konkretneho klubu.

### Members List

Zoznam clenov je viazany na konkretny klub. Zobrazuje:

- stav clena ako ikony,
- tituly,
- meno,
- datum narodenia,
- adresu,
- telefon,
- email,
- akciu na spravu clena.

V hlavicke zobrazuje informacie o klube, logo a legendu ikon.

Ikony signalizuju:

- aktivny clen,
- neaktivny clen,
- blokovany clen,
- ziadatel,
- host v inom ako primarnom klube,
- predseda,
- zlavnene clenstvo,
- vydany eCP,
- nezaplateny poplatok.

Zoznam podporuje aj hromadne oznacenie clenskeho poplatku ako zaplateneho.

### Member Search

Globalne hladanie clena spusta dotaz az po kratkom oneskoreni a minimalnej dlzke hladaneho textu. Hlada podla mena a priezviska. Vysledok zobrazuje stav, cele meno, primarny klub, email a akciu na spravu clena.

### Member Management

Dialog spravy clena sluzi na:

- vytvorenie clena,
- upravu osobnych a kontaktnych udajov,
- nastavenie statusu,
- nastavenie zlavneneho clenstva,
- oznacenie poplatku ako zaplateneho,
- pridanie a odstranenie klubovej prislusnosti,
- nastavenie primarneho klubu,
- vydanie eCP.

Novy clen sa vytvori v tabulke clenov a nasledne sa mu vytvori primarna klubova prislusnost.

### Club Management

Dialog spravy klubu sluzi na:

- vytvorenie klubu,
- upravu adresy a kontaktov,
- vyber predsedu zo zoznamu clenov klubu,
- upload loga do GCS,
- odstranenie predosleho loga, ak bolo nahradene novym objektom.

Predseda je referencovany cez `president_id`, nie cez samostatnu rolu v auth systeme.

### eCP Requests

Obrazovka eCP ziadosti nacitava pending ziadosti. Pre kazdu zobrazuje:

- ziadatela,
- datum ziadosti,
- status,
- tlacidlo na spracovanie.

Schvalenie ziadosti vytvori finalny eCP hash, podpise QR payload, nahra QR obrazok, aktualizuje eCP record, zapise eCP hash clena a nastavi ziadost na approved.

Zamietnutie ziadosti nastavi status rejected, zmaze eCP record a zmaze fotku z GCS.

### SEPA Import

SEPA import nacita camt.053 XML vypis, extrahuje kreditne transakcie a klasifikuje ich podla:

- najdeneho eCP hash alebo referencie,
- aktivneho eCP,
- ocakavanej sumy,
- standardneho alebo zlavneneho poplatku,
- neznameho odosielatela,
- nespravnej sumy.

Pouzivatelska tabulka stale farbi riadky, ale ulozenie platieb uz nepouziva farbu ako business logiku. Pouziva stabilny status transakcie.

### Notifications

Notifikacie umoznuju vlozit text spravy, zaciatok platnosti a dlzku platnosti. Spravy sa ukladaju so statusom pending. Aktualne ide o evidenciu sprav, nie o plne implementovany distribucny system.

### Settings

Nastavenia menia lokalnu aplikacnu konfiguraciu:

- krajina,
- jazyk,
- mena,
- vyska poplatkov,
- platnost clenstva,
- obnovovacie okno,
- IBAN.

### Reporting

Reporting obrazovka existuje, ale je prazdna. Je to miesto pre buduce reporty.

## Database Overview

Aktualna PostgreSQL schema pochadza z Adminer dumpu od autora projektu a bola upravena do lokalneho bootstrapu pre vyvoj a testy. Schema cieli na PostgreSQL 14 a pouziva pgcrypto.

Databaza je rozdelena na tieto oblasti:

- clenovia,
- kluby,
- vztah clen-klub,
- poplatky,
- eCP zaznamy,
- eCP ziadosti,
- certifikaty,
- notifikacie,
- konfiguracia,
- audit logy.

### High-Level Relationships

Zakladne vztahy:

- clen moze byt vo viacerych kluboch,
- klub moze mat viacerych clenov,
- vztah clen-klub nesie informaciu, ci je klub primarny,
- klub moze mat predsedu, ktory je clen,
- eCP ziadost patri clenovi,
- eCP ziadost moze ukazovat na eCP record,
- aktualny eCP clena je nepriamo zviazany cez `ecp_hash`,
- poplatok patri clenovi a moze odkazovat na eCP hash,
- certifikaty patria clenovi,
- logy su centralny auditny zapis.

Textovy model vztahov:

```text
members 1--N club_affiliations N--1 clubs
clubs president_id --0/1--> members
members 1--N membership_fees
members 1--N member_certificates
members 1--N ecp_requests
ecp_requests N--0/1 ecp_records
members ecp_hash --0/1--> ecp_records.ecp_hash
membership_fees ecp_hash --0/1--> ecp_records.ecp_hash
```

## Database Tables in Detail

### members

`members` je hlavna tabulka clena.

Ucel:

- drzi identitu clena,
- drzi kontaktne udaje,
- drzi status clenstva,
- drzi aktualny eCP hash,
- drzi informaciu o zlavnenom clenstve.

Najdolezitejsie polia:

| Pole | Vyznam |
| --- | --- |
| `member_id` | Primarny kluc clena |
| `first_name` | Meno |
| `last_name` | Priezvisko |
| `birth_date_encrypted` | Sifrovany datum narodenia |
| `email` | Email, potrebny pre eCP vydanie |
| `phone` | Telefon |
| `ecp_hash` | Aktualny hash vydaneho eCP |
| `member_status` | Stav clena |
| `discounted_membership` | Ci ma clen zlavneny poplatok |
| `title_prefix` | Titul pred menom |
| `title_suffix` | Titul za menom |
| `street`, `city`, `zip_code`, `country` | Adresa |
| `member_since` | Datum vstupu alebo evidencie |

Povolene statusy:

- `applicant`,
- `active`,
- `inactive`,
- `blocked`.

V kode sa status pouziva na ikony, filtrovanie a eCP payload. Status nie je zatial naviazany na OAuth2 roly.

Dolezite pravidla:

- `birth_date_encrypted` je povinne pole.
- `ecp_hash` ma unikatny index.
- eCP vazba nie je cez `member_id` v eCP tabulke, ale cez hash.
- Email ma default prazdny string, nie `NULL`; to ma dopad na buduce unikatne constrainty.

Rizika a odporucania:

- Pri OAuth2 portali bude treba mapovat externu identitu na `member_id`.
- Email by nemal byt jediny autoritativny identifikator bez potvrdenia.
- Pre produkciu treba jasne pravidla pre anonymizaciu alebo vymazanie clena.

### clubs

`clubs` reprezentuje jaskyniarsky klub alebo skupinu.

Ucel:

- drzi nazov klubu,
- kontakt a adresu,
- predsedu,
- datum zalozenia,
- URL loga.

Najdolezitejsie polia:

| Pole | Vyznam |
| --- | --- |
| `club_id` | Primarny kluc klubu |
| `club_name` | Nazov klubu |
| `phone` | Telefon |
| `email` | Email klubu |
| `president_id` | Odkaz na clena, ktory je predseda |
| `foundation_date` | Datum zalozenia |
| `logo_url` | Verejne URL loga v GCS |
| `street`, `city`, `zip_code`, `country` | Adresa |

Vztahy:

- `president_id` odkazuje na `members.member_id`.
- Pri zmazani clena sa prezident nastavi na `NULL`.
- Clenovia klubu sa neukladaju v tejto tabulke, ale cez `club_affiliations`.

Dolezite pravidla:

- `email` ma unikatny index.
- Pri prazdnych emailoch moze unikatny index sposobit problem, ak DB povazuje viac prazdnych stringov za duplicitu. Buduce riesenie by malo pouzit `NULL` alebo partial unique index.

### club_affiliations

`club_affiliations` je join tabulka medzi clenmi a klubmi.

Ucel:

- umoznit, aby clen patril do viacerych klubov,
- rozlisit primarny klub clena,
- podporit zobrazenie hosta v inom klube.

Polia:

| Pole | Vyznam |
| --- | --- |
| `member_id` | Odkaz na clena |
| `club_id` | Odkaz na klub |
| `is_primary_club` | Ci je klub primarny pre clena |

Primarny kluc je dvojica `member_id`, `club_id`.

Vztahy:

- zmazanie clena zmaze jeho prislusnosti,
- zmazanie klubu zmaze prislusnosti k nemu.

Dolezita medzera:

- Schema zatial nevynucuje, ze clen ma najviac jeden primarny klub.
- Kod vie nastavit primarny klub, ale SQL constraint by mal do buducna zabranit dvom primarnym klubom pre jedneho clena.

Odporucany buduci constraint:

```sql
CREATE UNIQUE INDEX one_primary_club_per_member
ON club_affiliations(member_id)
WHERE is_primary_club = true;
```

### membership_fees

`membership_fees` eviduje zaplatene clenske poplatky.

Ucel:

- oznacit, ze clen zaplatil za konkretny rok,
- podporit hromadne oznacenie poplatkov,
- podporit ulozenie validnych SEPA platieb.

Polia:

| Pole | Vyznam |
| --- | --- |
| `fee_id` | Primarny kluc poplatku |
| `member_id` | Odkaz na clena |
| `ecp_hash` | Volitelny odkaz na eCP hash |
| `year` | Rok poplatku |
| `fee_type` | Typ poplatku, default `standard` |

Aktualna logika:

- zoznam clenov pri nacitani zistuje, ci existuje poplatok pre aktualny rok,
- clensky dialog vie poplatok oznacit ako zaplateny,
- hromadna akcia vie vlozit poplatok pre oznacenych clenov,
- SEPA import uklada iba transakcie so statusom `valid`.

Dolezite medzery:

- Neexistuje unikatny constraint na `member_id`, `year`, `fee_type`.
- Neexistuje plny ledger importovanych bankovych transakcii.
- Neuklada sa suma, mena, datum zauctovania, IBAN odosielatela, identifikator transakcie ani identifikator vypisu.

Pre realnu uctovnu stopu treba neskor doplnit samostatny payment ledger.

### ecp_records

`ecp_records` je hlavna tabulka eCP zaznamov.

Ucel:

- uchovat eCP hash,
- uchovat referenciu na fotku,
- uchovat GDPR a notifikacne suhlasy,
- rozlisit aktivny a neaktivny eCP,
- uchovat kontrolny hash,
- uchovat metadata podpisaneho QR,
- pripravit stav pre Google Wallet.

Polia:

| Pole | Vyznam |
| --- | --- |
| `ecp_record_id` | Primarny kluc eCP recordu |
| `ecp_hash` | Verejne/pouzivatelske eCP ID alebo token |
| `gdpr_consent` | Suhlas so spracovanim pre eCP |
| `notifications_enabled` | Ci clen povolil notifikacie |
| `photo_hash` | Nazov/fingerprint fotky v GCS bez pripony |
| `ecp_active` | Ci je eCP aktivny |
| `check_hash` | Lokalne overovaci HMAC-like token |
| `qr_url` | Verejne URL QR PNG objektu |
| `qr_key_id` | ID podpisovacieho kluca |
| `qr_payload` | Podpisany JSON payload |
| `qr_payload_hash` | SHA-256 hash serializovaneho QR payloadu |
| `issued_at` | Cas vydania |
| `valid_until` | Datum platnosti |
| `wallet_status` | Stav Google Wallet issuance |
| `wallet_object_id` | Buduce ID Google Wallet objektu |
| `wallet_last_error` | Posledna chyba Google Wallet issuance |

Aktualna logika:

- pri direct eCP vydani sa najprv vytvori eCP record,
- nasledne sa podpisane QR metadata ulozia do toho isteho recordu,
- pri approval flow sa existujuci pending record aktualizuje finalnym eCP hashom a QR metadatami,
- `ecp_active` sa nastavi na true az pri finalnej issuance update.

Preco je `ecp_record_id` dolezity:

- Autorova schema nema `member_id` v `ecp_records`.
- eCP ziadost preto nemoze spoliehat na join cez `ecp_records.member_id`.
- Stabilny vztah request -> record ide cez `ecp_requests.ecp_record_id`.

Dolezite medzery:

- `photo_hash` pravdepodobne ma byt unikatny, schema to zatial nevynucuje.
- `wallet_status` nema check constraint.
- eCP vydanie by malo byt transakcne spolu s QR uploadom, DB update a Wallet stavom.
- Privatne podpisovanie patri do backendu.

### ecp_requests

`ecp_requests` eviduje ziadosti o eCP.

Ucel:

- clen alebo portal vytvori ziadost,
- admin alebo predseda ju schvali alebo zamietne,
- ziadost ukazuje na eCP record s fotkou a stavom.

Polia:

| Pole | Vyznam |
| --- | --- |
| `request_id` | Primarny kluc ziadosti |
| `member_id` | Odkaz na clena |
| `status` | Stav ziadosti |
| `request_date` | Datum vytvorenia ziadosti |
| `ecp_record_id` | Odkaz na eCP record |

Aktualne statusy pouzivane kodom:

- `pending`,
- `approved`,
- `rejected`.

Dolezite pravidla:

- pending view nacitava iba `pending`,
- approval aktualizuje status na `approved`,
- rejection aktualizuje status na `rejected` a maze suvisiaci eCP record/fotku.

Medzery:

- Schema nema check constraint na status.
- Nie je tam historia zmen statusov.
- Nie je tam actor, ktory ziadost schvalil alebo zamietol.
- Nie je tam dovod zamietnutia.

### member_certificates

`member_certificates` eviduje certifikaty alebo kvalifikacie clena.

Polia:

| Pole | Vyznam |
| --- | --- |
| `member_id` | Odkaz na clena |
| `sequence_number` | Poradie certifikatu pre clena |
| `name` | Nazov certifikatu |
| `issue_date` | Datum vydania |
| `valid_until` | Platnost |
| `url` | Odkaz na dokument |

Primarny kluc je `member_id`, `sequence_number`.

Aktualny UI dialog pre vydanie eCP ma lokalny zoznam certifikatov, ale kompletne prepojenie certifikatov na DB workflow treba este preverit a dopracovat.

### notifications

`notifications` eviduje spravy pre clenov.

Polia:

| Pole | Vyznam |
| --- | --- |
| `notification_id` | Primarny kluc |
| `created_at` | Cas vytvorenia |
| `text` | Text spravy |
| `valid_from` | Zaciatok platnosti |
| `valid_to` | Koniec platnosti |
| `status` | Stav spravy |

Aktualne UI vie spravu vytvorit a zmazat. Distribucny mechanizmus na email, push alebo portal zatial nie je implementovany.

### ess_config

`ess_config` je DB key-value konfiguracia.

Polia:

| Pole | Vyznam |
| --- | --- |
| `config_key` | Kluc konfiguracie |
| `config_value` | Hodnota |

Aktualna desktop aplikacia primarne pouziva lokalny properties config, nie tuto tabulku. Do buducna moze byt `ess_config` backendova konfiguracia, ale nemala by obsahovat plaintext secrets.

### db_logs

`db_logs` je audit log tabulka.

Polia:

| Pole | Vyznam |
| --- | --- |
| `log_id` | Primarny kluc |
| `action` | Typ akcie, napriklad INSERT, UPDATE, DELETE |
| `table_name` | Nazov cielovej tabulky |
| `user_name` | DB pouzivatel alebo actor |
| `details` | Textovy detail |
| `log_timestamp` | Cas zapisu |

Aktualny stav:

- DB manager zapisuje logy pri vybranych zapisovych operaciach,
- pred zapisom detailov sa rediguju citlive hodnoty,
- redakcia pokryva eCP hash, photo hash, birth date, email, telefon, adresu, credentials, crypt key a DB password.

Medzery:

- `user_name` je dnes casto DB pouzivatel, nie realny OAuth2 actor.
- `details` je text, nie strukturovany JSON.
- Chyba vysledok operacie, entity id ako samostatne pole, request id a korelacny id.

Pre backend treba audit log prerobit na server-side audit s realnym actorom.

## Indexes, Constraints, and Integrity

Aktualne existuju:

- primarne kluce pre vsetky hlavne tabulky,
- unikatny index na `members.ecp_hash`,
- unikatny index na `clubs.email`,
- unikatny index na `ecp_records.ecp_hash`,
- index na `member_certificates.member_id`,
- index na `ecp_records.valid_until`,
- index na `ecp_records.wallet_status`,
- foreign keys pre klubove prislusnosti, predsedu, eCP requesty, certifikaty a poplatky.

Odporucane doplnenia:

- index na `club_affiliations.club_id`,
- index na `clubs.president_id`,
- index na `ecp_requests.status, request_date`,
- index na `ecp_requests.ecp_record_id`,
- index na `membership_fees.member_id, year`,
- index alebo trigram pre hladanie v `members.last_name, first_name`,
- unique constraint pre jeden poplatok na clena/rok/typ,
- partial unique constraint pre jeden primarny klub na clena,
- check constraint pre `ecp_requests.status`,
- check constraint pre `wallet_status`,
- unique constraint alebo index pre `ecp_records.photo_hash`.

## eCP Issuance and Offline QR

eCP issuance dnes riesi dve veci:

1. vytvorenie internych DB zaznamov a GCS objektov,
2. vytvorenie podpisaneho QR, ktory sa da overit offline.

### Why Signed QR

Ak by QR obsahovalo iba nahodny hash, offline skener by nevedel nic overit. Vedel by iba poslat hash na server. To nesplna poziadavku offline overenia.

Aktualny QR preto obsahuje JSON payload:

- schema verziu,
- ID clena,
- display meno,
- primarny klub,
- status clena,
- datum vydania,
- datum platnosti,
- zaplateny rok,
- algoritmus,
- key id,
- Ed25519 podpis.

Skener potrebuje iba verejny kluc k danemu `key id`. Privatny kluc netreba na overenie.

### Trust Model

Offline overenie vie potvrdit:

- payload podpisala entita s privatnym klucom,
- payload nebol zmeneny,
- `valid_until` este neexpiroval,
- payload patri k podporovanej scheme.

Offline overenie nevie potvrdit:

- ci clen nebol medzicasom zablokovany,
- ci bol eCP revokovany po vydani,
- ci sa zmenil klub alebo status po vytvoreni QR,
- ci je Google Wallet pass aktualny.

Pre revokaciu a aktualny stav treba online kontrolu alebo pravidelne kratke platnosti.

### Direct eCP Issuance Flow

Pri vydani eCP priamo z clenskeho dialogu:

1. Skontroluje sa, ze clen existuje a ma email.
2. Pouzivatel nacita fotku.
3. Pouzivatel musi zaskrtnut GDPR suhlas.
4. Vygeneruje sa `photo_hash`.
5. Vygeneruje sa novy `ecp_hash`.
6. Nacita sa primarny klub clena.
7. Nacita sa podpisovaci kluc a key id zo secrets.
8. Vytvori sa podpisany claim a QR PNG.
9. QR PNG sa nahra do GCS.
10. Fotka sa nahra do GCS.
11. Vytvori sa eCP record.
12. eCP record sa aktualizuje QR metadatami a aktivuje sa.
13. Clenovi sa nastavi aktualny `ecp_hash`.

Ak chyba podpisovaci kluc alebo QR upload zlyha, eCP sa neaktivuje.

### eCP Request Approval Flow

Pri schvaleni ziadosti:

1. Nacita sa clen zo ziadosti.
2. Nacita sa eCP record cez `ecp_record_id`.
3. Vygeneruje sa finalny `ecp_hash`.
4. Vytvori sa podpisany QR payload.
5. QR PNG sa nahra do GCS.
6. Existujuci eCP record sa aktualizuje finalnym hashom, QR metadatami a aktivnym stavom.
7. Clenovi sa nastavi aktualny `ecp_hash`.
8. Ziadost sa nastavi na `approved`.
9. Zavola sa Google Wallet placeholder.

Transakcnost je zatial obmedzena. DB update, GCS upload a Wallet stav nie su este riadene backendovou transakcnou orchestriou.

### eCP Request Rejection Flow

Pri zamietnuti:

1. Ziadost sa nastavi na `rejected`.
2. eCP record sa zmaze.
3. Fotka sa zmaze z GCS.
4. Dialog sa zavrie ako spracovany.

Ak zlyha mazanie GCS objektu, aktualne je to logovane cez vypis, nie cez robustny retry mechanizmus.

## Google Wallet Status

Databaza uz ma polia pre Wallet:

- `wallet_status`,
- `wallet_object_id`,
- `wallet_last_error`.

Aktualne vsak realna Google Wallet integracia nie je implementovana. Existuje iba funkcia, ktora simuluje odoslanie a vracia uspech.

Odporucany stavovy model:

- `not_issued`,
- `pending`,
- `issued`,
- `failed`,
- `revoked`,
- `expired`.

Buduca backend implementacia by mala:

- vytvorit alebo aktualizovat Wallet class/object,
- ulozit Wallet object id,
- ulozit poslednu chybu,
- retryovat zlyhania,
- udrzat DB stav a Wallet stav konzistentny,
- neposielat service account credentials do desktopu ani portalu.

## SEPA Payment Processing

SEPA import ma dve oddelene casti:

- XML parser extrahuje transakcie z camt.053,
- cista processing funkcia klasifikuje transakcie.

Parser pracuje s kreditnymi polozkami a cita:

- IBAN vypisu,
- sumu,
- menu,
- datum zauctovania,
- referenciu transakcie,
- kandidata na eCP hash z remittance alebo EndToEndId,
- IBAN platcu.

Klasifikacia pouziva:

- standardny poplatok,
- zlavneny poplatok,
- eCP record,
- clena,
- aktivitu eCP.

Statusy transakcii:

| Status | Vyznam |
| --- | --- |
| `valid` | Znamy aktivny eCP a presna ocakavana suma |
| `underpaid` | Znamy aktivny eCP, ale suma je nizsia |
| `overpaid` | Znamy aktivny eCP, ale suma je vyssia |
| `inactive_expected_amount` | eCP nie je aktivny, ale suma sedi |
| `inactive_wrong_amount` | eCP nie je aktivny a suma nesedi |
| `unknown_reference_expected_amount` | Referencia nie je znama, ale suma vyzera ako poplatok |
| `unknown_reference_wrong_amount` | Referencia nie je znama a suma nesedi |
| `invalid_amount` | Suma sa neda spracovat |
| `unprocessed` | Pociatocny stav pred klasifikaciou |

Ulozenie platieb dnes uklada iba status `valid`.

Dolezite medzery:

- system neuklada importny batch,
- neuklada bankovy transaction id,
- nema ochranu proti duplicitnemu importu tej istej transakcie,
- nema workflow pre rucne sparovanie neznamej platby,
- `membership_fees.ecp_hash` ma v scheme FK vyznam smerom na eCP record, ale jedna aktualna zapisova cesta do neho uklada sifrovanu platobnu referenciu. Toto je znama nekonzistencia a pri platobnom redesign-e treba rozhodnut, ci pole ostane eCP FK, alebo vznikne samostatne pole pre platobnu referenciu.

## Audit Logging

Aktualne audit logovanie je centralizovane cez DB manager. Pri zapisovych operaciach sa vola interny log helper.

Co funguje:

- loguju sa insert/update/delete operacie vo vybranych tabulkach,
- citlive hodnoty v textovych detailoch sa rediguju,
- testy overuju, ze PII a tokeny sa neukladaju v surovej podobe.

Co treba zlepsit:

- logovat realneho pouzivatela, nie DB username,
- zaviest strukturovane log pole,
- logovat entity type a entity id oddelene,
- rozlisit success/failure,
- doplnit request/correlation id,
- robit audit v backende, nie v desktope.

## Security Model

### Current Controls

Aktualne existuju tieto ochrany:

- secrets subor je lokalne sifrovany PINom,
- DB birth date je sifrovany,
- audit log detaily su redigovane,
- eCP QR je podpisany asymetrickym klucom,
- offline skener moze overovat iba verejnym klucom,
- lokalne secrets a token subory su ignorovane gitom.

### Current Security Gaps

Hlavne rizika aktualnej architektury:

- desktop ma DB heslo,
- desktop ma Google service account credentials,
- desktop ma privatny eCP podpisovaci kluc,
- PostgreSQL musi byt dostupny z klientskych pocitacov,
- autorizacia nie je OAuth2/OIDC,
- neexistuje objektove opravnenie pre predsedov klubov,
- Google Wallet je placeholder,
- eCP issuance nie je transakcne koordinovany backendom,
- portal identity mapping neexistuje.

### Target Security Direction

Ciel:

- desktop a portaly nemaju DB credentials,
- desktop a portaly nemaju service account JSON,
- desktop a portaly nemaju privatne podpisovacie kluce,
- vsetky zapisy idu cez backend API,
- backend robi autorizaciu na urovni objektov,
- PostgreSQL je dostupny iba backendu,
- OAuth2/OIDC provider vydava tokeny,
- backend mapuje token claims na clena, admina alebo predsedu.

## Tests and Verification

Testy su pisane cez Python unittest. Pokryvaju hlavne stabilizovane casti.

Pokryte oblasti:

- audit redaction,
- schema bootstrap a migracia QR metadat,
- DB query contracty bez realnej DB cez mock cursor,
- eCP issuance a QR metadata,
- offline QR podpis a overenie,
- SEPA processing,
- setup secrets polia,
- Google Wallet helper pre dict aj objekt,
- importovatelnost utility modulu bez optional dependencies.

Zakladny prikaz:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

PostgreSQL schema integration test je opt-in:

```bash
ESPELEO_TEST_DATABASE_URL=postgresql://user:password@localhost:5432/espeleo_test \
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_database_schema_sql -v
```

Integracny test spustat iba proti disposable databaze, pretoze bootstrap schema maze a znovu vytvara aplikacne tabulky.

## Local Database Setup

Pre lokalny vyvoj existuje bootstrap schema odvodena od autorovho Adminer dumpu. Nie je to produkcna migracia.

Lokalny postup:

1. Vytvor prazdnu PostgreSQL databazu.
2. Nastav connection string do `ESPELEO_TEST_DATABASE_URL`.
3. Aplikuj bootstrap schema.
4. Spusti integracny test.

Priklad:

```bash
psql "$ESPELEO_TEST_DATABASE_URL" -f database/schema.sql
```

Pre existujuce databazy pouzi aditivne migracie. Aktualne najdolezitejsia migracia doplna QR metadata do `ecp_records`:

```bash
psql "$DATABASE_URL" -f database/migrations/2026-06-23-ecp-qr-metadata.sql
```

## Deployment Reality Today

Dnes system nie je pripraveny ako bezpecna multi-user webova produkcia. Je to desktop administracny klient, ktory vyzaduje:

- Python runtime,
- PyQt dependencies,
- PostgreSQL pristup,
- Google Cloud credentials,
- lokalne encrypted secrets,
- lokalny PIN,
- GCS bucket.

Pre male interne pouzitie to moze fungovat ako prechodny stav. Pre portal a sirsiu prevadzku treba backend.

## API and Portal Target Architecture

Cielova architektura:

```text
Desktop admin client  ---> HTTPS API ---> PostgreSQL
Member portal         ---> HTTPS API ---> Google Cloud Storage
President portal      ---> HTTPS API ---> Google Wallet
Offline QR scanner    ---> Public key only
```

Backend ma vlastnit:

- DB connection pool,
- autorizacne pravidla,
- audit log,
- eCP signing,
- Google Cloud upload,
- Google Wallet issuance,
- SEPA import write model,
- portal request workflow.

Minimalne roly:

- `admin`: plna sprava,
- `club_president`: sprava clenov a eCP ziadosti iba pre vlastny klub,
- `member`: vlastny profil, vlastna eCP ziadost, vlastny stav poplatkov.

Prve API hranice:

- kluby,
- clenovia klubu,
- hladanie clenov,
- vytvorenie/uprava clena,
- poplatky,
- eCP ziadosti,
- schvalenie/zamietnutie eCP,
- import SEPA vypisu.

## Recommended Next Technical Steps

Najlepsi postup po aktualnom stave:

1. Implementovat realnu Google Wallet issuance vrstvu.
2. Doplnit stavove prechody pre `wallet_status`.
3. Zabezpecit, aby eCP approval nevedel ticho divergovat medzi DB, QR uploadom a Wallet stavom.
4. Navrhnut backend API kontrakty ako DTO, nie ako priame kopie tabuliek.
5. Vytvorit backend skeleton s OAuth2/OIDC validaciou tokenov.
6. Presunut eCP podpisovanie do backendu.
7. Presunut GCS upload do backendu.
8. Prepnut desktop read-only endpointy na API.
9. Prepnut desktop write endpointy na API.
10. Doplnit member portal pre vlastny profil, eCP request, fotku a stav poplatkov.
11. Doplnit president portal pre clenov vlastneho klubu.
12. Odobrat DB heslo, service account JSON a privatny podpisovaci kluc z desktop secrets.
13. Obmedzit PostgreSQL network access iba na backend.

## Known Technical Debt

Najdolezitejsie dlhy:

- Priame SQL v desktope.
- Ziadna API vrstva.
- Ziadne OAuth2 roly.
- Ziadny portal.
- Google Wallet placeholder.
- Neplny payment ledger.
- Nejednoznacne pouzitie `membership_fees.ecp_hash`.
- Nie vsetky DB constrainty chrania business invariants.
- Audit log nie je strukturovany.
- Niektore utility miesaju UI, cloud a crypto zodpovednosti.
- Reporting je prazdny.
- Certifikaty nie su dotiahnute ako plny workflow.

## Glossary

| Pojem | Vyznam |
| --- | --- |
| eCP | Elektronicky clensky preukaz |
| eCP hash | Token/hash pouzivany ako identifikator preukazu alebo platobna referencia |
| eCP record | DB zaznam s fotkou, aktivitou, QR metadatami a Wallet stavom |
| eCP request | Ziadost o vydanie eCP |
| QR payload | JSON data zakodovane v QR kode |
| Ed25519 | Asymetricky podpisovy algoritmus pouzity pre offline overenie |
| GCS | Google Cloud Storage |
| Wallet | Google Wallet pass integracia |
| Thick client | Klient, ktory obsahuje vacsinu UI a business logiky |
| Backend API | Cielova serverova vrstva medzi klientmi a databazou |
| OAuth2/OIDC | Cielovy autentifikacny standard |
| PKCE | Flow pre verejnych klientov bez client secret |
| SEPA camt.053 | XML bankovy vypis pouzivany na import platieb |

## Quick Mental Model

Ak si treba system zapamatat jednou vetou:

> Dnes je to PyQt administracny klient, ktory priamo spravuje PostgreSQL data o kluboch, clenoch, poplatkoch a eCP; uz vie generovat offline podpisane eCP QR, ale musi sa postupne rozdelit tak, aby databazu, podpisovanie, cloud a Wallet vlastnil OAuth2 backend.
