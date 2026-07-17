# POS ArRahnu Gold-i — Web Scraper

## Project Overview

Scrapes gold prices from [POS ArRahnu Gold-i](https://posarrahnugold.ace2u.com/index-landing.php), a Malaysian digital gold investment platform. Two scraper scripts provide real-time and historical price data — no authentication required.

## Files

| File | Purpose |
|---|---|---|
| `capture_live_price.py` | One-shot live price capture → `latest.json` + `data/…/gold_*.json` (for GH Actions) |
| `scraper.py` | Real-time live gold prices via WebSocket → `prices.jsonl` (local continuous use) |
| `historical.py` | One-shot daily historical price fetch → JSON + CSV |
| `prices.jsonl` | Live price output (appended continuously by `scraper.py`; gitignored) |
| `latest.json` | Latest live price snapshot (overwritten each capture) |
| `historical_1w.json` / `.csv` | ~30 days of daily history (1-week preset) |
| `historical_1m.json` / `.csv` | ~30 days of daily history (1-month preset) |
| `historical_3m.json` / `.csv` | ~79 days of daily history (3-months preset) |
| `doc.md` | This file |

## Live Price Scraper (`scraper.py`)

Connects to the site's WebSocket endpoint to stream real-time gold buy/sell prices per gram.

**How it works:**
1. Fetches the landing page and extracts the embedded JWT token
2. Connects to `wss://posarrahnugoldprodapi.ace2u.com/mygtp.php` with the token
3. Receives price ticks (~every 1 second) and appends them to `prices.jsonl`
4. Auto-reconnects on disconnect; refreshes JWT every 6 hours

**Output format (JSON Lines):**
```json
{"timestamp": "2026-07-17T09:05:56+00:00", "buy_price": 538.75, "sell_price": 522.01, "uuid": "PS00002B920000000003F4B647"}
```

**Usage:**
```bash
python scraper.py
```
Press **Ctrl+C** to stop gracefully.

## Live Price Snapshot (`capture_live_price.py`)

One-shot capture for GitHub Actions hourly cron. Connects to WebSocket, grabs **1 price tick**, saves, and exits.

**How it works:**
1. Fetches the landing page and extracts the embedded JWT token
2. Connects to WebSocket, waits for first message (max 30s timeout)
3. Saves to `latest.json` (overwrite) + `data/YYYY-MM-DD/gold_YYYYMMDD_HHmmss.json`

**Output format (latest.json):**
```json
{"timestamp": "2026-07-17T09:00:00+00:00", "buy_price": 538.75, "sell_price": 522.01, "uuid": "PS00002B920000000003F4B647"}
```

**Usage:**
```bash
python capture_live_price.py
```

## Historical Price Scraper (`historical.py`)

Fetches daily historical gold price data from the site's backend API.

**How it works:**
1. Loads the landing page to get a session cookie
2. Primes the data cache via `controllers/pricehistory-landing.php`
3. Fetches records from `custom-data-request.php` (type=8)
4. Saves as formatted JSON and CSV

**Usage:**
```bash
python historical.py                    # all ranges (1w, 1m, 3m)
python historical.py --range 3m         # specific range only
python historical.py --output-dir data  # custom output directory
```

**CLI options:**

| Flag | Default | Description |
|---|---|---|
| `--range` | `all` | `1w`, `1m`, `3m`, or `all` |
| `--output-dir` | `.` | Directory for output files |

## Data Fields Reference

| Field | Description | Source |
|---|---|---|
| `companysell` | **Customer Buy Price** (RM/g) — what you pay to buy gold | WebSocket + History |
| `companybuy` | **Customer Sell Price** (RM/g) — what you receive when selling | WebSocket only |
| `uuid` | Unique price tick identifier | WebSocket only |
| `date` | Calendar date (YYYY-MM-DD format) | History only |
| `timestamp` | UTC timestamp of price tick | WebSocket only |

**Important note:** The API field `companysell` is the company's selling price, mapped to the customer's **buy** price. `companybuy` is the company's buying price, mapped to the customer's **sell** price.

## Historical Data Summary

The historical data is **daily granularity** — one record per calendar date.

| Preset | API ID | Records | Date Span | Price Range (RM/g) |
|---|---|---|---|---|
| 1-week (`1w`) | 1 | ~30 | Jun 17 – Jul 16 | 540.32 – 585.95 |
| 1-month (`1m`) | 2 | ~30 | Jun 17 – Jul 16 | 540.32 – 585.95 |
| 3-months (`3m`) | 3 | ~79 | Apr 17 – Jul 16 | 540.32 – 633.54 |

## Public Data — Scope

Only these metrics are available without authentication:

| Data | Type | Available |
|---|---|---|
| Buy Price (RM/g) | Real-time | Yes (WebSocket) |
| Sell Price (RM/g) | Real-time | Yes (WebSocket) |
| Historical Buy Price | Daily (up to ~3 months) | Yes (History API) |
| Quantity / Volume | — | Not available |
| Margin / Spread | — | Can be calculated from live data |
| Portfolio / Balances | — | Auth required |
| Transaction History | — | Auth required |

## Technical Notes

- **SSL**: Certificate verification is disabled (`verify=False`) — the site uses a non-standard certificate chain
- **JWT Token**: Embedded in the landing page HTML (`var js_variable = '...'`); expires ~24 hours, auto-refreshed every 6 hours
- **Market Hours**: 8:30 AM – 11:59 PM (Malaysia time, UTC+8). Outside these hours the WebSocket may not send data
- **GitHub Actions**: Hourly cron via `.github/workflows/scrape_gold.yml` — runs `capture_live_price.py`, commits `latest.json` + dated files, sends Teams alert
- **Dependencies**: `requests`, `websockets` (install with `pip install requests websockets`)
