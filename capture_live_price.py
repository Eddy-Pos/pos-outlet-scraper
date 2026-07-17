#!/usr/bin/env python3
"""
POS ArRahnu Gold-i Live Price Snapshot
One-shot WebSocket capture: connects, grabs 1 price tick, saves, exits.
Designed for GitHub Actions hourly cron.
"""

import asyncio
import json
import logging
import os
import re
import ssl
import sys
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gold_capture")


def fetch_jwt() -> str:
    resp = requests.get(PAGE_URL, timeout=15, verify=False)
    resp.raise_for_status()
    match = re.search(r"var\s+js_variable\s*=\s*'([^']+)'", resp.text)
    if not match:
        raise RuntimeError("Could not find JWT token in page source")
    return match.group(1)


async def capture_one_tick(token: str) -> dict:
    ws_url = f"{WS_BASE}&merchant_id={MERCHANT_ID}&access_token={token}"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

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
    log.info("Saved to %s", os.path.abspath(OUTPUT_FILE))


def save_dated(entry: dict):
    now = datetime.now()
    date_dir = os.path.join(DATA_DIR, now.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    filename = f"gold_{now.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(date_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)
    log.info("Saved to %s", os.path.abspath(filepath))


async def main():
    log.info("=" * 40)
    log.info("Gold Price Snapshot Capture")
    log.info("=" * 40)

    try:
        token = fetch_jwt()
        entry = await capture_one_tick(token)
        save_latest(entry)
        save_dated(entry)
        log.info("Capture complete.")
    except Exception as exc:
        log.error("Capture failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
