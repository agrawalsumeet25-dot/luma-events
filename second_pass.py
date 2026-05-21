"""
second_pass.py — Merge agent-discovered slugs into the latest crawl.

Takes the latest luma_raw_recursive_*.json + all slugs from extra_seeds.py,
resolves new slugs to calendar_api_ids, crawls events for any calendars not
already in the dataset, Bay-Area-filters them, enriches, and writes a merged
JSON with everything combined. Then regenerates the viewer.

Run AFTER the main crawler completes. Idempotent — running again only finds
deltas.
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(line_buffering=True)

# Re-use everything from the main crawler
sys.path.insert(0, str(Path(__file__).parent))
from scrape_luma_recursive import (  # noqa: E402
    BAY_AREA_PLACE_ID, OUT_DIR, HEADERS,
    in_bay_area, crawl_calendar_events, fetch_event_detail,
    resolve_slug_to_calendar_id,
)
from extra_seeds import (  # noqa: E402
    SF_PAGE_CAL_IDS,
    GITHUB_DISCOVERED_SLUGS,
    AGENT1_DISCOVERED_SLUGS,
    AGENT2_DISCOVERED_SLUGS,
    AGENT3_DISCOVERED_SLUGS,
)

PARALLEL_SLUG = 20
PARALLEL_CAL = 16
PARALLEL_DETAIL = 20


def latest_recursive_dump() -> Path:
    dumps = sorted(OUT_DIR.glob("luma_raw_recursive_*.json"))
    if not dumps:
        raise SystemExit("No recursive dump found. Run scrape_luma_recursive.py first.")
    return dumps[-1]


def main() -> int:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    src = latest_recursive_dump()
    print(f"[1/5] Loading base: {src.name}")
    base = json.loads(src.read_text(encoding="utf-8"))
    existing_events: dict[str, dict] = {r["api_id"]: r for r in base["events"]}
    existing_cals: set[str] = set()
    for r in base["events"]:
        det = r.get("detail") or {}
        cal_id = (det.get("calendar") or {}).get("api_id") or (
            r.get("list_entry", {}).get("event", {}) or {}
        ).get("calendar_api_id")
        if cal_id:
            existing_cals.add(cal_id)
    print(f"  base: {len(existing_events)} events, {len(existing_cals)} unique host cals")

    all_slugs = sorted(set(
        GITHUB_DISCOVERED_SLUGS
        + AGENT1_DISCOVERED_SLUGS
        + AGENT2_DISCOVERED_SLUGS
        + AGENT3_DISCOVERED_SLUGS
    ))
    print(f"\n[2/5] Resolving {len(all_slugs)} agent slugs in parallel "
          f"({PARALLEL_SLUG} workers)")

    def resolve(slug: str) -> tuple[str, str | None]:
        try:
            return slug, resolve_slug_to_calendar_id(requests.Session(), slug)
        except Exception:
            return slug, None

    resolved: dict[str, str] = {}    # cal_api_id -> slug
    with ThreadPoolExecutor(max_workers=PARALLEL_SLUG) as ex:
        for slug, cid in ex.map(resolve, all_slugs):
            if cid and cid not in existing_cals and cid not in resolved:
                resolved[cid] = slug
    print(f"  resolved: {len(resolved)} NEW calendar api_ids (not in base)")

    # Also include the direct SF page cal_ids if not yet known
    for cid in SF_PAGE_CAL_IDS:
        if cid not in existing_cals and cid not in resolved:
            resolved[cid] = f"sf-page:{cid}"
    print(f"  + SF page cal_ids: total NEW cals = {len(resolved)}")

    if not resolved:
        print("  No new calendars to crawl. Exiting.")
        return 0

    # ── Crawl each new calendar ──────────────────────────────────────────────
    print(f"\n[3/5] Crawling {len(resolved)} new calendars in parallel "
          f"({PARALLEL_CAL} workers)")

    def crawl(item: tuple[str, str]) -> tuple[str, list[dict]]:
        cid, label = item
        return cid, crawl_calendar_events(requests.Session(), cid, label)

    new_events: dict[str, dict] = {}
    items = list(resolved.items())
    with ThreadPoolExecutor(max_workers=PARALLEL_CAL) as ex:
        for cid, ents in ex.map(crawl, items):
            kept = 0
            for entry in ents:
                ev = entry.get("event") or {}
                aid = ev.get("api_id")
                if not aid or aid in existing_events or aid in new_events:
                    continue
                if not in_bay_area(ev):
                    continue
                new_events[aid] = entry
                kept += 1
            if kept:
                print(f"    +{kept} from {resolved[cid][:35]}", flush=True)

    print(f"\n  net new bay events: {len(new_events)}")

    if not new_events:
        print("  No new events found. Exiting.")
        return 0

    # ── Enrich new events ────────────────────────────────────────────────────
    print(f"\n[4/5] Enriching {len(new_events)} new events in parallel "
          f"({PARALLEL_DETAIL} workers)")

    def enrich(item: tuple[str, dict]) -> dict:
        aid, entry = item
        det = fetch_event_detail(requests.Session(), aid)
        return {"api_id": aid, "list_entry": entry, "detail": det}

    new_records: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=PARALLEL_DETAIL) as ex:
        for rec in ex.map(enrich, list(new_events.items())):
            new_records.append(rec)
            done += 1
            if done % 25 == 0 or done == len(new_events):
                print(f"  detail {done}/{len(new_events)}", flush=True)

    # ── Merge and write ──────────────────────────────────────────────────────
    print(f"\n[5/5] Merging and writing")
    merged_records = list(existing_events.values()) + new_records
    out_path = OUT_DIR / f"luma_raw_recursive_{ts}_merged.json"
    out_path.write_text(json.dumps({
        "fetched_at": ts,
        "place_api_id": BAY_AREA_PLACE_ID,
        "merged_from": src.name,
        "count": len(merged_records),
        "events": merged_records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"DONE")
    print(f"  base events:        {len(existing_events)}")
    print(f"  new events added:   {len(new_records)}")
    print(f"  total events:       {len(merged_records)}")
    print(f"  output:             {out_path}")
    print(f"  size:               {out_path.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
