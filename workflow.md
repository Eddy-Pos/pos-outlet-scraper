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

### Local Development
- Run `python scrape_pos_outlets.py` manually to test
- `git pull` to sync latest data files from GitHub
