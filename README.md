# Job Bot

Automatski prati job portale i šalje Telegram notifikacije za relevantne oglase.

## Portali koje prati
- HelloWorld.rs (RSS)
- Infostud.com
- MojPosao.net
- karriere.at (Graz, Wien, Klagenfurt)

## Profili
- **Junior developer** — Python, JS, PHP, Java, web dev
- **Network/Sysadmin medior** — Cisco, CCNA, sysadmin, NOC

---

## Pokretanje lokalno

### 1. Instaliraj zavisnosti
```bash
pip install -r requirements.txt
```

### 2. Napravi Telegram bota
1. Otvori Telegram, potraži `@BotFather`
2. Pošalji `/newbot`, prati upute
3. Dobićeš **token** (npr. `1234567890:ABCdef...`)
4. Pošalji poruku svom botu, zatim posjeti:
   `https://api.telegram.org/botTVOJ_TOKEN/getUpdates`
5. U JSON-u pronađi `chat.id` — to je tvoj **CHAT_ID**

### 3. Konfiguriši
Otvori `config.py` i upiši token i chat_id:
```python
TELEGRAM_BOT_TOKEN = "1234567890:ABCdef..."
TELEGRAM_CHAT_ID   = "123456789"
```
Ili napravi `.env` fajl po uzoru na `.env.example`.

### 4. Pokreni
```bash
python main.py
```

Bot će odmah uraditi prvi pregled, pa onda svakih 30 minuta.

---

## Deploy na Railway

### 1. Registracija
Idi na [railway.app](https://railway.app) → New Project → Deploy from GitHub

### 2. Environment varijable
U Railway dashboardu, pod **Variables** dodaj:
```
TELEGRAM_BOT_TOKEN  = tvoj_token
TELEGRAM_CHAT_ID    = tvoj_chat_id
ANTHROPIC_API_KEY   = sk-ant-...   (opcionalno, za AI filter)
```

### 3. Volume za bazu (da ne gubi podatke pri restartu)
Railway → Add Volume → Mount path: `/app/data`
Postavi: `DB_PATH = /app/data/jobs.db`

### 4. Procfile
Projekat već sadrži `Procfile` koji Railway čita automatski:
```
worker: python main.py
```

**Cijena:** Railway starter plan je besplatan za ~500h/mj, što je dovoljno.

---

## Prilagođavanje selektora

Sajtovi mijenjaju HTML strukturu — ako bot prestane hvatati oglase,
otvoraj sajt u Chromeu → F12 → Inspector, nađi CSS klasu kartice oglasa
i ažuriraj selektor u `scraper.py`.

## AI filter (opcionalno)

Bez `ANTHROPIC_API_KEY` bot radi samo na keyword matchingu (besplatno).
Sa ključem, Claude haiku model dodatno filtrira oglase (~$0.001 po ciklusu).
