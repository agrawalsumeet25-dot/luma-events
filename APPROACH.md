# Luma Events — Full Auto-Scraping Pipeline (Approach)

This doc captures the architecture and roadmap for a fully-automated Luma event
pipeline: discover every relevant event, enrich, filter, score, RSVP, surface
in a dashboard, and email a daily digest. Built incrementally so each phase
ships value on its own.

Maintain this file as the source of truth. If you ship a new phase or change
the strategy, update it.

---

## Discovered Luma API Surface (no auth required)

| Endpoint | Purpose | Key params |
|---|---|---|
| `GET https://api.lu.ma/discover/get-paginated-events` | List events for a place ± category | `discover_place_api_id`, `discover_category_api_id`, `period=upcoming`, `pagination_limit`, `pagination_cursor` |
| `GET https://api.lu.ma/discover/get-calendars` | List calendars for a place ± category | same place/category params, `pagination_limit` |
| `GET https://api.lu.ma/calendar/get-items` | List events on a specific calendar | `calendar_api_id`, `period=future`, `pagination_limit`, `pagination_cursor` |
| `GET https://api.lu.ma/event/get` | Full event detail (description, hosts, capacity, tickets, RSVP requirements) | `event_api_id` |
| `GET https://lu.ma/<slug>` (HTML) | Parse `__NEXT_DATA__` to identify kind (`discover-place` / `category` / `calendar` / `event`) and harvest `featured_calendars`, `timeline_calendars`, `featured_items` | none |

### Known identifiers

- **Bay Area discover-place:** `discplace-BDj7GNbGlsF7Cka` (slug `sf`, but covers SF, East Bay, parts of Peninsula — South Bay coverage requires bbox filter)
- **Categories (7 confirmed):**
  - `cat-ai` (AI) – 3,130 upcoming events globally
  - `cat-tech` (Tech) – 3,959
  - `cat-crypto` (Crypto) – 816
  - `cat-climate` (Climate) – 673
  - `cat-fooddrink` (Food & Drink)
  - `cat-C1VaNLnt25w9t6c` (Wellness) – 1,128
  - `cat-0Km9ZnuBjFAjwFl` (Fitness) – 1,452

### Bay Area bounding box (lat/lng)

```
south = 37.0   (Gilroy)
north = 38.5   (Vallejo)
west  = -123.0 (coast)
east  = -121.5 (Livermore)
```

Used to filter out non-Bay-Area events that leak in from globally-tagged
calendars (e.g. "The AI Collective" hosts events in Prague, Atlanta, etc.).

### Discovery sources Luma does NOT expose publicly

- No `/search` API for events or calendars (returns 404)
- No sitemap.xml (returns HTML 200 instead of XML)
- No master `list-categories` or `list-places` endpoint
- New categories / places must be probed manually or discovered via crawled data

### Quirks observed in production

- **Category filter is mostly cosmetic on the discover endpoint.** When you
  combine `discover_place_api_id` with `discover_category_api_id`, the response
  is roughly the same as place-only (Luma surfaces ~66 events for SF either
  way). Real diversity comes from the **recursive calendar crawl** in Phase C,
  not from slicing by category. Don't over-invest in category fan-out.

