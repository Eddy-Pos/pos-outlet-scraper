# POS ArRahnu Gold-i Scraper — Workflow

## Architecture

```
GitHub Actions (hourly cron)
        │
        │ .github/workflows/scrape_gold.yml
        ▼
  ┌─ capture_live_price.py  (one-shot WebSocket → 1 tick)
  │   ├─ Saves data/YYYY-MM-DD/gold_YYYYMMDD_HHmmss.json
  │   └─ Updates latest.json
  │
  └─ historical.py           (daily price history, on demand)
      └─ Saves historical_*.json / .csv
        │
        ▼
Commits & pushes to GitHub repo
```

## Trigger

| Source | Schedule | Status |
|--------|----------|--------|
| GitHub Actions cron | Every hour (`0 * * * *`) | ✅ Primary |
| Manual `workflow_dispatch` | On demand | ✅ |

## Components

### 1. GitHub Actions (`.github/workflows/scrape_gold.yml`)
- Runs hourly via cron
- Installs Python dependencies (`requests`, `websockets`)
- Runs `capture_live_price.py`
- Commits new data to the repo
- Sends optional Teams alert with price

### 2. Live Snapshot (`capture_live_price.py`)
- Fetches JWT from the landing page
- Connects to WebSocket, captures **1 price tick**, exits
- Saves to `latest.json` (overwrites) + `data/YYYY-MM-DD/gold_YYYYMMDD_HHmmss.json`

### 3. Continuous Scraper (`scraper.py`)
- **For local use only** — connects continuously, appends to `prices.jsonl`
- Run manually: `python scraper.py` (Ctrl+C to stop)

### 4. Historical Scraper (`historical.py`)
- Fetches daily closing prices (up to ~3 months)
- Run on demand: `python historical.py --range all`

## Output Structure

```
latest.json                    ← Latest live price tick (overwritten)
prices.jsonl                   ← Continuous tick log (local only, gitignored)
historical_1w.json / .csv      ← Daily history (1-week preset)
historical_1m.json / .csv      ← Daily history (1-month preset)
historical_3m.json / .csv      ← Daily history (3-months preset)
data/
└── YYYY-MM-DD/
    └── gold_YYYYMMDD_HHmmss.json
```

## Setup

### GitHub Actions
The workflow is self-contained — no external trigger needed. It runs on GitHub's hosted runners.

To enable Teams notifications, add a repository secret:
- **Name:** `TEAMS_WEBHOOK`
- **Value:** Your Teams webhook URL

### Local Development
```bash
git clone https://github.com/Eddy-Pos/pos-outlet-scraper.git
cd pos-outlet-scraper
pip install requests websockets
python capture_live_price.py    # one-shot test
python scraper.py               # continuous stream
python historical.py --range 3m # fetch 3-month history
```

## Data Storage
- **Cloud (source of truth):** GitHub repo → `data/YYYY-MM-DD/`, `latest.json`, `historical_*.json`
- **Local:** Run `git pull` to download the latest files to your machine

## Syncing to Local
```bash
git pull
```

## Next Steps — Enable Teams Alerts

The workflow sends a Teams notification on every run, but it needs your Teams webhook URL stored as a **repository secret**.

### 1. Create a Teams webhook
1. Open Microsoft Teams
2. Go to the channel where you want alerts (e.g. your gold price channel)
3. Click **•••** (More options) → **Connectors**
4. Find **Incoming Webhook** → click **Configure**
5. Name it `Gold Price Scraper`, create the webhook
6. Copy the webhook URL (it looks like `https://outlook.office.com/webhook/...`)

### 2. Add it as a GitHub secret
1. Go to your repo on GitHub: `https://github.com/Eddy-Pos/pos-outlet-scraper`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name:** `TEAMS_WEBHOOK`
5. **Value:** Paste the webhook URL you copied from Teams
6. Click **Add secret**

### 3. Verify it works
1. Go to the **Actions** tab of your repo
2. Click **Scrape Gold Price** workflow
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. After it completes (~30s), check your Teams channel for a gold price alert
