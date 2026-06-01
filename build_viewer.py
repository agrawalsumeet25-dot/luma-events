"""
build_viewer.py — Generate the Luma Events viewer.

Reads the latest scored/raw JSON dump and produces output/viewer.html —
a self-contained, mobile-first event discovery app with:
- Discover mode (time-grouped grid with hero spotlight)
- Swipe mode (Tinder-style card stack with drag physics)
- Score rings, keyboard nav, confetti, 3D tilt, command palette
"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

OUT_DIR = Path(__file__).parent / "output"


def prosemirror_to_html(node: dict) -> str:
    if not isinstance(node, dict):
        return ""
    ntype = node.get("type")
    content = node.get("content") or []
    attrs = node.get("attrs") or {}
    if ntype == "text":
        text = html.escape(node.get("text") or "")
        for mark in node.get("marks") or []:
            mtype = mark.get("type")
            mattrs = mark.get("attrs") or {}
            if mtype == "bold":
                text = f"<strong>{text}</strong>"
            elif mtype == "italic":
                text = f"<em>{text}</em>"
            elif mtype == "link":
                href = html.escape(mattrs.get("href") or "")
                text = f'<a href="{href}" target="_blank" rel="noopener">{text}</a>'
            elif mtype == "code":
                text = f"<code>{text}</code>"
        return text
    children = "".join(prosemirror_to_html(c) for c in content)
    if ntype == "doc": return children
    if ntype == "paragraph": return f"<p>{children}</p>" if children else ""
    if ntype == "heading":
        level = max(1, min(6, attrs.get("level") or 2))
        return f"<h{level}>{children}</h{level}>"
    if ntype == "hard_break": return "<br/>"
    if ntype == "bullet_list": return f"<ul>{children}</ul>"
    if ntype == "ordered_list": return f"<ol>{children}</ol>"
    if ntype == "list_item": return f"<li>{children}</li>"
    if ntype == "horizontal_rule": return "<hr/>"
    if ntype == "blockquote": return f"<blockquote>{children}</blockquote>"
    if ntype == "image":
        src = html.escape(attrs.get("src") or "")
        return f'<img src="{src}" alt="" loading="lazy"/>'
    if ntype == "code_block": return f"<pre><code>{children}</code></pre>"
    return children


def latest_dump() -> Path:
    for pattern in ["luma_scored_*.json", "luma_raw_recursive_*_merged.json",
                    "luma_raw_recursive_*.json", "luma_raw_*.json"]:
        dumps = sorted(OUT_DIR.glob(pattern))
        if dumps:
            return dumps[-1]
    raise SystemExit("No event data found.")


def slim(records: list[dict]) -> list[dict]:
    out: list[dict] = []
    now_utc = datetime.now(timezone.utc)
    dropped = 0
    for r in records:
        ev = (r.get("list_entry") or {}).get("event") or {}
        det = r.get("detail") or {}
        det_ev = det.get("event") or {}

        # Drop past events: use end_at if available, else start_at + 3h buffer
        end_str = ev.get("end_at") or det_ev.get("end_at")
        start_str = ev.get("start_at") or det_ev.get("start_at")
        try:
            if end_str:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end_dt < now_utc:
                    dropped += 1
                    continue
            elif start_str:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_dt + timedelta(hours=3) < now_utc:
                    dropped += 1
                    continue
        except (ValueError, TypeError):
            pass

        cal = det.get("calendar") or {}
        geo = ev.get("geo_address_info") or det_ev.get("geo_address_info") or {}
        ti = det.get("ticket_info") or {}
        hosts = det.get("hosts") or []
        cats = [c.get("name") for c in (det.get("categories") or []) if c.get("name")]
        guests = det.get("featured_guests") or []
        url_slug = ev.get("url") or det_ev.get("url") or ""
        rsvp_url = f"https://lu.ma/{url_slug}" if url_slug else ""
        text_blob = " ".join([ev.get("name") or "", det_ev.get("name") or "",
                              cal.get("name") or "",
                              (det.get("event") or {}).get("description") or ""]).lower()
        derived_tags: list[str] = []
        if any(t in text_blob for t in ["design", "ux ", "ui ", "ux/", "ui/", "/ux", "/ui",
            "figma", "framer", "prototype", "wireframe", "design system", "product designer",
            "user experience", "user interface", "interaction design"]):
            derived_tags.append("Design")
        if any(t in text_blob for t in [" ai ", "a.i.", "agent", "llm", "ml ", "machine learning",
            "claude", "openai", "anthropic", "gpt", "gemini", "neural", "transformer", "rag ", "vector db"]):
            derived_tags.append("AI (keyword)")
        out.append({
            "id": ev.get("api_id"),
            "name": ev.get("name") or det_ev.get("name"),
            "start_at": ev.get("start_at") or det_ev.get("start_at"),
            "end_at": ev.get("end_at") or det_ev.get("end_at"),
            "timezone": ev.get("timezone") or det_ev.get("timezone"),
            "location_type": ev.get("location_type") or det_ev.get("location_type"),
            "city": geo.get("city") or "",
            "venue": geo.get("address") or "",
            "full_address": geo.get("full_address") or "",
            "cover_url": ev.get("cover_url") or "",
            "tint": det.get("tint_color") or "#7c3aed",
            "calendar_name": cal.get("name") or "",
            "calendar_avatar": cal.get("avatar_url") or "",
            "hosts": [{"name": h.get("name"), "avatar": h.get("avatar_url")} for h in hosts],
            "guest_count": det.get("guest_count", 0) or 0,
            "categories": cats + derived_tags,
            "description_html": prosemirror_to_html(det.get("description_mirror") or {}),
            "registration_availability": det.get("registration_availability"),
            "sold_out": det.get("sold_out", False),
            "waitlist_active": det.get("waitlist_active", False),
            "featured_guests": [{"name": g.get("name"), "avatar": g.get("avatar_url")}
                                for g in guests][:8],
            "url": rsvp_url,
            "scores": r.get("scores") or {},
            "prep": r.get("prep") or {},
        })
    if dropped:
        print(f"  dropped {dropped} past events", flush=True)
    return out



# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
:root{
  --bg:#111110;--surface:rgba(24,24,22,.88);--s2:rgba(32,32,28,.72);
  --border:rgba(148,163,184,.06);--bh:rgba(148,163,184,.14);
  --text:#ede9e3;--t2:#9c9590;--t3:#706a65;--t4:#6b7280;
  --accent:#2db87a;--ah:#4fd1a0;--abg:rgba(45,184,122,.08);
  --score:#d97706;--sbg:rgba(217,119,6,.08);--sglow:rgba(217,119,6,.18);
  --pos:#2db87a;--info:#3b9ece;--danger:#d1453b;
  --rs:6px;--rl:14px;
  --eo:cubic-bezier(0.23,1,0.32,1);
  --fd:'Outfit',system-ui,sans-serif;
  --fb:'Sora',-apple-system,BlinkMacSystemFont,sans-serif;
  --fi:'Newsreader',Georgia,serif;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{color-scheme:dark;scroll-behavior:smooth}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
body{font-family:var(--fb);background:var(--bg);color:var(--t2);line-height:1.55;min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden;font-size:15px}
.wrap{max-width:1280px;margin:0 auto;padding:32px 40px}
@media(max-width:768px){.wrap{padding:20px 16px}}

header{margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--border)}
.header-row{display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:16px}
h1{font-family:var(--fi);font-size:44px;font-weight:400;font-style:normal;letter-spacing:-.02em;color:var(--text);line-height:1.05}
@media(max-width:640px){h1{font-size:32px}}
.sub{color:var(--t4);font-size:12px;font-weight:400;letter-spacing:.04em}
.summary{font-size:15px;color:var(--t2);margin:16px 0 0;line-height:1.5}
.summary strong{color:var(--text);font-weight:600}
.mode-toggle{display:flex;gap:2px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rs);padding:4px}
.mode-btn{padding:10px 16px;font-size:12px;font-weight:500;color:var(--t3);background:transparent;border:none;border-radius:4px;cursor:pointer;transition:color .2s var(--eo),background .2s var(--eo);font-family:var(--fb)}
.mode-btn.active{background:var(--s2);color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.3)}
.mode-btn:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.mode-btn:hover:not(.active){color:var(--t2)}}

.toolbar{display:flex;gap:12px;align-items:center;margin:0 0 8px;flex-wrap:wrap}
.toolbar input,.toolbar select{background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:var(--rs);padding:10px 16px;font-size:13px;font-family:var(--fb);outline:none;transition:border-color .2s var(--eo)}
.toolbar input:focus,.toolbar select:focus{border-color:var(--accent)}
.toolbar input[type=search]{flex:1;min-width:200px}
.toolbar input::placeholder{color:var(--t4)}
.toolbar label{font-size:11px;color:var(--t4);font-weight:500;text-transform:uppercase;letter-spacing:.06em}
.toolbar select{cursor:pointer}
.filter-toggle{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:var(--rs);padding:10px 16px;font-size:13px;font-weight:500;cursor:pointer;font-family:var(--fb);transition:border-color .2s var(--eo),color .2s var(--eo)}
.filter-toggle:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.filter-toggle:hover{color:var(--text);border-color:var(--bh)}}
.filter-toggle.has-active{color:var(--accent);border-color:rgba(45,184,122,.3)}
.filter-count{background:var(--accent);color:var(--bg);border-radius:999px;padding:1px 7px;font-size:10px;font-weight:700;margin-left:6px;display:none}
.filter-count.show{display:inline}
.filter-drawer{display:none;padding:16px 0 20px;border-bottom:1px solid var(--border);margin:0 0 24px}
.filter-drawer.open{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.chips{display:flex;flex-wrap:wrap;gap:6px;width:100%}
.chip{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:999px;padding:10px 16px;font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:color .2s var(--eo),border-color .2s var(--eo),background .2s var(--eo)}
.chip:active{transform:scale(.96)}
@media(hover:hover)and(pointer:fine){.chip:hover{color:var(--text);border-color:var(--bh)}}
.chip.active{background:var(--text);color:var(--bg);border-color:var(--text)}
.person-chips{display:flex;gap:8px;align-items:center}
.person-chips .label{font-size:10px;color:var(--t4);text-transform:uppercase;letter-spacing:.12em;font-weight:600}
.person-chip{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:999px;padding:10px 20px;font-size:12px;font-weight:600;cursor:pointer;user-select:none;transition:color .2s var(--eo),border-color .2s var(--eo),background .2s var(--eo)}
.person-chip:active{transform:scale(.96)}
@media(hover:hover)and(pointer:fine){.person-chip:hover{color:var(--text);border-color:var(--bh)}}
.person-chip.active{background:var(--accent);color:#fff;border-color:transparent}
.date-range{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.date-range label{font-size:11px;color:var(--t4);font-weight:500}
.date-range input[type=date]{background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;font-size:12px;font-family:var(--fb);outline:none;cursor:pointer;color-scheme:dark}
.date-range input[type=date]:focus{border-color:var(--accent)}
.date-quick{display:flex;gap:4px}
.date-quick button{background:transparent;color:var(--t3);border:1px solid var(--border);border-radius:var(--rs);padding:10px 14px;font-size:12px;font-weight:500;cursor:pointer;transition:color .2s var(--eo),border-color .2s var(--eo),background .2s var(--eo);font-family:var(--fb)}
.date-quick button:active{transform:scale(.96)}
@media(hover:hover)and(pointer:fine){.date-quick button:hover{color:var(--text);border-color:var(--bh)}}
.date-quick button.active{background:var(--text);color:var(--bg);border-color:var(--text)}
.score-slider{display:none;align-items:center;gap:12px;width:100%;padding:4px 0}
.score-slider.show{display:flex}
.score-slider label{font-size:11px;color:var(--score);font-weight:600;white-space:nowrap;letter-spacing:.02em}
.score-slider input[type=range]{flex:1;height:4px;-webkit-appearance:none;appearance:none;background:rgba(71,85,105,.2);border-radius:2px;outline:none;cursor:pointer}
.score-slider input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;border-radius:50%;background:var(--score);cursor:pointer;box-shadow:0 2px 8px var(--sglow)}
.score-slider input[type=range]::-moz-range-thumb{width:24px;height:24px;border-radius:50%;background:var(--score);cursor:pointer;border:none}
.score-slider .val{font-family:var(--fd);font-size:15px;font-weight:700;color:var(--score);min-width:28px;text-align:right}
.count{margin:0 0 16px;color:var(--t4);font-size:12px;font-weight:400}

.card.going{border-color:rgba(45,184,122,.25)}
.card.going .going-badge{display:flex}
.going-badge{display:none;position:absolute;top:14px;left:60px;z-index:2;background:var(--pos);color:#fff;font-size:10px;font-weight:700;padding:4px 12px;border-radius:999px;text-transform:uppercase;letter-spacing:.08em}
.going-btn{background:transparent;color:var(--pos);border:1px solid rgba(45,184,122,.25);padding:10px 20px;border-radius:var(--rs);font-size:13px;font-weight:500;cursor:pointer;transition:border-color .2s var(--eo),background .2s var(--eo);font-family:var(--fb);display:inline-flex;align-items:center;gap:6px}
.going-btn:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.going-btn:hover{border-color:var(--pos);background:rgba(45,184,122,.08)}}
.going-btn.active{background:var(--pos);color:#fff;border-color:transparent}
.cal-btn{background:transparent;color:var(--info);border:1px solid rgba(59,158,206,.25);padding:10px 20px;border-radius:var(--rs);font-size:13px;font-weight:500;cursor:pointer;transition:border-color .2s var(--eo),background .2s var(--eo);text-decoration:none;font-family:var(--fb);display:inline-flex;align-items:center;gap:6px}
.cal-btn:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.cal-btn:hover{border-color:var(--info);background:rgba(59,158,206,.08)}}
.my-events{margin:0 0 24px;padding:20px 24px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rl);display:none}
.my-events.show{display:block}
.my-events h3{font-family:var(--fd);font-size:13px;font-weight:600;color:var(--pos);text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px}
.my-events-list{display:flex;flex-wrap:wrap;gap:8px}
.my-event-chip{background:transparent;color:var(--pos);border:1px solid rgba(45,184,122,.2);border-radius:var(--rs);padding:8px 14px;font-size:12px;font-weight:500;cursor:pointer;transition:border-color .2s var(--eo);display:flex;align-items:center;gap:8px}
.my-event-chip:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.my-event-chip:hover{border-color:var(--pos)}}
.my-event-chip .remove{color:var(--t4);font-size:14px;cursor:pointer}
@media(hover:hover)and(pointer:fine){.my-event-chip .remove:hover{color:var(--danger)}}

.hero{display:none;margin:0 0 48px;border-radius:var(--rl);overflow:hidden;position:relative;min-height:400px;background-size:cover;background-position:center;cursor:pointer}
.hero.show{display:block}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(17,17,16,.95) 0%,rgba(17,17,16,.4) 50%,transparent 100%);display:flex;align-items:flex-end;padding:48px}
@media(max-width:640px){.hero-overlay{padding:24px}.hero{min-height:280px}}
.hero-content{display:flex;align-items:flex-end;gap:32px;width:100%}
.hero-text{flex:1}
.hero-label{font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.15em;font-weight:600;margin-bottom:12px}
.hero-title{font-family:var(--fi);font-size:32px;font-weight:400;font-style:normal;color:#fff;line-height:1.1;margin-bottom:14px}
@media(max-width:640px){.hero-title{font-size:24px}}
.hero-meta{font-size:13px;color:var(--t2)}
.hero-ring{flex-shrink:0}

.ring-wrap{position:relative;display:inline-flex;align-items:center;justify-content:center}
.ring-val{position:absolute;font-family:var(--fd);font-weight:800;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.5)}
.ring-sm .ring-val{font-size:13px}
.ring-lg .ring-val{font-size:20px}

.section-header{font-family:var(--fi);font-size:24px;font-weight:400;color:var(--t2);margin:48px 0 20px;letter-spacing:-.01em;font-style:normal;line-height:1.15}
.section{opacity:0;transform:translateY(16px);transition:opacity .5s var(--eo),transform .5s var(--eo);content-visibility:auto;contain-intrinsic-size:auto 600px}
.section.visible{opacity:1;transform:translateY(0)}
.section .grid .card{opacity:0;transform:translateY(10px);transition:opacity .4s var(--eo),transform .4s var(--eo)}
.section.visible .grid .card{opacity:1;transform:translateY(0);will-change:auto}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
@media(max-width:768px){.grid{grid-template-columns:1fr;gap:12px}}
.grid .card:first-child{grid-column:1/-1;height:400px}
.grid .card:first-child .title{font-size:24px;font-family:var(--fi)}
.grid .card:nth-child(2),.grid .card:nth-child(3){height:340px}
.grid .card:nth-child(n+4){height:280px}

.section[data-period="today"] .grid{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px;-webkit-overflow-scrolling:touch}
.section[data-period="today"] .grid .card{flex:0 0 380px;scroll-snap-align:start;height:400px}
.section[data-period="today"] .grid .card:first-child{flex:0 0 520px;grid-column:auto}
@media(max-width:768px){.section[data-period="today"] .grid .card,.section[data-period="today"] .grid .card:first-child{flex:0 0 85vw;height:360px}}

.section[data-period="tomorrow"] .grid{grid-template-columns:1.4fr 1fr;grid-template-rows:auto auto}
.section[data-period="tomorrow"] .grid .card:first-child{grid-row:1/3;height:auto;min-height:380px}
@media(max-width:768px){.section[data-period="tomorrow"] .grid{grid-template-columns:1fr}.section[data-period="tomorrow"] .grid .card:first-child{grid-row:auto;height:340px}}

.section[data-period="month"] .grid,.section[data-period="later"] .grid{grid-template-columns:1fr;gap:8px}
.section[data-period="month"] .grid .card,.section[data-period="later"] .grid .card{height:auto;min-height:80px;flex-direction:row;border-radius:var(--rs)}
.section[data-period="month"] .grid .card .cover,.section[data-period="later"] .grid .card .cover{position:relative;width:140px;min-width:140px;height:auto;border-radius:var(--rs) 0 0 var(--rs)}
.section[data-period="month"] .grid .card .body,.section[data-period="later"] .grid .card .body{position:relative;background:none;padding:16px}
.section[data-period="month"] .grid .card .title,.section[data-period="later"] .grid .card .title{font-size:15px;text-shadow:none}
.section[data-period="month"] .grid .card:first-child,.section[data-period="later"] .grid .card:first-child{grid-column:1;height:auto;min-height:80px}
.section[data-period="month"] .grid .card:first-child .title,.section[data-period="later"] .grid .card:first-child .title{font-size:15px;font-family:var(--fd)}
.section[data-period="month"] .grid .card .going-badge,.section[data-period="later"] .grid .card .going-badge{top:8px;left:8px}

.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--rl);overflow:hidden;cursor:pointer;display:flex;flex-direction:column;position:relative;height:380px;transition:border-color .3s var(--eo),box-shadow .3s var(--eo);contain:layout style}
.card:active{transform:scale(.99)}
@media(hover:hover)and(pointer:fine){.card:hover{border-color:var(--bh);box-shadow:0 8px 32px rgba(0,0,0,.15)}}
.cover{position:absolute;inset:0;background-color:var(--surface);overflow:hidden}
.cover .ring-wrap{position:absolute;top:14px;left:14px;z-index:3;background:rgba(0,0,0,.85);border-radius:50%;padding:5px;box-shadow:0 2px 10px rgba(0,0,0,.6),0 0 0 2px rgba(255,255,255,.1)}
.badges{position:absolute;top:14px;right:14px;display:flex;gap:6px;z-index:2}
.badge{background:rgba(17,17,16,.75);color:var(--text);font-size:10px;font-weight:600;padding:4px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.06em}
.badge.sold{background:rgba(209,69,59,.8)}.badge.waitlist{background:rgba(234,88,12,.8)}.badge.open{background:rgba(45,184,122,.7)}
.body{position:absolute;bottom:0;left:0;right:0;padding:24px;display:flex;flex-direction:column;gap:6px;background:linear-gradient(to top,rgba(17,17,16,.88),transparent);z-index:1}
.title{font-family:var(--fd);font-size:18px;font-weight:700;color:#fff;line-height:1.25;text-shadow:0 1px 3px rgba(0,0,0,.3)}
.meta{display:flex;flex-direction:column;gap:3px;font-size:12px;color:rgba(255,255,255,.6)}
.meta .row{display:flex;align-items:center;gap:6px}
.icon{width:14px;height:14px;opacity:.35;flex-shrink:0}
.host{display:none}
.cats{display:none}
.rsvp-strip{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-top:2px}
.rsvp-count{color:rgba(255,255,255,.5);font-weight:500}
.rsvp-count span{color:rgba(255,255,255,.35);font-weight:400}

.swipe-container{display:none;flex-direction:column;align-items:center;padding:40px 0;min-height:70vh}
.swipe-container.show{display:flex}
.swipe-stack{position:relative;width:360px;height:520px;max-width:90vw}
@media(max-width:400px){.swipe-stack{width:300px;height:460px}}
.swipe-card{position:absolute;inset:0;border-radius:var(--rl);overflow:hidden;background:var(--bg);border:1px solid var(--border);cursor:grab;touch-action:none;user-select:none;will-change:transform}
.swipe-card:active{cursor:grabbing}
.swipe-card .s-cover{height:58%;background-size:cover;background-position:center;position:relative}
.swipe-card .s-body{padding:24px;display:flex;flex-direction:column;gap:10px;height:42%;overflow:hidden}
.swipe-card .s-title{font-family:var(--fd);font-size:24px;font-weight:700;color:var(--text);line-height:1.2}
.swipe-card .s-meta{font-size:13px;color:var(--t2);display:flex;flex-direction:column;gap:4px}
.swipe-card .s-host{font-size:12px;color:var(--t4);margin-top:auto}
.swipe-flash{position:absolute;top:24px;border-radius:var(--rs);padding:8px 20px;font-family:var(--fd);font-size:24px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;opacity:0;transition:opacity .15s var(--eo);pointer-events:none;z-index:10}
.swipe-flash.like{right:24px;color:var(--pos);border:3px solid var(--pos);transform:rotate(12deg)}
.swipe-flash.nope{left:24px;color:var(--danger);border:3px solid var(--danger);transform:rotate(-12deg)}
.swipe-actions{display:flex;gap:20px;margin-top:32px}
.swipe-btn{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:1px solid var(--border);background:transparent;cursor:pointer;font-size:22px;transition:border-color .2s var(--eo),color .2s var(--eo);color:var(--t3)}
.swipe-btn:active{transform:scale(.9)}
@media(hover:hover)and(pointer:fine){.swipe-btn:hover{border-color:var(--bh);color:var(--text)}}
.swipe-btn.skip{color:var(--danger)}
.swipe-btn.like-btn{color:var(--pos)}
.swipe-btn.undo-btn{color:var(--score);font-size:16px}
.swipe-counter{margin-top:20px;font-size:12px;color:var(--t4)}
.picks-bar{margin-top:28px;width:100%;max-width:420px}
.picks-label{font-size:11px;color:var(--t4);text-transform:uppercase;letter-spacing:.1em;font-weight:600;margin-bottom:10px}
.picks-list{display:flex;flex-wrap:wrap;gap:8px}
.pick-chip{background:transparent;color:var(--pos);border:1px solid rgba(45,184,122,.2);border-radius:var(--rs);padding:8px 12px;font-size:12px;font-weight:500;cursor:pointer;transition:border-color .2s var(--eo)}
.pick-chip:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.pick-chip:hover{border-color:var(--pos)}}

.modal-bg{display:none;position:fixed;inset:0;background:rgba(17,17,16,.95);z-index:100;align-items:flex-start;justify-content:center;padding:48px 24px;overflow-y:auto}
.modal-bg.open{display:flex}
@media(max-width:640px){.modal-bg{padding:0;align-items:flex-end}.modal-bg .modal-wrap{max-width:100%}.modal-bg .modal{border-radius:var(--rl) var(--rl) 0 0;max-height:92vh;overflow-y:auto}}
.modal-wrap{position:relative;width:100%;max-width:720px}
.modal{background:rgba(24,24,22,.98);border:1px solid var(--border);border-radius:var(--rl);width:100%;overflow:hidden;box-shadow:0 32px 96px rgba(0,0,0,.5)}
.modal .cover{position:relative;height:280px;background-size:cover;background-position:center;background-color:var(--surface)}
@media(max-width:640px){.modal .cover{height:200px}}
.modal-body{padding:32px}
@media(max-width:640px){.modal-body{padding:20px}}
.modal h2{font-family:var(--fi);font-size:24px;font-weight:400;font-style:normal;color:var(--text);line-height:1.15;margin-bottom:16px}
.modal .meta{font-size:13px;color:var(--t2);margin-bottom:20px}
.modal-scores{display:flex;gap:16px;margin:20px 0;padding:20px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rl)}
.modal-score-item{flex:1;text-align:center}
.modal-score-item .name{font-size:10px;color:var(--t4);text-transform:uppercase;letter-spacing:.12em;font-weight:600;margin-bottom:8px}
.modal-score-item .why{font-size:12px;color:var(--t3);margin-top:8px;line-height:1.5}
.modal .desc{color:var(--t2);font-size:15px;line-height:1.55;margin:24px 0;max-height:400px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(71,85,105,.3) transparent}
.modal .desc p{margin-bottom:12px}.modal .desc a{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
@media(hover:hover)and(pointer:fine){.modal .desc a:hover{color:var(--ah)}}
.modal .desc img{max-width:100%;border-radius:var(--rs);margin:12px 0}.modal .desc h2,.modal .desc h3{font-family:var(--fd);color:var(--text);margin:20px 0 8px}
.modal .desc ul,.modal .desc ol{padding-left:20px;margin-bottom:12px}.modal .desc li{margin-bottom:4px}.modal .desc hr{border:none;border-top:1px solid var(--border);margin:20px 0}
.modal .actions{display:flex;gap:12px;margin-top:24px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;background:var(--text);color:var(--bg);padding:12px 24px;border-radius:var(--rs);text-decoration:none;font-size:13px;font-weight:600;border:none;cursor:pointer;transition:opacity .15s var(--eo);font-family:var(--fb)}
.btn:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.btn:hover{opacity:.85}}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--t2)}
.btn.ghost:active{transform:scale(.97)}
@media(hover:hover)and(pointer:fine){.btn.ghost:hover{border-color:var(--bh);color:var(--text)}}
.guests{display:flex;margin:12px 0}.guests img{width:30px;height:30px;border-radius:50%;border:2px solid var(--bg);margin-left:-8px;object-fit:cover}.guests img:first-child{margin-left:0}
.close{position:absolute;top:12px;right:12px;background:rgba(17,17,16,.5);color:var(--text);width:44px;height:44px;border-radius:50%;border:1px solid rgba(255,255,255,.06);cursor:pointer;font-size:18px;z-index:2;display:flex;align-items:center;justify-content:center;transition:background .15s var(--eo)}
.close:active{transform:scale(.9)}
@media(hover:hover)and(pointer:fine){.close:hover{background:rgba(209,69,59,.5)}}

.prep-section{margin:24px 0;padding:24px;background:var(--surface);border:1px solid var(--border);border-radius:var(--rl)}
.prep-section h3{font-family:var(--fd);font-size:11px;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:.1em;margin-bottom:14px}
.prep-news{list-style:none;padding:0;margin:0 0 20px}
.prep-news li{font-size:13px;color:var(--t2);line-height:1.6;padding:8px 0 8px 18px;position:relative;border-bottom:1px solid var(--border)}
.prep-news li::before{content:'';position:absolute;left:0;top:14px;width:5px;height:5px;border-radius:50%;background:var(--accent)}
.prep-news li:last-child{border-bottom:none}
.prep-starters{list-style:none;padding:0;margin:0}
.prep-starters li{font-size:13px;color:var(--text);line-height:1.6;padding:12px 16px;margin-bottom:8px;background:var(--s2);border:1px solid var(--border);border-radius:var(--rs);transition:border-color .2s var(--eo)}
@media(hover:hover)and(pointer:fine){.prep-starters li:hover{border-color:var(--bh)}}

::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(71,85,105,.2);border-radius:3px}::-webkit-scrollbar-thumb:hover{background:rgba(71,85,105,.35)}
.cmd-bg{display:none;position:fixed;inset:0;background:rgba(17,17,16,.92);z-index:150;align-items:flex-start;justify-content:center;padding:18vh 24px 24px}
.cmd-bg.open{display:flex}
.cmd-box{width:100%;max-width:560px;background:rgba(24,24,22,.98);border:1px solid var(--border);border-radius:var(--rl);overflow:hidden;box-shadow:0 32px 96px rgba(0,0,0,.5)}
.cmd-input{width:100%;background:transparent;border:none;border-bottom:1px solid var(--border);padding:18px 24px;font-size:15px;color:var(--text);font-family:var(--fb);outline:none}
.cmd-input::placeholder{color:var(--t4)}
.cmd-results{max-height:360px;overflow-y:auto;padding:8px}
.cmd-item{display:flex;align-items:center;gap:14px;padding:12px 16px;border-radius:var(--rs);cursor:pointer;transition:background .15s var(--eo)}
.cmd-item:active{transform:scale(.99)}
@media(hover:hover)and(pointer:fine){.cmd-item:hover{background:var(--surface)}}
.cmd-item.active{background:var(--surface)}
.cmd-item .ci-title{font-size:15px;font-weight:500;color:var(--text)}
.cmd-item .ci-meta{font-size:12px;color:var(--t4)}
"""

