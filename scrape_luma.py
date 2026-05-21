"""
scrape_luma.py — Phase 1 of the Luma events pipeline.

Pulls every event Luma's public Discover surface returns for the SF Bay Area,
then enriches each with the per-event detail endpoint (full description,
location, hosts, calendar, tickets, capacity, RSVP info, etc.).

Writes the raw JSON to output/luma_raw_<timestamp>.json so we can inspect what
fields Luma actually exposes before designing filters / scoring / auto-RSVP.

No auth required. Public endpoints only.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(line_buffering=True)

# ── Constants ──────────────────────────────────────────────────────────────────
LIST_URL = "https://api.lu.ma/discover/get-paginated-events"
EVENT_URL = "https://api.lu.ma/event/get"

# SF Bay Area discover-place (covers SF + East Bay + parts of Peninsula).
# This is the ONLY Bay Area discover surface Luma exposes — South Bay
# (Mountain View, San Jose) is not its own discover-place.
BAY_AREA_PLACE_ID = "discplace-BDj7GNbGlsF7Cka"

PAGE_SIZE = 100
DETAIL_DELAY_SEC = 0.2          # ~5 requests/sec on the detail endpoint
RETRY_BACKOFF_SEC = 5
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── HTTP helpers ───────────────────────────────────────────────────────────────
def get_json(session: requests.Session, url: str, params: dict | None = None) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = RETRY_BACKOFF_SEC * (attempt + 1)
                print(f"  rate-limited, sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            print(f"  retry {attempt+1}/{MAX_RETRIES}: {exc}", flush=True)
            time.sleep(RETRY_BACKOFF_SEC)
    return {}


# ── Discover list (paginated) ──────────────────────────────────────────────────
def fetch_all_list_entries(session: requests.Session) -> list[dict]:
    """Walk all pages of the discover endpoint for the Bay Area place."""
    entries: list[dict] = []
    cursor: str | None = None
    page = 0
    while True:
        page += 1
        params: dict = {
            "period": "upcoming",
            "pagination_limit": PAGE_SIZE,
            "discover_place_api_id": BAY_AREA_PLACE_ID,
        }
        if cursor:
            params["pagination_cursor"] = cursor

        data = get_json(session, LIST_URL, params)
        page_entries = data.get("entries", [])
        entries.extend(page_entries)
        print(
            f"  page {page}: +{len(page_entries)} events  "
            f"(total {len(entries)}, has_more={data.get('has_more')})",
            flush=True,
        )

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.3)
    return entries


# ── Per-event detail ───────────────────────────────────────────────────────────
def fetch_event_detail(session: requests.Session, api_id: str) -> dict | None:
    try:
        data = get_json(session, EVENT_URL, {"event_api_id": api_id})
        if isinstance(data, dict) and data.get("message"):
            return None
        return data
    except requests.RequestException as exc:
        print(f"  detail fetch failed for {api_id}: {exc}", flush=True)
        return None


def enrich_entries(session: requests.Session, entries: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    total = len(entries)
    for i, entry in enumerate(entries, 1):
        api_id = entry.get("api_id") or entry.get("event", {}).get("api_id")
        if not api_id:
            enriched.append({"list_entry": entry, "detail": None, "error": "no_api_id"})
            continue

        detail = fetch_event_detail(session, api_id)
        enriched.append({
            "api_id": api_id,
            "list_entry": entry,
            "detail": detail,
        })
        if i % 10 == 0 or i == total:
            print(f"  detail {i}/{total}", flush=True)
        time.sleep(DETAIL_DELAY_SEC)
    return enriched


# ── Summary ────────────────────────────────────────────────────────────────────
def print_summary(records: list[dict]) -> None:
    print("\n" + "=" * 70)
    print(f"FETCHED {len(records)} events")
    print("=" * 70)

    detail_ok = sum(1 for r in records if r.get("detail"))
    print(f"  detail endpoint succeeded: {detail_ok}/{len(records)}")

    cities: dict[str, int] = {}
    descriptions = 0
    venues = 0
    online = 0
    paid = 0
    approval_req = 0
    earliest = latest = None

    for r in records:
        ev = r.get("list_entry", {}).get("event", {}) or {}
        det = r.get("detail") or {}

        geo = ev.get("geo_address_info") or {}
        if ev.get("location_type") == "online":
            online += 1
            city = "ONLINE"
        else:
            city = geo.get("city") or "?"
        cities[city] = cities.get(city, 0) + 1

        if geo.get("full_address"):
            venues += 1
        if det.get("description_mirror") or det.get("description") or ev.get("description"):
            descriptions += 1

        if ev.get("registration_questions") or ev.get("require_approval") or det.get("require_approval"):
            approval_req += 1
        ti = r.get("list_entry", {}).get("ticket_info") or det.get("ticket_info") or {}
        if ti and (ti.get("price_cents") or 0) > 0:
            paid += 1

        start = ev.get("start_at")
        if start:
            if not earliest or start < earliest:
                earliest = start
            if not latest or start > latest:
                latest = start

    print(f"  with venue address: {venues}/{len(records)}")
    print(f"  with description:   {descriptions}/{len(records)}")
    print(f"  online-only events: {online}")
    print(f"  approval required:  {approval_req}")
    print(f"  paid events:        {paid}")
    print(f"  date range:         {earliest}  ->  {latest}")

    print("\nBy city:")
    for city, n in sorted(cities.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4}  {city}")

    print("\nSample titles:")
    for r in records[:8]:
        ev = r.get("list_entry", {}).get("event", {}) or {}
        name = ev.get("name", "?")
        city = (ev.get("geo_address_info") or {}).get("city") or ev.get("location_type", "?")
        start = ev.get("start_at", "?")[:16]
        print(f"  - {start}  {name[:60]:60}  ({city})")


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> int:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = OUT_DIR / f"luma_raw_{ts}.json"

    print(f"[1/3] Fetching Discover list for SF Bay Area "
          f"(place={BAY_AREA_PLACE_ID})", flush=True)
    session = requests.Session()
    entries = fetch_all_list_entries(session)
    if not entries:
        print("  no events returned, aborting")
        return 1

    print(f"\n[2/3] Enriching {len(entries)} events with per-event detail", flush=True)
    records = enrich_entries(session, entries)

    print(f"\n[3/3] Writing {out_path}", flush=True)
    out_path.write_text(
        json.dumps({
            "fetched_at": ts,
            "place_api_id": BAY_AREA_PLACE_ID,
            "count": len(records),
            "events": records,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print_summary(records)
    print(f"\nWrote -> {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
