import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://www-api.pos.com.my/api/outlets"
PAGE_SIZE = 100
TIMEOUT = 30
MAX_DAYS = 2

LOG_FILE = os.path.join(BASE_DIR, "scraper.log")
LATEST_FILE = os.path.join(BASE_DIR, "latest.json")
DATA_DIR = os.path.join(BASE_DIR, "data")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def fetch_page(page: int) -> list[dict]:
    url = f"{API_URL}?pagination[pageSize]={PAGE_SIZE}&pagination[page]={page}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            logger.info(f"Page {page}: fetched {len(items)} outlets")
            outlets = []
            for item in items:
                attrs = item.get("attributes", {})
                outlets.append({
                    "id": item.get("id"),
                    "outlet_name": attrs.get("outlet_name", ""),
                    "address": attrs.get("address", ""),
                    "postalcode": attrs.get("postalcode", ""),
                    "phoneNo1": attrs.get("phoneNo1", ""),
                    "phoneNo2": attrs.get("phoneNo2", ""),
                    "phoneNo3": attrs.get("phoneNo3", ""),
                    "url": attrs.get("url", ""),
                    "latitude": attrs.get("latitude"),
                    "longitude": attrs.get("longitude"),
                    "state": attrs.get("state", ""),
                    "operating_hours": attrs.get("operating_hours", ""),
                    "status": attrs.get("status", ""),
                    "special_arrangement": attrs.get("special_arrangement", ""),
                })
            return outlets
    except URLError as e:
        logger.error(f"Page {page}: network error - {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Page {page}: JSON decode error - {e}")
    except Exception as e:
        logger.error(f"Page {page}: unexpected error - {e}")
    return []


def get_total_pages() -> int:
    url = f"{API_URL}?pagination[pageSize]={PAGE_SIZE}&pagination[page]=1"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total = data.get("meta", {}).get("pagination", {}).get("pageCount", 0)
            logger.info(f"Total pages: {total}")
            return total
    except Exception as e:
        logger.error(f"Failed to get total pages: {e}")
        return 0


def main():
    logger.info("=== Scraper started ===")

    total_pages = get_total_pages()
    if total_pages == 0:
        logger.error("No pages to fetch. Exiting.")
        sys.exit(1)

    all_outlets = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_page, page): page for page in range(1, total_pages + 1)}
        for future in as_completed(futures):
            page_outlets = future.result()
            all_outlets.extend(page_outlets)

    all_outlets.sort(key=lambda x: x["id"] or 0)
    logger.info(f"Total outlets fetched: {len(all_outlets)}")

    if not all_outlets:
        logger.warning("No data fetched. Skipping file saves.")
        sys.exit(1)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    ts_str = now.strftime("%Y%m%d_%H%M%S")

    date_dir = os.path.join(DATA_DIR, date_str)
    os.makedirs(date_dir, exist_ok=True)

    out_file = os.path.join(date_dir, f"outlets_{ts_str}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_outlets, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved: {out_file}")

    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        json.dump(all_outlets, f, ensure_ascii=False, indent=2)
    logger.info(f"Updated: {LATEST_FILE}")

    cutoff = now.timestamp() - MAX_DAYS * 86400
    cleaned = 0
    if os.path.isdir(DATA_DIR):
        for root, dirs, files in os.walk(DATA_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    cleaned += 1
            if not os.listdir(root) and root != DATA_DIR:
                os.rmdir(root)
    if cleaned:
        logger.info(f"Cleaned {cleaned} old file(s)")

    logger.info(f"=== Scraper completed ({len(all_outlets)} outlets) ===")


if __name__ == "__main__":
    main()
