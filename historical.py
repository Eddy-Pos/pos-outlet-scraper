#!/usr/bin/env python3
"""
POS ArRahnu Gold-i Historical Price Scraper
Fetches daily gold price data and saves as JSON + CSV.
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAGE_URL = "https://posarrahnugold.ace2u.com/index-landing.php"
PRIME_URL = "https://posarrahnugold.ace2u.com/controllers/pricehistory-landing.php"
DATA_URL = "https://posarrahnugold.ace2u.com/custom-data-request.php"
MAX_RETRIES = 3
RETRY_DELAY = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("historical")

RANGES = {
    "1w": {"label": "1-week", "id": 1, "prime": (1, 7)},
    "1m": {"label": "1-month", "id": 2, "prime": (1, 0)},
    "3m": {"label": "3-months", "id": 3, "prime": (3, 0)},
}


def fetch_historical(range_key: str) -> list[dict]:
    cfg = RANGES[range_key]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                log.info("Retry %d/%d in %ds...", attempt, MAX_RETRIES, RETRY_DELAY)
                time.sleep(RETRY_DELAY)

            session = requests.Session()
            session.verify = False

            log.info("Loading landing page for session cookie...")
            resp = session.get(PAGE_URL, timeout=15)
            resp.raise_for_status()

            month, day = cfg["prime"]
            log.info("Priming data (month=%s, day=%s)...", month, day)
            resp = session.post(PRIME_URL, data={"month": month, "day": day}, timeout=15)
            resp.raise_for_status()

            log.info("Fetching %s historical data...", cfg["label"])
            resp = session.post(DATA_URL, data={"type": 8, "id": cfg["id"]}, timeout=15)
            resp.raise_for_status()

            resp_data = resp.json()
            raw = resp_data.get("data")
            if not raw:
                log.warning("No data returned from API")
                return []

            if not isinstance(raw, str):
                log.error("API returned unexpected data type: %s", type(raw).__name__)
                continue

            records = json.loads(raw)
            return records

        except (requests.ConnectionError, requests.Timeout) as exc:
            log.error("Attempt %d/%d failed (server): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                log.error("Server unreachable after %d attempts", MAX_RETRIES)
                return []

        except (json.JSONDecodeError, ValueError) as exc:
            log.error("Attempt %d/%d failed (parse): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                return []

        except Exception as exc:
            log.error("Unexpected error: %s", exc)
            if attempt == MAX_RETRIES:
                return []

    return []


def save_json(records: list[dict], filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    log.info("Saved %d records to %s", len(records), filepath)


def save_csv(records: list[dict], filepath: str):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "price"])
        for r in records:
            writer.writerow([r["date"], r["companysell"]])
    log.info("Saved %d records to %s", len(records), filepath)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch daily gold price history from POS ArRahnu Gold-i"
    )
    parser.add_argument(
        "--range",
        choices=list(RANGES.keys()) + ["all"],
        default="all",
        help="Time range: 1w (1-week), 1m (1-month), 3m (3-months), or all (default)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save output files (default: current directory)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    ranges_to_fetch = list(RANGES.keys()) if args.range == "all" else [args.range]

    for rk in ranges_to_fetch:
        cfg = RANGES[rk]
        log.info("=" * 40)
        log.info("Fetching %s...", cfg["label"])

        records = fetch_historical(rk)

        if not records:
            log.warning("Skipping %s — no data", cfg["label"])
            continue

        log.info(
            "Got %d records: %s to %s",
            len(records),
            records[0]["date"],
            records[-1]["date"],
        )

        base = os.path.join(args.output_dir, f"historical_{rk}")
        save_json(records, f"{base}.json")
        save_csv(records, f"{base}.csv")

    log.info("Done.")


if __name__ == "__main__":
    main()