- **Luma has no native "Design" / "UX" / "UI" category.** Use a keyword-derived
  tag on the client side (see `build_viewer.py`'s `derived_tags` logic) to
  group design events.

- **South Bay coverage is thin** in the SF discover-place. Mountain View, San
  Jose, Cupertino, Sunnyvale events only show up via the recursive calendar
  crawl, not via `discover_place_api_id=SF` alone.

---

## Pipeline Phases

### Phase 1 — Discovery (DONE)
**File:** `scrape_luma.py` (single discover-place crawler — kept as the simple baseline)

Pulls all events from the SF Bay Area discover-place + per-event detail enrichment. Output:
`output/luma_raw_<timestamp>.json`. ~66 events.

### Phase 2 — Recursive Discovery (DONE)
**File:** `scrape_luma_recursive.py`

Exhaustive multi-source crawl that turns every stone Luma exposes. Strategy:

```
A. category × place
   for each Luma category: paginate /discover/get-paginated-events
   filtered to the SF Bay Area place. Record events + their host calendars.

B. seed calendar harvest
   B1. fetch each category page (lu.ma/<slug>), parse __NEXT_DATA__,
       harvest featured_calendars + timeline_calendars
   B2. /discover/get-calendars for SF (overall + per-category)
   B3. hand-picked Bay Area AI/tech communities

C. recursive calendar crawl (BFS)
   for each calendar in queue:
     fetch all upcoming events via /calendar/get-items
     keep those inside the Bay Area bbox
     enqueue every unseen host calendar
   continues until queue empty or MAX_CALENDARS hit

D. per-event detail enrichment
   /event/get for every unique event api_id

E. write same JSON shape as Phase 1 so the viewer keeps working
```

Same output format as Phase 1 → `build_viewer.py` works on either.

### Phase 3 — Viewer (DONE)
**File:** `build_viewer.py`

Generates `output/viewer.html`: a self-contained, dark-theme, client-side
search/sort/filter viewer over the latest scrape. No server, no deps. Card
grid + modal expand. Reads the most recent `luma_raw_*.json`.

### Phase 4 — Relevance Scoring (TODO)
**File:** `score_events.py`

For each enriched event, compute a relevance score (0–10) based on:
- **Keyword density** in title + description (AI, agents, LLM, MCP, Claude, GPU, robotics, etc.)
- **Host calendar reputation** (curated allow-list of high-signal communities)
- **Featured guest signal** (known speakers / orgs)
- **Capacity vs. RSVP ratio** (under-promoted high-signal events score higher)
- **Time-of-day fit** (weekday evenings > random afternoon)
- **Distance from user's location** (Mountain View, since user works at Microsoft MV)
- **Calendar category vs. user interests**

Output augments each event with `score`, `score_breakdown`, `recommended` boolean.
Reused by viewer, digest, and RSVP gate.

### Phase 5 — Auto-RSVP (TODO)
**File:** `rsvp_events.py`

For each event matching auto-RSVP criteria:
- score ≥ threshold (default 7)
- `registration_availability == "open"`
- `is_paid == false`
- `sold_out == false`
- no calendar conflict (Google Calendar check)
- max N RSVPs per week (configurable, default 5)

RSVP via the official Luma API (requires `LUMA_API_KEY` env var — user provides
when ready). For approval-required or paid events, queue for manual review in
the digest email.

Browser-automation fallback (Playwright on a dedicated CDP port — allocate from
the **9240-9249** block, never collide with existing tasks per CLAUDE.md
port-ownership rules) for any flow the API can't handle.

Track RSVP history in `state/rsvp_history.jsonl` to avoid duplicates and
to detect no-show patterns.

### Phase 6 — Calendar Sync (TODO)
**File:** `sync_to_gcal.py`

For each RSVP'd event:
- Push to user's Google Calendar (already-authed via existing gmail credentials)
- Include venue address, RSVP URL, host info in the calendar event body
- Set reminder 30 min before

Bidirectional consistency: if event cancelled on Luma, remove from gcal.

### Phase 7 — Daily Email Digest (TODO)
**File:** `email_digest.py`

Generate and send a daily HTML email:
- Top section: "Auto-RSVP'd today" (3-5 events with confirmation)
- Middle: "Recommended this week (manual RSVP)" — gated/paid/approval-needed
- Bottom: "Also fetched" — full list with relevance scores

Send via `linkedin_apply/email_report.send_email()` (already configured with
Gmail API + OAuth refresh token). Recipient: agrawal.sumeet25@gmail.com.

### Phase 8 — Supervisor Integration (TODO)
**File:** `task_registry.json` entry + Task Scheduler

Register as `luma_events_daily`:
```json
{
  "name": "Luma Events — Daily Discover + RSVP + Digest",
  "script": "C:/Users/suagraw/luma-events/run_daily.py",
  "working_dir": "C:/Users/suagraw/luma-events",
  "python": "C:/Users/suagraw/Ayushi/browser-agent/.venv/Scripts/python.exe",
  "report_dir": "output",
  "report_pattern": "digest_*.html",
  "validator": "base",
  "expected_runtime_minutes": 20,
  "email_to": "agrawal.sumeet25@gmail.com",
  "schedule": "daily 7:45 AM",
  "rules": {
    "min_events_fetched": 30,
    "min_recommended": 1
  },
  "source_files": [
    "scrape_luma_recursive.py",
    "score_events.py",
    "rsvp_events.py",
    "sync_to_gcal.py",
    "email_digest.py",
    "build_viewer.py",
    "run_daily.py"
  ]
}
```

Wrapped via `supervisor/run.py` per the mandatory protocol.

Schedule: 7:45 AM daily (before the existing 8:03 / 8:15 / 8:20 briefings).

### Phase 9 — Streamlit Dashboard (optional, TODO)
**File:** `app.py`

For interactive exploration (similar to `apartment_hunting/app.py`). Filters by
score/date/host, marks events to RSVP manually, edits keyword weights live.
`streamlit run app.py`. Not part of the daily auto-run.

---

## Roadmap

| Phase | Status | Notes |
|---|---|---|
| 1. Single-source discover | DONE | `scrape_luma.py` — 66 events |
| 2. Recursive multi-source | DONE | `scrape_luma_recursive.py` — expected ~500-2000 events |
| 3. Static HTML viewer | DONE | `build_viewer.py` — `output/viewer.html` |
| 4. Relevance scoring | TODO | Needs keyword list + calendar reputation list from user |
| 5. Auto-RSVP | TODO | Blocked on user providing `LUMA_API_KEY` |
| 6. Google Calendar sync | TODO | Reuses existing gmail OAuth creds |
| 7. Daily email digest | TODO | Reuses `linkedin_apply/email_report.send_email()` |
| 8. Supervisor + scheduler | TODO | Follow CLAUDE.md supervisor protocol exactly |
| 9. Streamlit dashboard | OPTIONAL | Not in auto-pipeline |

---

## Key Operating Decisions

1. **Read-side aggression OK, write-side caution.** We crawl exhaustively on
   the read side (no Luma write happens). For writes (RSVPs), enforce a weekly
   cap and skip approval-required events by default — otherwise the user gets
   blacklisted as a no-show.

2. **Bay Area filter via bbox, not city name.** City names miss events whose
   `geo_address_info.city` is unset or weird; lat/lng is reliable.

3. **One JSON shape for all phases.** Both scrapers output the same record
   structure (`{api_id, list_entry, detail}`) so the viewer and downstream
   scorer / RSVP gate are scraper-agnostic.

4. **Polite rate limiting.** ~5 req/sec on detail, 3 req/sec on list.
   Exponential backoff on 429. No parallelism; single-threaded BFS.

5. **Port ownership.** When Playwright fallback is added (Phase 5), allocate
   ports `9240-9249` per CLAUDE.md. Never use `taskkill /IM msedge.exe` —
   only `kill_edge_on_ports([9240, ...])`.

6. **Supervisor mandatory.** Once Phase 8 lands, the daily task must run via
   `supervisor/run.py`. No direct Task Scheduler → script invocation.

---

## Files

```
C:\Users\suagraw\luma-events\
├── APPROACH.md                       # This file
├── scrape_luma.py                    # Phase 1
├── scrape_luma_recursive.py          # Phase 2
├── build_viewer.py                   # Phase 3
├── score_events.py                   # Phase 4 (TODO)
├── rsvp_events.py                    # Phase 5 (TODO)
├── sync_to_gcal.py                   # Phase 6 (TODO)
├── email_digest.py                   # Phase 7 (TODO)
├── run_daily.py                      # Phase 8 entry point (TODO)
├── app.py                            # Phase 9 (optional, TODO)
└── output/
    ├── luma_raw_<ts>.json
    ├── luma_raw_recursive_<ts>.json
    ├── viewer.html
    └── digest_<date>.html (future)
```