# ── JS ────────────────────────────────────────────────────────────────────────
JS = r"""
const E=window.__EVENTS__,S=s=>document.querySelector(s),SA=s=>document.querySelectorAll(s);
let mode='discover',activePerson=null,picks=[],undoStack=[],scoreThreshold=0;
const cityF=new Set(),catF=new Set(),statusF=new Set();
const isMobile='ontouchstart'in window&&innerWidth<768;
let debounceTimer=null;
const debounce=(fn,ms)=>(...a)=>{clearTimeout(debounceTimer);debounceTimer=setTimeout(()=>fn(...a),ms)};

const PST=-8,PDT=-7,TZ_OFF=PDT;
function toPST(d){return new Date(d.getTime()+(d.getTimezoneOffset()+TZ_OFF*60)*60000)}
const fD=s=>{if(!s)return'?';const d=new Date(s);return d.toLocaleString('en-US',{timeZone:'America/Los_Angeles',weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})};
const relDay=s=>{if(!s)return'later';const d=toPST(new Date(s)),n=toPST(new Date());const ed=new Date(d.getFullYear(),d.getMonth(),d.getDate()),td=new Date(n.getFullYear(),n.getMonth(),n.getDate());const diff=Math.round((ed-td)/864e5);if(diff<0)return'past';if(diff===0)return'today';if(diff===1)return'tomorrow';if(diff<=7)return'week';if(diff<=30)return'month';return'later'};
const st=e=>e.sold_out?'sold':e.waitlist_active?'waitlist':'open';
const stL=s=>({sold:'Sold out',waitlist:'Waitlist',open:'Open'})[s];
const scC=n=>n>=80?'#2db87a':n>=50?'#d97706':'#3a3a38';
const gS=(e,p)=>((e.scores||{})[p]||{}).score||0;
const esc=s=>s==null?'':String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);

function ring(score,size){
  const r=size==='lg'?40:20,sw=size==='lg'?6:4,circ=2*Math.PI*r;
  const off=circ*(1-score/100),col=scC(score);
  return `<div class="ring-wrap ring-${size}"><svg width="${(r+sw)*2}" height="${(r+sw)*2}" style="transform:rotate(-90deg)"><circle cx="${r+sw}" cy="${r+sw}" r="${r}" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="${sw}"/><circle cx="${r+sw}" cy="${r+sw}" r="${r}" fill="none" stroke="${col}" stroke-width="${sw}" stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${off}" style="transition:stroke-dashoffset 1s var(--eo)"/></svg><span class="ring-val">${score}</span></div>`;
}
function iconCal(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'}
function iconPin(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>'}

function buildCard(e){
  const s=st(e),sc=activePerson?gS(e,activePerson):0;
  const covImg=e.cover_url?`<img src="${esc(e.cover_url)}" loading="lazy" decoding="async" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"/>`:'';
  const covBg=`style="background-color:${esc(e.tint)}"`;
  const hn=e.calendar_name||(e.hosts[0]||{}).name||'';
  const ringPh=activePerson?`<div class="ring-placeholder" data-score="${sc}" style="position:absolute;top:14px;left:14px;z-index:3;width:42px;height:42px"></div>`:'';
  const isGoing=goingSet.has(e.id);
  return `<div class="card${isGoing?' going':''}" data-id="${esc(e.id)}" tabindex="0"><div class="cover" ${covBg}>${covImg}${ringPh}<div class="badges"><span class="badge ${s}">${stL(s)}</span></div><div class="going-badge">Going</div></div><div class="body"><div class="title">${esc(e.name||'?')}</div><div class="meta"><div class="row">${iconCal()} ${esc(fD(e.start_at))}</div><div class="row">${iconPin()} ${esc(e.venue||e.city||'?')}${e.city&&e.venue?', '+esc(e.city):''}</div></div><div class="rsvp-strip"><span class="rsvp-count">${(e.guest_count||0).toLocaleString()} <span>RSVPs</span></span></div></div></div>`;
}

/* Summary */
function renderSummary(){
  const today=E.filter(e=>relDay(e.start_at)==='today').length;
  const tmrw=E.filter(e=>relDay(e.start_at)==='tomorrow').length;
  const el=S('#summary');
  if(!el)return;
  let txt=`<strong>${E.length} events</strong> in the Bay Area`;
  if(today)txt+=`. <strong>${today}</strong> happening today`;
  if(tmrw)txt+=`, <strong>${tmrw}</strong> tomorrow`;
  el.innerHTML=txt;
}

/* Hero */
function renderHero(){
  const h=S('#hero');
  if(!activePerson){h.classList.remove('show');return}
  const sorted=[...E].sort((a,b)=>gS(b,activePerson)-gS(a,activePerson));
  const e=sorted[0];if(!e||gS(e,activePerson)<40){h.classList.remove('show');return}
  const sc=gS(e,activePerson);
  h.style.backgroundImage=e.cover_url?`url('${e.cover_url}')`:'none';
  h.style.backgroundColor=e.tint;
  h.innerHTML=`<div class="hero-overlay"><div class="hero-content"><div class="hero-text"><div class="hero-label">Top pick for ${activePerson}</div><div class="hero-title">${esc(e.name)}</div><div class="hero-meta">${esc(fD(e.start_at))} · ${esc(e.city||'?')} · ${(e.guest_count||0).toLocaleString()} RSVPs</div></div><div class="hero-ring">${ring(sc,'lg')}</div></div></div>`;
  h.classList.add('show');
  h.onclick=()=>openModal(e.id);
}

/* Section observer */
const sectionObs=new IntersectionObserver(entries=>{
  entries.forEach(entry=>{
    if(entry.isIntersecting){
      // Hydrate section if it has deferred content
      const render=entry.target._deferredRender;
      if(render){entry.target.querySelector('.grid').innerHTML=render();delete entry.target._deferredRender}
      entry.target.classList.add('visible');
      const cards=entry.target.querySelectorAll('.card');
      cards.forEach((c,i)=>{c.style.transitionDelay=`${Math.min(i*50,400)}ms`});
      entry.target.querySelectorAll('.ring-placeholder').forEach(ph=>{
        const sc=parseInt(ph.dataset.score)||0;ph.innerHTML=ring(sc,'sm');ph.classList.remove('ring-placeholder');
      });
      // Click handlers attached via event delegation on #grid (see init)
      sectionObs.unobserve(entry.target);
    }
  });
},{rootMargin:'200px 0px',threshold:0.01});

/* Discover */
function filterAndRender(){
  let list=E.slice();
  const q=(S('#search').value||'').toLowerCase().trim();
  if(q)list=list.filter(e=>(e.name||'').toLowerCase().includes(q)||(e.calendar_name||'').toLowerCase().includes(q)||(e.city||'').toLowerCase().includes(q));
  if(cityF.size)list=list.filter(e=>cityF.has(e.city||'TBD'));
  if(catF.size)list=list.filter(e=>(e.categories||[]).some(c=>catF.has(c)));
  if(statusF.size)list=list.filter(e=>statusF.has(st(e)));
  const df=S('#dateFrom').value,dt=S('#dateTo').value;
  if(df){const from=new Date(df+'T00:00:00');list=list.filter(e=>{const d=new Date(e.start_at);return d>=from})}
  if(dt){const to=new Date(dt+'T23:59:59');list=list.filter(e=>{const d=new Date(e.start_at);return d<=to})}
  if(activePerson&&scoreThreshold>0)list=list.filter(e=>gS(e,activePerson)>=scoreThreshold);
  const sv=S('#sort').value;
  if(sv==='date')list.sort((a,b)=>(a.start_at||'').localeCompare(b.start_at||''));
  else if(sv==='rsvps')list.sort((a,b)=>(b.guest_count||0)-(a.guest_count||0));
  else if(sv==='name')list.sort((a,b)=>(a.name||'').localeCompare(b.name||''));
  else list.sort((a,b)=>gS(b,sv)-gS(a,sv));

  const grid=S('#grid');
  const groups={today:[],tomorrow:[],week:[],month:[],later:[]};
  list.forEach(e=>{const g=relDay(e.start_at);(groups[g]||groups.later).push(e)});
  const labels={today:'Happening Today',tomorrow:'Tomorrow',week:'This Week',month:'This Month',later:'Later'};
  const frag=document.createDocumentFragment();
  let sectionIdx=0;
  for(const[k,lbl]of Object.entries(labels)){
    const evts=groups[k];if(!evts||!evts.length)continue;
    const section=document.createElement('div');
    section.className='section';
    section.dataset.period=k;
    const headerHtml=`<div class="section-header">${lbl} <span style="color:var(--t4);font-weight:400;font-size:13px">(${evts.length})</span></div>`;
    if(sectionIdx<2){
      // Render first 2 sections immediately
      section.innerHTML=headerHtml+`<div class="grid">${evts.map(buildCard).join('')}</div>`;
    }else{
      // Defer remaining sections — render on scroll
      section.innerHTML=headerHtml+`<div class="grid"></div>`;
      section._deferredRender=()=>evts.map(buildCard).join('');
    }
    frag.appendChild(section);
    requestAnimationFrame(()=>sectionObs.observe(section));
    sectionIdx++;
  }
  grid.innerHTML='';
  grid.appendChild(frag);
  S('#count').textContent=`${list.length} of ${E.length} events`;
  renderHero();
}

/* Modal */
function scoresHtml(e){
  const sc=e.scores||{};const names=Object.keys(sc);if(!names.length)return'';
  return `<div class="modal-scores">${names.map(n=>{const s=sc[n]||{};const v=s.score||0;return `<div class="modal-score-item"><div class="name">${esc(n)}</div>${ring(v,'sm')}<div class="why">${esc(s.reason||'')}</div></div>`}).join('')}</div>`;
}
function prepHtml(e){
  const p=e.prep||{};const news=p.news||[];const st=p.starters||[];
  if(!news.length&&!st.length)return'';
  let h='';
  if(news.length)h+=`<div class="prep-section"><h3>Latest on this topic</h3><ul class="prep-news">${news.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></div>`;
  if(st.length)h+=`<div class="prep-section"><h3>Conversation starters</h3><ul class="prep-starters">${st.map(s=>`<li>${esc(s)}</li>`).join('')}</ul></div>`;
  return h;
}
function openModal(id){
  const e=E.find(x=>x.id===id);if(!e)return;
  const s=st(e);
  const modalCovBg=`style="background-color:${esc(e.tint)}"`;
  const modalCovImg=e.cover_url?`<img src="${esc(e.cover_url)}" decoding="async" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"/>`:'';
  const guests=(e.featured_guests||[]).map(g=>`<img src="${esc(g.avatar||'')}" title="${esc(g.name||'')}" alt=""/>`).join('');
  const desc=e.description_html||'<p style="color:var(--t4)">No description.</p>';
  S('#modal').innerHTML=`<div class="modal-wrap"><button class="close" onclick="closeModal()">&#215;</button><div class="modal"><div class="cover" ${modalCovBg}>${modalCovImg}<div class="badges"><span class="badge ${s}">${stL(s)}</span></div></div><div class="modal-body"><h2>${esc(e.name||'?')}</h2><div class="meta"><div class="row">${iconCal()} ${esc(fD(e.start_at))}</div><div class="row">${iconPin()} ${esc(e.full_address||e.venue||e.city||'')}</div></div>${scoresHtml(e)}${prepHtml(e)}${guests?`<div class="guests">${guests}</div>`:''}<div class="desc">${desc}</div><div class="actions"><button class="going-btn${goingSet.has(e.id)?' active':''}" id="modalGoingBtn" data-id="${esc(e.id)}" onclick="toggleGoing('${esc(e.id)}')">${goingSet.has(e.id)?'Going':'Mark as Going'}</button><a class="cal-btn" href="${esc(gcalUrl(e))}" target="_blank" rel="noopener" onclick="if(!goingSet.has('${esc(e.id)}'))toggleGoing('${esc(e.id)}')">Add to Calendar</a><a class="btn" href="${esc(e.url)}" target="_blank" rel="noopener">RSVP on Luma</a><button class="btn ghost" onclick="closeModal()">Close</button></div></div></div></div>`;
  S('#modalBg').classList.add('open');document.body.style.overflow='hidden';
}
function closeModal(){S('#modalBg').classList.remove('open');document.body.style.overflow=''}

/* Going / Calendar */
const GOING_KEY='luma_going_events';
let goingSet=new Set(JSON.parse(localStorage.getItem(GOING_KEY)||'[]'));
function saveGoing(){localStorage.setItem(GOING_KEY,JSON.stringify([...goingSet]))}
function toggleGoing(id,evt){
  if(evt)evt.stopPropagation();
  if(goingSet.has(id))goingSet.delete(id);else goingSet.add(id);
  saveGoing();renderMyEvents();
  SA(`.card[data-id="${id}"]`).forEach(c=>c.classList.toggle('going',goingSet.has(id)));
  const btn=S('#modalGoingBtn');if(btn&&btn.dataset.id===id){btn.classList.toggle('active',goingSet.has(id));btn.textContent=goingSet.has(id)?'Going':'Mark as Going'}
}
function gcalUrl(e){
  const start=(e.start_at||'').replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  const end=(e.end_at||e.start_at||'').replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  const title=encodeURIComponent(e.name||'Event');
  const loc=encodeURIComponent(e.full_address||e.venue||(e.city?e.city+', CA':''));
  const details=encodeURIComponent(`RSVP: ${e.url||''}\nHost: ${e.calendar_name||''}`);
  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${start}/${end}&location=${loc}&details=${details}&add=ayushi999@gmail.com`;
}
function renderMyEvents(){
  const el=S('#myEvents'),list=S('#myEventsList');
  const going=E.filter(e=>goingSet.has(e.id)).sort((a,b)=>(a.start_at||'').localeCompare(b.start_at||''));
  if(!going.length){el.classList.remove('show');return}
  el.classList.add('show');
  list.innerHTML=going.map(e=>`<span class="my-event-chip" onclick="openModal('${esc(e.id)}')">${esc((e.name||'').slice(0,35))} <span style="color:var(--t4);font-weight:400">${esc(fD(e.start_at).split(',')[0])}</span> <span class="remove" onclick="event.stopPropagation();toggleGoing('${esc(e.id)}')">&times;</span></span>`).join('');
}
window.toggleGoing=toggleGoing;window.closeModal=closeModal;window.openModal=openModal;

/* Swipe Mode */
let swipeList=[],swipeIdx=0;
function initSwipe(){
  swipeList=[...E].sort((a,b)=>activePerson?gS(b,activePerson)-gS(a,activePerson):(a.start_at||'').localeCompare(b.start_at||''));
  swipeIdx=0;picks=[];undoStack=[];renderSwipe();
}
function renderSwipe(){
  const stack=S('#swipeStack');if(!stack)return;
  stack.innerHTML='';
  const remaining=swipeList.slice(swipeIdx);
  const show=remaining.slice(0,3).reverse();
  show.forEach((e,i)=>{
    const isTop=i===show.length-1;
    const sc=activePerson?gS(e,activePerson):0;
    const card=document.createElement('div');
    card.className='swipe-card';
    card.style.zIndex=i+1;
    if(!isTop){card.style.transform=`scale(${1-(.03*(show.length-1-i))}) translateY(${(show.length-1-i)*8}px)`;card.style.opacity=.7+i*.15}
    card.innerHTML=`<div class="s-cover" style="background-color:${esc(e.tint)}"><img src="${esc(e.cover_url)}" loading="lazy" decoding="async" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"><div class="badges"><span class="badge ${st(e)}">${stL(st(e))}</span></div><div class="swipe-flash like">Like</div><div class="swipe-flash nope">Nope</div>${activePerson?`<div style="position:absolute;bottom:12px;left:12px">${ring(sc,'sm')}</div>`:''}</div><div class="s-body"><div class="s-title">${esc(e.name)}</div><div class="s-meta"><div>${esc(fD(e.start_at))}</div><div>${esc(e.city||'?')}</div></div><div class="s-host">by ${esc(e.calendar_name)}</div></div>`;
    if(isTop)setupDrag(card,e);
    stack.appendChild(card);
  });
  S('#swipeCounter').textContent=`${swipeIdx}/${swipeList.length}`;
  renderPicks();
}
function setupDrag(card,event){
  let sx=0,dx=0,dragging=false;
  const start=(x)=>{sx=x;dragging=true;card.style.transition='none'};
  const move=(x)=>{if(!dragging)return;dx=x-sx;const r=dx*.1;card.style.transform=`translateX(${dx}px) rotate(${r}deg)`;const like=card.querySelector('.like'),nope=card.querySelector('.nope');if(like)like.style.opacity=Math.max(0,dx/100);if(nope)nope.style.opacity=Math.max(0,-dx/100)};
  const end=()=>{if(!dragging)return;dragging=false;if(Math.abs(dx)>100){swipeAction(dx>0?'like':'skip',card,event)}else{card.style.transition='transform .3s var(--eo)';card.style.transform='';const like=card.querySelector('.like'),nope=card.querySelector('.nope');if(like)like.style.opacity=0;if(nope)nope.style.opacity=0}dx=0};
  card.addEventListener('mousedown',e=>{e.preventDefault();start(e.clientX)});
  window.addEventListener('mousemove',e=>move(e.clientX));
  window.addEventListener('mouseup',end);
  card.addEventListener('touchstart',e=>{start(e.touches[0].clientX)},{passive:true});
  card.addEventListener('touchmove',e=>{move(e.touches[0].clientX)},{passive:true});
  card.addEventListener('touchend',end);
}
function swipeAction(action,card,event){
  const dir=action==='like'?1:-1;
  if(card){card.style.transition='transform .4s var(--eo),opacity .4s';card.style.transform=`translateX(${dir*600}px) rotate(${dir*30}deg)`;card.style.opacity='0'}
  undoStack.push({idx:swipeIdx,action,event});
  if(action==='like')picks.push(event);
  swipeIdx++;
  setTimeout(renderSwipe,350);
}
function undoSwipe(){
  if(!undoStack.length)return;
  const last=undoStack.pop();
  if(last.action==='like')picks=picks.filter(p=>p.id!==last.event.id);
  swipeIdx=last.idx;
  renderSwipe();
}
function renderPicks(){
  const el=S('#picksList');if(!el)return;
  el.innerHTML=picks.map(p=>`<span class="pick-chip" onclick="openModal('${esc(p.id)}')">${esc((p.name||'').slice(0,30))}</span>`).join('');
  S('#picksCount').textContent=picks.length?`My Picks (${picks.length})`:'My Picks';
}
window.undoSwipe=undoSwipe;window.swipeAction=swipeAction;

/* Mode */
function setMode(m){
  mode=m;
  S('#discoverView').style.display=m==='discover'?'block':'none';
  S('#swipeView').classList.toggle('show',m==='swipe');
  SA('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===m));
  if(m==='swipe')initSwipe();
  if(m==='discover')filterAndRender();
}

/* Date */
function setDateRange(preset){
  const df=S('#dateFrom'),dt=S('#dateTo');
  const now=new Date();
  const fmt=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  SA('.date-quick button').forEach(b=>b.classList.remove('active'));
  if(preset==='today'){df.value=fmt(now);dt.value=fmt(now)}
  else if(preset==='week'){df.value=fmt(now);const end=new Date(now);end.setDate(end.getDate()+7);dt.value=fmt(end)}
  else if(preset==='month'){df.value=fmt(now);const end=new Date(now);end.setMonth(end.getMonth()+1);dt.value=fmt(end)}
  else{df.value='';dt.value=''}
  event.target.classList.add('active');
  filterAndRender();
}
window.setDateRange=setDateRange;

/* Filter drawer */
function toggleFilters(){
  const drawer=S('#filterDrawer'),btn=S('#filterToggle');
  drawer.classList.toggle('open');
  btn.classList.toggle('has-active',drawer.classList.contains('open'));
}
function updateFilterCount(){
  const count=cityF.size+catF.size+statusF.size+(S('#dateFrom').value?1:0)+(activePerson?1:0);
  const el=S('#filterCount');
  if(count){el.textContent=count;el.classList.add('show')}else{el.classList.remove('show')}
  S('#filterToggle').classList.toggle('has-active',count>0);
}
window.toggleFilters=toggleFilters;

/* Command palette */
function openCmd(){S('#cmdBg').classList.add('open');S('#cmdInput').value='';S('#cmdInput').focus();cmdSearch('')}
function closeCmd(){S('#cmdBg').classList.remove('open')}
function cmdSearch(q){
  q=q.toLowerCase().trim();
  const list=q?E.filter(e=>(e.name||'').toLowerCase().includes(q)||(e.calendar_name||'').toLowerCase().includes(q)||(e.city||'').toLowerCase().includes(q)).slice(0,8):E.slice(0,8);
  S('#cmdResults').innerHTML=list.map(e=>`<div class="cmd-item" onclick="closeCmd();openModal('${esc(e.id)}')"><div><div class="ci-title">${esc(e.name)}</div><div class="ci-meta">${esc(fD(e.start_at))} · ${esc(e.city||'?')}</div></div></div>`).join('');
}

/* Chips */
function buildChips(){
  const cities=new Map(),cats=new Map();
  E.forEach(e=>{cities.set(e.city||'TBD',(cities.get(e.city||'TBD')||0)+1);(e.categories||[]).forEach(c=>cats.set(c,(cats.get(c)||0)+1))});
  const pRow=S('#personChips'),people=new Set();
  E.forEach(e=>Object.keys(e.scores||{}).forEach(n=>people.add(n)));
  [...people].sort().forEach(p=>{
    const el=document.createElement('span');el.className='person-chip';el.textContent=p[0].toUpperCase()+p.slice(1);
    el.onclick=()=>{if(activePerson===p){activePerson=null;el.classList.remove('active');S('#sort').value='date';S('#scoreSlider').classList.remove('show');scoreThreshold=0;S('#scoreRange').value=0;S('#scoreVal').textContent='0'}else{activePerson=p;pRow.querySelectorAll('.person-chip').forEach(x=>x.classList.remove('active'));el.classList.add('active');S('#sort').value=p;S('#scoreSlider').classList.add('show');scoreThreshold=parseInt(S('#scoreRange').value)}updateFilterCount();if(mode==='discover')filterAndRender();else initSwipe()};
    pRow.appendChild(el);
  });
  const cRow=S('#cityChips');[...cities.entries()].sort((a,b)=>b[1]-a[1]).slice(0,8).forEach(([c,n])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${c} (${n})`;el.onclick=()=>{cityF.has(c)?cityF.delete(c):cityF.add(c);el.classList.toggle('active');updateFilterCount();filterAndRender()};cRow.appendChild(el)});
  const tRow=S('#catChips');[...cats.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).forEach(([c,n])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${c} (${n})`;el.onclick=()=>{catF.has(c)?catF.delete(c):catF.add(c);el.classList.toggle('active');updateFilterCount();filterAndRender()};tRow.appendChild(el)});
  const sRow=S('#statusChips');[['open','Open'],['waitlist','Waitlist'],['sold','Sold out']].forEach(([s,l])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${l} (${E.filter(e=>st(e)===s).length})`;el.onclick=()=>{statusF.has(s)?statusF.delete(s):statusF.add(s);el.classList.toggle('active');updateFilterCount();filterAndRender()};sRow.appendChild(el)});
}

/* Keyboard */
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  if(e.key==='/'){e.preventDefault();openCmd()}
  if(e.key==='Escape'){closeModal();closeCmd()}
  if(e.key==='s')setMode(mode==='discover'?'swipe':'discover');
  if(e.key==='1'){const chips=SA('.person-chip');if(chips[0])chips[0].click()}
  if(e.key==='2'){const chips=SA('.person-chip');if(chips[1])chips[1].click()}
  if(e.key==='f')toggleFilters();
});

/* Init */
// Event delegation: single listener handles all card clicks (including deferred sections)
S('#grid').addEventListener('click',e=>{
  const card=e.target.closest('.card');
  if(card&&card.dataset.id)openModal(card.dataset.id);
});
S('#modalBg').addEventListener('click',e=>{if(e.target.id==='modalBg')closeModal()});
S('#cmdBg').addEventListener('click',e=>{if(e.target.id==='cmdBg')closeCmd()});
S('#cmdInput').addEventListener('input',e=>cmdSearch(e.target.value));
S('#search').addEventListener('input',debounce(filterAndRender,150));
S('#dateFrom').addEventListener('change',()=>{updateFilterCount();filterAndRender()});
S('#dateTo').addEventListener('change',()=>{updateFilterCount();filterAndRender()});
S('#scoreRange').addEventListener('input',e=>{scoreThreshold=parseInt(e.target.value);S('#scoreVal').textContent=scoreThreshold;filterAndRender()});
S('#sort').addEventListener('change',()=>{const v=S('#sort').value;if(v!=='date'&&v!=='rsvps'&&v!=='name'){activePerson=v;SA('.person-chip').forEach(x=>x.classList.toggle('active',x.textContent.toLowerCase()===v))}filterAndRender()});
SA('.mode-btn').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
buildChips();
setMode(isMobile?'swipe':'discover');
renderSummary();
renderMyEvents();
"""



