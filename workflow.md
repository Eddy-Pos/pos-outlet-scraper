# POS Outlet Scraper — Workflow

## Architecture

```
Google Apps Script (every 5 min)
        │
        │ POST /repos/.../dispatches (workflow_dispatch)
        ▼
GitHub Actions (runs scrape.yml)
        │
        │ python scrape_pos_outlets.py
        ▼
Fetches POS API → https://www-api.pos.com.my/api/outlets
        │
        ├─ Saves data/YYYY-MM-DD/outlets_YYYYMMDD_HHmmss.json
        ├─ Updates latest.json
        ├─ Auto-cleans files older than 2 days
        │
        ▼
Commits & pushes to GitHub repo
```

## Trigger

| Source | Schedule | Status |
|--------|----------|--------|
| Google Apps Script | Every 5 minutes | ✅ Primary |

## Components

### 1. Google Apps Script
- Hosted at `script.google.com`
- Calls GitHub API `workflow_dispatch` every 5 minutes
- Token stored in **Script Properties** (not in code)
- Run history visible under **Executions** tab

### 2. GitHub Actions (`.github/workflows/scrape.yml`)
- Triggered by `workflow_dispatch` from Apps Script
- Runs `scrape_pos_outlets.py`
- Commits new data to the repo

### 3. Scraper (`scrape_pos_outlets.py`)
- Fetches 20 pages concurrently (100 items/page = 1,968 outlets)
- Saves JSON with timestamp in filename
- Updates `latest.json` with latest snapshot
- Deletes files older than 2 days

## Output Structure

```
data/
└── YYYY-MM-DD/
    ├── outlets_YYYYMMDD_HHmmss.json
    └── outlets_YYYYMMDD_HHmmss.json
latest.json
```

## Setup

### Google Apps Script
1. Go to https://script.google.com
2. Create new project, paste code from `google_apps_script.gs`
3. Add **Script Property**: `GITHUB_TOKEN` = your token
4. Add time-driven trigger: every 5 minutes

## Data Storage

- **Cloud (source of truth):** GitHub repo → `data/YYYY-MM-DD/`
- **Local:** You run `git pull` to download the latest files to your laptop

No data is stored on your machine until you explicitly pull it.

## Syncing to Local

To download the latest data files:

```bash
git pull
```

### Optional: Auto-sync every 5 minutes (Windows Task Scheduler)

If you keep your laptop on during the day, set a lightweight task that just pulls:

```
Task: git pull
Repeat: Every 5 minutes
Action: C:\Program Files\Git\bin\git.exe pull
Args: -C "C:\path\to\your\repo"
```

This runs only `git pull` (no Python, no scraping) — very lightweight.

### Local Development
- Run `python scrape_pos_outlets.py` manually to test
- `git pull` to sync latest data files from GitHub
