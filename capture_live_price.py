#!/usr/bin/env python3
"""
POS ArRahnu Gold-i Live Price Snapshot
One-shot WebSocket capture with retry logic and error classification.
  Exit 0 = success
  Exit 2 = server/network error (retriable)
  Exit 1 = script/parsing error (likely bug)
"""

import asyncio
import json
import logging
import os
import re
import ssl
import sys
import time
from datetime import datetime, timezone

import requests
import urllib3
import websockets

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAGE_URL = "https://posarrahnugold.ace2u.com/index-landing.php"
WS_BASE = "wss://posarrahnugoldprodapi.ace2u.com/mygtp.php?version=1.0my&action=pricestream"
MERCHANT_ID = "POSARRAHNU@PROD"
OUTPUT_FILE = "latest.json"
DATA_DIR = "data"
TIMEOUT_SEC = 30
MAX_RETRIES = 3
RETRY_DELAYS = [3, 5, 10]

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gold_capture")


def fetch_jwt(session: requests.Session) -> str:
    resp = session.get(PAGE_URL, timeout=20)
    resp.raise_for_status()
    match = re.search(r"var\s+js_variable\s*=\s*'([^']+)'", resp.text)
    if not match:
        raise RuntimeError("JWT pattern not found in page source")
    return match.group(1)


async def capture_one_tick(token: str) -> dict:
    ws_url = f"{WS_BASE}&merchant_id={MERCHANT_ID}&access_token={token}"

    log.info("Connecting to WebSocket...")
    async with websockets.connect(ws_url, ssl=ssl_ctx, ping_interval=10, ping_timeout=5, close_timeout=5) as ws:
        log.info("Connected. Waiting for first price tick...")
        message = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_SEC)
        data = json.loads(message)
        records = data.get("data", [])
        if not records:
            raise RuntimeError("No price data in WebSocket message")
        record = records[0]
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": timestamp,
            "buy_price": round(float(record.get("companysell", 0)), 2),
            "sell_price": round(float(record.get("companybuy", 0)), 2),
            "uuid": record.get("uuid", ""),
        }
        log.info("Captured: Buy RM %.2f/g | Sell RM %.2f/g", entry["buy_price"], entry["sell_price"])
        return entry


def save_latest(entry: dict):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)


def save_dated(entry: dict):
    now = datetime.now()
    date_dir = os.path.join(DATA_DIR, now.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    filename = f"gold_{now.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(date_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)


async def main():
    log.info("=" * 40)
    log.info("Gold Price Snapshot Capture")
    log.info("=" * 40)

    session = requests.Session()
    session.verify = False

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                delay = RETRY_DELAYS[min(attempt - 2, len(RETRY_DELAYS) - 1)]
                log.info("Retry %d/%d in %ds...", attempt, MAX_RETRIES, delay)
                await asyncio.sleep(delay)

            token = fetch_jwt(session)
            entry = await capture_one_tick(token)
            save_latest(entry)
            save_dated(entry)
            log.info("Capture complete.")
            return

        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ReadTimeout) as exc:
            last_err = f"SERVER DOWN: {exc}"
            log.error("Attempt %d/%d failed (server): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                log.error(last_err)
                sys.exit(2)

        except (json.JSONDecodeError, KeyError, ValueError, RuntimeError, TypeError) as exc:
            log.error("SCRIPT ERROR: %s", exc)
            sys.exit(1)

        except websockets.exceptions.WebSocketException as exc:
            last_err = f"SERVER DOWN (WebSocket): {exc}"
            log.error("Attempt %d/%d failed (WebSocket): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                log.error(last_err)
                sys.exit(2)

        except asyncio.TimeoutError:
            last_err = "SERVER DOWN: WebSocket timed out"
            log.error("Attempt %d/%d failed (timeout)", attempt, MAX_RETRIES)
            if attempt == MAX_RETRIES:
                log.error(last_err)
                sys.exit(2)

        except Exception as exc:
            log.error("SCRIPT ERROR (unexpected): %s", exc)
            sys.exit(1)

    log.error(last_err or "Unknown error after all retries")
    sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