def build_html(data: dict, slimmed: list[dict]) -> str:
    fetched = data.get("scored_at") or data.get("fetched_at") or ""
    total = len(slimmed)
    total_rsvps = sum(e.get("guest_count", 0) or 0 for e in slimmed)
    open_count = sum(1 for e in slimmed if not e.get("sold_out") and not e.get("waitlist_active"))
    sold_count = sum(1 for e in slimmed if e.get("sold_out"))

    data_json = json.dumps(slimmed, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Luma Bay Area Events</title>
<style>{CSS}</style>
</head><body>
<div class="wrap">
  <header>
    <div class="header-row">
      <div>
        <h1>Luma Bay Area Events</h1>
        <div class="sub">{total} events &middot; updated {html.escape(fetched[:10])}</div>
        <div class="summary" id="summary"></div>
      </div>
      <div class="mode-toggle">
        <button class="mode-btn active" data-mode="discover">Discover</button>
        <button class="mode-btn" data-mode="swipe">Swipe</button>
      </div>
    </div>
  </header>

  <div class="toolbar">
    <input type="search" id="search" placeholder="Search events..."/>
    <label>Sort: <select id="sort">
      <option value="date">Date</option>
      <option value="rsvps">RSVPs</option>
      <option value="sumeet">Sumeet</option>
      <option value="ayushi">Ayushi</option>
      <option value="name">Name</option>
    </select></label>
    <button class="filter-toggle" id="filterToggle" onclick="toggleFilters()">Filters <span class="filter-count" id="filterCount"></span></button>
  </div>
  <div class="filter-drawer" id="filterDrawer">
    <div class="person-chips" id="personChips"><span class="label">For:</span></div>
    <div class="score-slider" id="scoreSlider">
      <label>Min score</label>
      <input type="range" id="scoreRange" min="0" max="100" value="0"/>
      <span class="val" id="scoreVal">0</span>
    </div>
    <div class="chips" id="statusChips"></div>
    <div class="chips" id="catChips"></div>
    <div class="chips" id="cityChips"></div>
    <div class="date-range">
      <label>From</label><input type="date" id="dateFrom"/>
      <label>To</label><input type="date" id="dateTo"/>
      <div class="date-quick">
        <button onclick="setDateRange('today')">Today</button>
        <button onclick="setDateRange('week')">This Week</button>
        <button onclick="setDateRange('month')">This Month</button>
        <button onclick="setDateRange('all')" class="active">All</button>
      </div>
    </div>
  </div>

  <div id="discoverView">
    <div class="my-events" id="myEvents">
      <h3>My Events</h3>
      <div class="my-events-list" id="myEventsList"></div>
    </div>
    <div class="hero" id="hero"></div>
    <div class="count" id="count"></div>
    <div id="grid"></div>
  </div>

  <div class="swipe-container" id="swipeView">
    <div class="swipe-stack" id="swipeStack"></div>
    <div class="swipe-actions">
      <button class="swipe-btn undo-btn" onclick="undoSwipe()" title="Undo">&#8630;</button>
      <button class="swipe-btn skip" onclick="swipeAction('skip')" title="Skip">&#10005;</button>
      <button class="swipe-btn like-btn" onclick="swipeAction('like')" title="Interested">&#10003;</button>
    </div>
    <div class="swipe-counter" id="swipeCounter"></div>
    <div class="picks-bar">
      <div class="picks-label" id="picksCount">My Picks</div>
      <div class="picks-list" id="picksList"></div>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalBg"><div id="modal"></div></div>

<div class="cmd-bg" id="cmdBg">
  <div class="cmd-box">
    <input class="cmd-input" id="cmdInput" placeholder="Search events..." autocomplete="off"/>
    <div class="cmd-results" id="cmdResults"></div>
  </div>
</div>

<script type="application/json" id="data">{data_json}</script>
<script>window.__EVENTS__=JSON.parse(document.getElementById('data').textContent);</script>
<script>{JS}</script>
</body></html>"""


def main() -> int:
    src = latest_dump()
    print(f"Reading {src.name}", flush=True)
    data = json.loads(src.read_text(encoding="utf-8"))
    slimmed = slim(data["events"])
    print(f"Slimmed {len(slimmed)} events", flush=True)
    out = OUT_DIR / "viewer.html"
    out.write_text(build_html(data, slimmed), encoding="utf-8")
    print(f"Wrote {out}", flush=True)
    print(f"Size: {out.stat().st_size / 1024:.1f} KB")
    print(f"\nOpen in browser: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

