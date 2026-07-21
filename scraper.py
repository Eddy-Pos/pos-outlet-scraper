#!/usr/bin/env python3
"""
POS ArRahnu Gold-i Live Gold Price Scraper
Connects to WebSocket stream, captures buy/sell prices,
appends each tick as JSON Lines to prices.jsonl
"""

import asyncio
import json
import logging
import os
import re
import signal
import ssl
import sys
import time
from datetime import datetime, timezone

import requests
import urllib3
import websockets
from websockets.exceptions import ConnectionClosed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAGE_URL = "https://posarrahnugold.ace2u.com/index-landing.php"
WS_BASE = "wss://posarrahnugoldprodapi.ace2u.com/mygtp.php?version=1.0my&action=pricestream"
MERCHANT_ID = "POSARRAHNU@PROD"
TOKEN_REFRESH_INTERVAL = 21_600
OUTPUT_FILE = "prices.jsonl"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

running = True
total_ticks = 0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gold_scraper")


def signal_handler(signum, frame):
    global running
    if running:
        log.info("Shutdown signal received. Stopping scraper...")
        running = False


def fetch_jwt(session: requests.Session) -> str:
    log.info("Fetching landing page for JWT token...")
    resp = session.get(PAGE_URL, timeout=30)
    resp.raise_for_status()
    match = re.search(r"var\s+js_variable\s*=\s*'([^']+)'", resp.text)
    if not match:
        raise RuntimeError("Could not find JWT token in page source")
    token = match.group(1)
    log.info("JWT token extracted successfully (%d chars)", len(token))
    return token


def build_ws_url(token: str) -> str:
    return f"{WS_BASE}&merchant_id={MERCHANT_ID}&access_token={token}"


async def connect_and_scrape(token: str, fh):
    global total_ticks
    ws_url = build_ws_url(token)
    log.info("Connecting to WebSocket...")

    async with websockets.connect(ws_url, ssl=ssl_ctx, ping_interval=30, ping_timeout=10) as ws:
        log.info("WebSocket connected. Waiting for price data...")
        async for message in ws:
            if not running:
                break

            try:
                data = json.loads(message)
                records = data.get("data", [])
                for record in records:
                    timestamp = datetime.now(timezone.utc).isoformat()
                    entry = {
                        "timestamp": timestamp,
                        "buy_price": round(float(record.get("companysell", 0)), 2),
                        "sell_price": round(float(record.get("companybuy", 0)), 2),
                        "uuid": record.get("uuid", ""),
                    }
                    total_ticks += 1
                    line = json.dumps(entry)
                    fh.write(line + "\n")
                    fh.flush()

                    log.info(
                        "[#%d] Buy: RM %.2f/g | Sell: RM %.2f/g",
                        total_ticks,
                        entry["buy_price"],
                        entry["sell_price"],
                    )
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                log.warning("Failed to parse message: %s | raw: %s", exc, message[:200])


async def main():
    global running

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log.info("=" * 50)
    log.info("POS ArRahnu Gold-i Price Scraper")
    log.info("Output: %s", os.path.abspath(OUTPUT_FILE))
    log.info("Press Ctrl+C to stop")
    log.info("=" * 50)

    session = requests.Session()
    session.verify = False

    last_token_fetch = 0.0
    token = None

    with open(OUTPUT_FILE, "a", encoding="utf-8") as fh:
        while running:
            try:
                now = time.monotonic()
                if token is None or (now - last_token_fetch) >= TOKEN_REFRESH_INTERVAL:
                    token = fetch_jwt(session)
                    last_token_fetch = now

                await connect_and_scrape(token, fh)

            except ConnectionClosed as exc:
                log.warning("WebSocket disconnected (code=%s). Reconnecting in 3s...", exc.code)
                await asyncio.sleep(3)

            except requests.RequestException as exc:
                log.error("HTTP request failed: %s. Retrying in 10s...", exc)
                await asyncio.sleep(10)

            except Exception as exc:
                log.error("Unexpected error: %s. Retrying in 10s...", exc)
                await asyncio.sleep(10)

    log.info("Scraper stopped. Total ticks captured: %d", total_ticks)


if __name__ == "__main__":
    asyncio.run(main())
