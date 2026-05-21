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
        })
    if dropped:
        print(f"  dropped {dropped} past events", flush=True)
    return out


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{color-scheme:dark;scroll-behavior:smooth}
@media(prefers-reduced-motion:reduce){*,html{scroll-behavior:auto!important;animation-duration:.01ms!important;transition-duration:.01ms!important}}
body{font-family:'Inter',system-ui,sans-serif;background:#020617;color:#e2e8f0;line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;z-index:-1;background:radial-gradient(ellipse 80% 50% at 20% 10%,rgba(124,58,237,.1),transparent),radial-gradient(ellipse 60% 40% at 80% 80%,rgba(14,165,233,.07),transparent),radial-gradient(ellipse 50% 50% at 50% 0%,rgba(34,197,94,.05),transparent)}
.wrap{max-width:1440px;margin:0 auto;padding:20px 24px}
@media(max-width:640px){.wrap{padding:12px 14px}}

/* Header */
header{margin-bottom:20px}
.header-row{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
h1{font-family:'Outfit',sans-serif;font-size:28px;font-weight:800;letter-spacing:-.02em;background:linear-gradient(135deg,#a78bfa,#7c3aed 40%,#22c55e 80%,#0ea5e9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sub{color:#475569;font-size:12px;font-weight:500}
.mode-toggle{display:flex;background:rgba(15,23,42,.6);border:1px solid rgba(100,116,139,.15);border-radius:12px;overflow:hidden}
.mode-btn{padding:8px 18px;font-size:13px;font-weight:600;color:#64748b;background:transparent;border:none;cursor:pointer;transition:all .2s;font-family:inherit}
.mode-btn.active{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff}
.mode-btn:hover:not(.active){color:#e2e8f0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:16px 0}
.stat{background:rgba(15,23,42,.7);border:1px solid rgba(100,116,139,.1);border-radius:14px;padding:14px 16px}
.stat .n{font-family:'Outfit',sans-serif;font-size:26px;font-weight:700;color:#f8fafc}
.stat .l{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.1em;font-weight:700;margin-top:2px}

/* Controls */
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0;padding:14px 16px;background:rgba(15,23,42,.5);border:1px solid rgba(100,116,139,.1);border-radius:14px;backdrop-filter:blur(16px)}
.controls input,.controls select{background:rgba(2,6,23,.7);color:#e2e8f0;border:1px solid rgba(100,116,139,.15);border-radius:10px;padding:9px 14px;font-size:13px;font-family:inherit;outline:none;transition:border-color .2s,box-shadow .2s}
.controls input:focus,.controls select:focus{border-color:#7c3aed;box-shadow:0 0 0 3px rgba(124,58,237,.15)}
.controls input[type=search]{flex:1;min-width:180px}
.controls input::placeholder{color:#334155}
.controls label{font-size:12px;color:#475569;font-weight:600}
.controls select{cursor:pointer}
.chips{display:flex;flex-wrap:wrap;gap:5px;width:100%}
.chip{background:rgba(30,41,59,.5);color:#94a3b8;border:1px solid rgba(100,116,139,.1);border-radius:999px;padding:4px 12px;font-size:11px;font-weight:500;cursor:pointer;user-select:none;transition:all .2s}
.chip:hover{background:rgba(51,65,85,.5);color:#e2e8f0}
.chip.active{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border-color:transparent;box-shadow:0 2px 8px rgba(124,58,237,.25)}
.person-chips{display:flex;gap:8px;align-items:center}
.person-chips .label{font-size:10px;color:#334155;text-transform:uppercase;letter-spacing:.12em;font-weight:800}
.person-chip{background:rgba(30,41,59,.5);color:#94a3b8;border:1px solid rgba(100,116,139,.1);border-radius:999px;padding:6px 16px;font-size:13px;font-weight:600;cursor:pointer;user-select:none;transition:all .25s}
.person-chip:hover{background:rgba(51,65,85,.5);color:#e2e8f0}
.person-chip.active{background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border-color:transparent;box-shadow:0 4px 16px rgba(124,58,237,.3)}
.count{margin:12px 0 8px;color:#475569;font-size:12px;font-weight:500}

/* Hero */
.hero{display:none;margin:20px 0;border-radius:18px;overflow:hidden;position:relative;min-height:220px;background-size:cover;background-position:center;cursor:pointer;transition:transform .3s}
.hero:hover{transform:scale(1.005)}
.hero.show{display:block}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(135deg,rgba(2,6,23,.85),rgba(2,6,23,.4));display:flex;align-items:flex-end;padding:28px 32px}
.hero-content{display:flex;align-items:flex-end;gap:24px;width:100%}
.hero-text{flex:1}
.hero-label{font-size:11px;color:#a78bfa;text-transform:uppercase;letter-spacing:.1em;font-weight:700;margin-bottom:6px}
.hero-title{font-family:'Outfit',sans-serif;font-size:28px;font-weight:800;color:#f8fafc;line-height:1.2;margin-bottom:8px}
.hero-meta{font-size:13px;color:#94a3b8}
.hero-ring{flex-shrink:0}
@media(max-width:640px){.hero{min-height:180px}.hero-overlay{padding:18px}.hero-title{font-size:20px}.hero-content{flex-direction:column;align-items:flex-start;gap:12px}}

/* Score ring SVG */
.ring-wrap{position:relative;display:inline-flex;align-items:center;justify-content:center}
.ring-val{position:absolute;font-family:'Outfit',sans-serif;font-weight:800;color:#f8fafc}
.ring-sm .ring-val{font-size:12px}
.ring-lg .ring-val{font-size:22px}

/* Section headers (time grouping) */
.section-header{font-family:'Outfit',sans-serif;font-size:18px;font-weight:700;color:#94a3b8;margin:28px 0 14px;padding-bottom:8px;border-bottom:1px solid rgba(100,116,139,.1);display:flex;align-items:center;gap:8px}
.section-header .dot{width:8px;height:8px;border-radius:50%;background:#22c55e;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.section{opacity:0;transform:translateY(12px);transition:opacity .4s,transform .4s}
.section.visible{opacity:1;transform:translateY(0)}
.section .grid .card{opacity:0;transform:translateY(8px);transition:opacity .3s,transform .3s}
.section.visible .grid .card{opacity:1;transform:translateY(0)}

/* Card grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.card{background:rgba(15,23,42,.65);border:1px solid rgba(100,116,139,.08);border-radius:16px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;transition:transform .3s cubic-bezier(.22,1,.36,1),border-color .3s,box-shadow .3s;transform-style:preserve-3d;contain:layout style}
.card:hover{transform:translateY(-4px);border-color:rgba(124,58,237,.2);box-shadow:0 16px 48px rgba(0,0,0,.25),0 0 0 1px rgba(124,58,237,.08);will-change:transform}
.cover{height:160px;background-size:cover;background-position:center;background-color:#1e293b;position:relative;contain:layout style paint}
.cover .ring-wrap{position:absolute;top:10px;left:10px;z-index:2}
.badges{position:absolute;top:10px;right:10px;display:flex;gap:5px}
.badge{background:rgba(0,0,0,.55);backdrop-filter:blur(8px);color:#fff;font-size:10px;font-weight:600;padding:4px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
.badge.sold{background:rgba(220,38,38,.8)}.badge.waitlist{background:rgba(234,88,12,.8)}.badge.open{background:rgba(34,197,94,.75)}
.body{padding:14px 16px;display:flex;flex-direction:column;gap:6px;flex:1}
.title{font-family:'Outfit',sans-serif;font-size:15px;font-weight:600;color:#f1f5f9;line-height:1.3}
.meta{display:flex;flex-direction:column;gap:3px;font-size:12px;color:#64748b}
.meta .row{display:flex;align-items:center;gap:5px}
.icon{width:13px;height:13px;opacity:.45;flex-shrink:0}
.host{display:flex;align-items:center;gap:6px;margin-top:auto;padding-top:10px;border-top:1px solid rgba(100,116,139,.08);font-size:11px;color:#475569}
.host img{width:20px;height:20px;border-radius:50%;object-fit:cover}
.cats{display:flex;flex-wrap:wrap;gap:3px}
.cat{background:rgba(30,41,59,.6);color:#64748b;font-size:9px;font-weight:600;padding:2px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.06em}
.rsvp-strip{display:flex;justify-content:space-between;align-items:center;font-size:11px;margin-top:4px}
.rsvp-count{color:#94a3b8;font-weight:600}
.rsvp-count span{color:#475569;font-weight:400}

/* ── Swipe Mode ──────────────────────────────────────────────────────── */
.swipe-container{display:none;flex-direction:column;align-items:center;padding:20px 0;min-height:70vh;position:relative}
.swipe-container.show{display:flex}
.swipe-stack{position:relative;width:340px;height:480px;max-width:90vw}
@media(max-width:400px){.swipe-stack{width:300px;height:440px}}
.swipe-card{position:absolute;inset:0;border-radius:20px;overflow:hidden;background:#0f172a;border:1px solid rgba(100,116,139,.12);cursor:grab;touch-action:none;user-select:none;will-change:transform;transition:box-shadow .2s}
.swipe-card:active{cursor:grabbing}
.swipe-card .s-cover{height:55%;background-size:cover;background-position:center;position:relative}
.swipe-card .s-body{padding:18px;display:flex;flex-direction:column;gap:8px;height:45%;overflow:hidden}
.swipe-card .s-title{font-family:'Outfit',sans-serif;font-size:20px;font-weight:700;color:#f1f5f9;line-height:1.2}
.swipe-card .s-meta{font-size:13px;color:#94a3b8;display:flex;flex-direction:column;gap:4px}
.swipe-card .s-host{font-size:12px;color:#475569;margin-top:auto}
.swipe-card .s-scores{display:flex;gap:12px;margin-top:8px}
.swipe-flash{position:absolute;top:20px;border-radius:8px;padding:6px 18px;font-family:'Outfit',sans-serif;font-size:20px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;opacity:0;transition:opacity .15s;pointer-events:none;z-index:10}
.swipe-flash.like{right:20px;color:#22c55e;border:3px solid #22c55e;transform:rotate(12deg)}
.swipe-flash.nope{left:20px;color:#ef4444;border:3px solid #ef4444;transform:rotate(-12deg)}
.swipe-actions{display:flex;gap:16px;margin-top:24px}
.swipe-btn{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(100,116,139,.2);background:rgba(15,23,42,.8);cursor:pointer;font-size:22px;transition:all .2s;color:#94a3b8}
.swipe-btn:hover{transform:scale(1.1)}
.swipe-btn.skip{color:#ef4444;border-color:rgba(239,68,68,.3)}.swipe-btn.skip:hover{background:rgba(239,68,68,.15)}
.swipe-btn.like-btn{color:#22c55e;border-color:rgba(34,197,94,.3)}.swipe-btn.like-btn:hover{background:rgba(34,197,94,.15)}
.swipe-btn.undo-btn{color:#a78bfa;border-color:rgba(167,139,250,.3);font-size:16px}.swipe-btn.undo-btn:hover{background:rgba(167,139,250,.15)}
.swipe-counter{margin-top:16px;font-size:13px;color:#475569;font-weight:500}
.picks-bar{margin-top:20px;width:100%;max-width:400px}
.picks-label{font-size:12px;color:#475569;text-transform:uppercase;letter-spacing:.1em;font-weight:700;margin-bottom:8px}
.picks-list{display:flex;flex-wrap:wrap;gap:6px}
.pick-chip{background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.2);border-radius:8px;padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer;transition:all .2s}
.pick-chip:hover{background:rgba(34,197,94,.25)}

/* ── Modal ───────────────────────────────────────────────────────────── */
.modal-bg{display:none;position:fixed;inset:0;background:rgba(2,6,23,.8);backdrop-filter:blur(12px);z-index:100;align-items:flex-start;justify-content:center;padding:40px 20px;overflow-y:auto}
.modal-bg.open{display:flex}
@media(max-width:640px){.modal-bg{padding:0;align-items:flex-end}.modal-bg .modal-wrap{max-width:100%}.modal-bg .modal{border-radius:20px 20px 0 0;max-height:92vh;overflow-y:auto}}
.modal-wrap{position:relative;width:100%;max-width:700px}
.modal{background:rgba(15,23,42,.95);border:1px solid rgba(100,116,139,.12);border-radius:18px;width:100%;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.5);backdrop-filter:blur(20px)}
.modal .cover{height:240px}
@media(max-width:640px){.modal .cover{height:180px}}
.modal-body{padding:24px}
.modal h2{font-family:'Outfit',sans-serif;font-size:24px;font-weight:700;color:#f1f5f9;line-height:1.3;margin-bottom:12px}
.modal .meta{font-size:13px;color:#94a3b8;margin-bottom:14px}
.modal-scores{display:flex;gap:12px;margin:14px 0;padding:16px;background:rgba(30,41,59,.35);border:1px solid rgba(100,116,139,.08);border-radius:14px}
.modal-score-item{flex:1;text-align:center}
.modal-score-item .name{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.1em;font-weight:800;margin-bottom:6px}
.modal-score-item .why{font-size:11px;color:#64748b;margin-top:6px;line-height:1.4}
.modal .desc{color:#cbd5e1;font-size:13px;line-height:1.7;margin:16px 0;max-height:350px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:#334155 transparent}
.modal .desc p{margin-bottom:8px}.modal .desc a{color:#a78bfa;text-decoration:underline;text-underline-offset:2px}.modal .desc a:hover{color:#c4b5fd}
.modal .desc img{max-width:100%;border-radius:8px;margin:8px 0}.modal .desc h2,.modal .desc h3{font-family:'Outfit',sans-serif;color:#f1f5f9;margin:12px 0 6px}
.modal .desc ul,.modal .desc ol{padding-left:18px;margin-bottom:8px}.modal .desc li{margin-bottom:3px}.modal .desc hr{border:none;border-top:1px solid rgba(100,116,139,.1);margin:12px 0}
.modal .actions{display:flex;gap:10px;margin-top:16px}
.btn{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:11px 22px;border-radius:12px;text-decoration:none;font-size:13px;font-weight:600;border:none;cursor:pointer;transition:all .2s;box-shadow:0 4px 12px rgba(124,58,237,.25)}
.btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(124,58,237,.35)}
.btn.ghost{background:transparent;border:1px solid rgba(100,116,139,.15);color:#94a3b8;box-shadow:none}.btn.ghost:hover{background:rgba(30,41,59,.5);color:#e2e8f0;transform:none}
.guests{display:flex;margin:10px 0}.guests img{width:28px;height:28px;border-radius:50%;border:2px solid #0f172a;margin-left:-6px;object-fit:cover}.guests img:first-child{margin-left:0}
.close{position:absolute;top:14px;right:14px;background:rgba(0,0,0,.45);color:#fff;width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.08);cursor:pointer;font-size:18px;z-index:2;display:flex;align-items:center;justify-content:center;transition:all .2s;backdrop-filter:blur(8px)}.close:hover{background:rgba(220,38,38,.6)}

/* Confetti canvas */
#confetti{position:fixed;inset:0;pointer-events:none;z-index:200}

/* Keyboard hint */
.kb-hint{position:fixed;bottom:16px;right:16px;background:rgba(15,23,42,.8);border:1px solid rgba(100,116,139,.12);border-radius:8px;padding:6px 12px;font-size:11px;color:#475569;backdrop-filter:blur(8px);z-index:50;display:flex;align-items:center;gap:6px}
.kb-hint kbd{background:rgba(51,65,85,.5);border:1px solid rgba(100,116,139,.2);border-radius:4px;padding:1px 6px;font-family:'Outfit',monospace;font-size:10px;color:#94a3b8}
@media(max-width:768px){.kb-hint{display:none}}

/* Scrollbar */
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:#1e293b;border-radius:3px}::-webkit-scrollbar-thumb:hover{background:#334155}

/* Command palette */
.cmd-bg{display:none;position:fixed;inset:0;background:rgba(2,6,23,.75);backdrop-filter:blur(8px);z-index:150;align-items:flex-start;justify-content:center;padding:15vh 20px 20px}
.cmd-bg.open{display:flex}
.cmd-box{width:100%;max-width:560px;background:rgba(15,23,42,.95);border:1px solid rgba(100,116,139,.15);border-radius:16px;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.5)}
.cmd-input{width:100%;background:transparent;border:none;border-bottom:1px solid rgba(100,116,139,.1);padding:16px 20px;font-size:16px;color:#e2e8f0;font-family:inherit;outline:none}
.cmd-input::placeholder{color:#334155}
.cmd-results{max-height:360px;overflow-y:auto;padding:8px}
.cmd-item{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:10px;cursor:pointer;transition:background .15s}
.cmd-item:hover,.cmd-item.active{background:rgba(124,58,237,.12)}
.cmd-item .ci-title{font-size:14px;font-weight:500;color:#e2e8f0}
.cmd-item .ci-meta{font-size:11px;color:#475569}
"""

# ── JS ────────────────────────────────────────────────────────────────────────
JS = r"""
const E=window.__EVENTS__,S=s=>document.querySelector(s),SA=s=>document.querySelectorAll(s);
let mode='discover',activePerson=null,picks=[],undoStack=[];
const cityF=new Set(),catF=new Set(),statusF=new Set();
const isMobile='ontouchstart'in window&&innerWidth<768;
let debounceTimer=null;
const debounce=(fn,ms)=>(...a)=>{clearTimeout(debounceTimer);debounceTimer=setTimeout(()=>fn(...a),ms)};

const fD=s=>{if(!s)return'?';const d=new Date(s);return d.toLocaleString('en-US',{timeZone:'America/Los_Angeles',weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})};
const PST=-8,PDT=-7,TZ_OFF=PDT;
function toPST(d){return new Date(d.getTime()+(d.getTimezoneOffset()+TZ_OFF*60)*60000)}
const relDay=s=>{if(!s)return'later';const d=toPST(new Date(s)),n=toPST(new Date());const ed=new Date(d.getFullYear(),d.getMonth(),d.getDate()),td=new Date(n.getFullYear(),n.getMonth(),n.getDate());const diff=Math.round((ed-td)/864e5);if(diff<0)return'past';if(diff===0)return'today';if(diff===1)return'tomorrow';if(diff<=7)return'week';if(diff<=30)return'month';return'later'};
const st=e=>e.sold_out?'sold':e.waitlist_active?'waitlist':'open';
const stL=s=>({sold:'Sold out',waitlist:'Waitlist',open:'Open'})[s];
const scC=n=>n>=80?'#22c55e':n>=50?'#eab308':'#334155';
const gS=(e,p)=>((e.scores||{})[p]||{}).score||0;
const esc=s=>s==null?'':String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);

function ring(score,size){
  const r=size==='lg'?44:18,sw=size==='lg'?6:3,circ=2*Math.PI*r;
  const off=circ*(1-score/100),col=scC(score);
  return `<div class="ring-wrap ring-${size}"><svg width="${(r+sw)*2}" height="${(r+sw)*2}" style="transform:rotate(-90deg)"><circle cx="${r+sw}" cy="${r+sw}" r="${r}" fill="none" stroke="rgba(100,116,139,.15)" stroke-width="${sw}"/><circle cx="${r+sw}" cy="${r+sw}" r="${r}" fill="none" stroke="${col}" stroke-width="${sw}" stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${off}" style="transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)"/></svg><span class="ring-val" style="color:${col}">${score}</span></div>`;
}

function iconCal(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'}
function iconPin(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>'}

function buildCard(e){
  const s=st(e),sc=activePerson?gS(e,activePerson):0;
  const cov=e.cover_url?`style="background-image:url('${esc(e.cover_url)}');background-color:${esc(e.tint)}"`:`style="background-color:${esc(e.tint)}"`;
  const hn=e.calendar_name||(e.hosts[0]||{}).name||'';
  const ha=e.calendar_avatar||(e.hosts[0]||{}).avatar||'';
  const cats=(e.categories||[]).slice(0,3).map(c=>`<span class="cat">${esc(c)}</span>`).join('');
  const ringPlaceholder=activePerson?`<div class="ring-placeholder" data-score="${sc}" style="position:absolute;top:10px;left:10px;z-index:2;width:42px;height:42px"></div>`:'';
  return `<div class="card" data-id="${esc(e.id)}" tabindex="0"><div class="cover" ${cov}>${ringPlaceholder}<div class="badges"><span class="badge ${s}">${stL(s)}</span></div></div><div class="body"><div class="title">${esc(e.name||'?')}</div><div class="meta"><div class="row">${iconCal()} ${esc(fD(e.start_at))}</div><div class="row">${iconPin()} ${esc(e.venue||e.city||'?')}${e.city&&e.venue?', '+esc(e.city):''}</div></div><div class="cats">${cats}</div><div class="host">${ha?`<img src="${esc(ha)}" loading="lazy" alt=""/>`:''}by ${esc(hn)}</div><div class="rsvp-strip"><span class="rsvp-count">${(e.guest_count||0).toLocaleString()} <span>RSVPs</span></span></div></div></div>`;
}

/* ── Hero ─────────────────────────────────────────────────────────────── */
function renderHero(){
  const h=S('#hero');
  if(!activePerson){h.classList.remove('show');return}
  const sorted=[...E].sort((a,b)=>gS(b,activePerson)-gS(a,activePerson));
  const e=sorted[0];if(!e||gS(e,activePerson)<40){h.classList.remove('show');return}
  const sc=gS(e,activePerson);
  h.style.backgroundImage=e.cover_url?`url('${e.cover_url}')`:'none';
  h.style.backgroundColor=e.tint;
  h.innerHTML=`<div class="hero-overlay"><div class="hero-content"><div class="hero-text"><div class="hero-label">Top pick for ${activePerson}</div><div class="hero-title">${esc(e.name)}</div><div class="hero-meta">${esc(fD(e.start_at))} &middot; ${esc(e.city||'?')} &middot; ${(e.guest_count||0).toLocaleString()} RSVPs</div></div><div class="hero-ring">${ring(sc,'lg')}</div></div></div>`;
  h.classList.add('show');
  h.onclick=()=>openModal(e.id);
}

/* ── Discover mode ────────────────────────────────────────────────────── */
const sectionObs=new IntersectionObserver((entries)=>{
  entries.forEach(entry=>{
    if(entry.isIntersecting){
      entry.target.classList.add('visible');
      // Stagger card animations
      const cards=entry.target.querySelectorAll('.card');
      cards.forEach((c,i)=>{c.style.transitionDelay=`${Math.min(i*40,400)}ms`});
      // Hydrate score ring placeholders
      entry.target.querySelectorAll('.ring-placeholder').forEach(ph=>{
        const sc=parseInt(ph.dataset.score)||0;
        ph.innerHTML=ring(sc,'sm');
        ph.classList.remove('ring-placeholder');
      });
      sectionObs.unobserve(entry.target);
    }
  });
},{rootMargin:'100px 0px',threshold:0.01});

function filterAndRender(){
  let list=E.slice();
  const q=(S('#search').value||'').toLowerCase().trim();
  if(q)list=list.filter(e=>(e.name||'').toLowerCase().includes(q)||(e.calendar_name||'').toLowerCase().includes(q)||(e.city||'').toLowerCase().includes(q));
  if(cityF.size)list=list.filter(e=>cityF.has(e.city||'TBD'));
  if(catF.size)list=list.filter(e=>(e.categories||[]).some(c=>catF.has(c)));
  if(statusF.size)list=list.filter(e=>statusF.has(st(e)));
  const sv=S('#sort').value;
  if(sv==='date')list.sort((a,b)=>(a.start_at||'').localeCompare(b.start_at||''));
  else if(sv==='rsvps')list.sort((a,b)=>(b.guest_count||0)-(a.guest_count||0));
  else if(sv==='name')list.sort((a,b)=>(a.name||'').localeCompare(b.name||''));
  else list.sort((a,b)=>gS(b,sv)-gS(a,sv));

  const grid=S('#grid');
  const groups={today:[],tomorrow:[],week:[],month:[],later:[],past:[]};
  list.forEach(e=>{const g=relDay(e.start_at);(groups[g]||groups.later).push(e)});
  const labels={today:'Happening Today',tomorrow:'Tomorrow',week:'This Week',month:'This Month',later:'Later'};

  // Build HTML with section wrappers for lazy reveal
  const frag=document.createDocumentFragment();
  for(const[k,lbl]of Object.entries(labels)){
    const evts=groups[k];if(!evts||!evts.length)continue;
    const section=document.createElement('div');
    section.className='section';
    const dot=k==='today'?'<span class="dot"></span>':'';
    section.innerHTML=`<div class="section-header">${dot}${lbl} <span style="color:#334155;font-weight:400;font-size:13px">(${evts.length})</span></div><div class="grid">${evts.map(buildCard).join('')}</div>`;
    frag.appendChild(section);
    // Observe AFTER appending to DOM
    requestAnimationFrame(()=>sectionObs.observe(section));
  }
  grid.innerHTML='';
  grid.appendChild(frag);

  S('#count').textContent=`${list.length} of ${E.length} events`;
  SA('.card').forEach(c=>{c.addEventListener('click',()=>openModal(c.dataset.id));c.addEventListener('keydown',ev=>{if(ev.key==='Enter')openModal(c.dataset.id)})});
  renderHero();
}

/* ── Modal ────────────────────────────────────────────────────────────── */
function scoresHtml(e){
  const sc=e.scores||{};const names=Object.keys(sc);if(!names.length)return'';
  return `<div class="modal-scores">${names.map(n=>{const s=sc[n]||{};const v=s.score||0;return `<div class="modal-score-item"><div class="name">${esc(n)}</div>${ring(v,'sm')}<div class="why">${esc(s.reason||'')}</div></div>`}).join('')}</div>`;
}
function openModal(id){
  const e=E.find(x=>x.id===id);if(!e)return;
  const s=st(e);const cov=e.cover_url?`style="background-image:url('${esc(e.cover_url)}');background-color:${esc(e.tint)}"`:`style="background-color:${esc(e.tint)}"`;
  const guests=(e.featured_guests||[]).map(g=>`<img src="${esc(g.avatar||'')}" title="${esc(g.name||'')}" alt=""/>`).join('');
  const desc=e.description_html||'<p style="color:#475569">No description.</p>';
  S('#modal').innerHTML=`<div class="modal-wrap"><button class="close" onclick="closeModal()">&times;</button><div class="modal"><div class="cover" ${cov}><div class="badges"><span class="badge ${s}">${stL(s)}</span></div></div><div class="modal-body"><h2>${esc(e.name||'?')}</h2><div class="meta"><div class="row">${iconCal()} ${esc(fD(e.start_at))}</div><div class="row">${iconPin()} ${esc(e.full_address||e.venue||e.city||'')}</div></div>${scoresHtml(e)}${guests?`<div class="guests">${guests}</div>`:''}<div class="desc">${desc}</div><div class="actions"><a class="btn" href="${esc(e.url)}" target="_blank" rel="noopener" onclick="confetti(event)">RSVP on Luma</a><button class="btn ghost" onclick="closeModal()">Close</button></div></div></div></div>`;
  S('#modalBg').classList.add('open');document.body.style.overflow='hidden';
}
function closeModal(){S('#modalBg').classList.remove('open');document.body.style.overflow=''}

/* ── Swipe Mode ───────────────────────────────────────────────────────── */
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
    card.innerHTML=`<div class="s-cover" style="background-image:url('${esc(e.cover_url)}');background-color:${esc(e.tint)}"><div class="badges"><span class="badge ${st(e)}">${stL(st(e))}</span></div><div class="swipe-flash like">Like</div><div class="swipe-flash nope">Nope</div>${activePerson?`<div style="position:absolute;bottom:12px;left:12px">${ring(sc,'sm')}</div>`:''}</div><div class="s-body"><div class="s-title">${esc(e.name)}</div><div class="s-meta"><div>${esc(fD(e.start_at))}</div><div>${esc(e.city||'?')}</div></div><div class="s-host">by ${esc(e.calendar_name)}</div></div>`;
    if(isTop)setupDrag(card,e);
    stack.appendChild(card);
  });
  S('#swipeCounter').textContent=`${swipeIdx}/${swipeList.length}`;
  renderPicks();
}
function setupDrag(card,event){
  let sx=0,sy=0,dx=0,dragging=false;
  const start=(x,y)=>{sx=x;sy=y;dragging=true;card.style.transition='none'};
  const move=(x,y)=>{if(!dragging)return;dx=x-sx;const r=dx*.1;card.style.transform=`translateX(${dx}px) rotate(${r}deg)`;const like=card.querySelector('.like'),nope=card.querySelector('.nope');if(like)like.style.opacity=Math.max(0,dx/100);if(nope)nope.style.opacity=Math.max(0,-dx/100)};
  const end=()=>{if(!dragging)return;dragging=false;if(Math.abs(dx)>100){swipeAction(dx>0?'like':'skip',card,event)}else{card.style.transition='transform .3s';card.style.transform='';const like=card.querySelector('.like'),nope=card.querySelector('.nope');if(like)like.style.opacity=0;if(nope)nope.style.opacity=0}dx=0};
  card.addEventListener('mousedown',e=>{e.preventDefault();start(e.clientX,e.clientY)});
  window.addEventListener('mousemove',e=>move(e.clientX,e.clientY));
  window.addEventListener('mouseup',end);
  card.addEventListener('touchstart',e=>{const t=e.touches[0];start(t.clientX,t.clientY)},{passive:true});
  card.addEventListener('touchmove',e=>{const t=e.touches[0];move(t.clientX,t.clientY)},{passive:true});
  card.addEventListener('touchend',end);
}
function swipeAction(action,card,event){
  const dir=action==='like'?1:-1;
  if(card){card.style.transition='transform .4s cubic-bezier(.22,1,.36,1),opacity .4s';card.style.transform=`translateX(${dir*600}px) rotate(${dir*30}deg)`;card.style.opacity='0'}
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

/* ── Confetti ─────────────────────────────────────────────────────────── */
function confetti(evt){
  if(evt)evt.stopPropagation();
  const c=S('#confetti'),ctx=c.getContext('2d');c.width=innerWidth;c.height=innerHeight;
  const particles=Array.from({length:40},()=>({x:innerWidth/2,y:innerHeight/2,vx:(Math.random()-.5)*16,vy:Math.random()*-14-4,r:Math.random()*4+2,c:['#7c3aed','#22c55e','#0ea5e9','#eab308','#ef4444','#a78bfa'][Math.floor(Math.random()*6)],life:1}));
  let frame=0;
  function draw(){ctx.clearRect(0,0,c.width,c.height);let alive=false;particles.forEach(p=>{if(p.life<=0)return;alive=true;p.x+=p.vx;p.y+=p.vy;p.vy+=.5;p.life-=.02;ctx.globalAlpha=p.life;ctx.fillStyle=p.c;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill()});ctx.globalAlpha=1;if(alive&&frame++<60)requestAnimationFrame(draw);else ctx.clearRect(0,0,c.width,c.height)}
  draw();
}
window.confetti=confetti;

/* ── Mode toggle ──────────────────────────────────────────────────────── */
function setMode(m){
  mode=m;
  S('#discoverView').style.display=m==='discover'?'block':'none';
  S('#swipeView').classList.toggle('show',m==='swipe');
  SA('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===m));
  if(m==='swipe')initSwipe();
  if(m==='discover')filterAndRender();
}

/* ── Command palette ──────────────────────────────────────────────────── */
function openCmd(){S('#cmdBg').classList.add('open');S('#cmdInput').value='';S('#cmdInput').focus();cmdSearch('')}
function closeCmd(){S('#cmdBg').classList.remove('open')}
function cmdSearch(q){
  q=q.toLowerCase().trim();
  const list=q?E.filter(e=>(e.name||'').toLowerCase().includes(q)||(e.calendar_name||'').toLowerCase().includes(q)||(e.city||'').toLowerCase().includes(q)).slice(0,8):E.slice(0,8);
  S('#cmdResults').innerHTML=list.map(e=>`<div class="cmd-item" onclick="closeCmd();openModal('${esc(e.id)}')"><div><div class="ci-title">${esc(e.name)}</div><div class="ci-meta">${esc(fD(e.start_at))} &middot; ${esc(e.city||'?')}</div></div></div>`).join('');
}

/* ── Chips ─────────────────────────────────────────────────────────────── */
function buildChips(){
  const cities=new Map(),cats=new Map();
  E.forEach(e=>{cities.set(e.city||'TBD',(cities.get(e.city||'TBD')||0)+1);(e.categories||[]).forEach(c=>cats.set(c,(cats.get(c)||0)+1))});
  const pRow=S('#personChips'),people=new Set();
  E.forEach(e=>Object.keys(e.scores||{}).forEach(n=>people.add(n)));
  [...people].sort().forEach(p=>{
    const el=document.createElement('span');el.className='person-chip';el.textContent=p[0].toUpperCase()+p.slice(1);
    el.onclick=()=>{if(activePerson===p){activePerson=null;el.classList.remove('active');S('#sort').value='date'}else{activePerson=p;pRow.querySelectorAll('.person-chip').forEach(x=>x.classList.remove('active'));el.classList.add('active');S('#sort').value=p}if(mode==='discover')filterAndRender();else initSwipe()};
    pRow.appendChild(el);
  });
  const cRow=S('#cityChips');[...cities.entries()].sort((a,b)=>b[1]-a[1]).forEach(([c,n])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${c} (${n})`;el.onclick=()=>{cityF.has(c)?cityF.delete(c):cityF.add(c);el.classList.toggle('active');filterAndRender()};cRow.appendChild(el)});
  const tRow=S('#catChips');[...cats.entries()].sort((a,b)=>b[1]-a[1]).forEach(([c,n])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${c} (${n})`;el.onclick=()=>{catF.has(c)?catF.delete(c):catF.add(c);el.classList.toggle('active');filterAndRender()};tRow.appendChild(el)});
  const sRow=S('#statusChips');[['open','Open'],['waitlist','Waitlist'],['sold','Sold out']].forEach(([s,l])=>{const el=document.createElement('span');el.className='chip';el.textContent=`${l} (${E.filter(e=>st(e)===s).length})`;el.onclick=()=>{statusF.has(s)?statusF.delete(s):statusF.add(s);el.classList.toggle('active');filterAndRender()};sRow.appendChild(el)});
}

/* ── Keyboard ─────────────────────────────────────────────────────────── */
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  if(e.key==='/'){e.preventDefault();openCmd()}
  if(e.key==='Escape'){closeModal();closeCmd()}
  if(e.key==='s')setMode(mode==='discover'?'swipe':'discover');
  if(e.key==='1'){const chips=SA('.person-chip');if(chips[0])chips[0].click()}
  if(e.key==='2'){const chips=SA('.person-chip');if(chips[1])chips[1].click()}
});

/* ── Animated stats ───────────────────────────────────────────────────── */
function animateStats(){
  SA('.stat .n').forEach(el=>{const target=parseInt(el.dataset.val||el.textContent.replace(/,/g,''));let current=0;const step=()=>{current+=Math.ceil(target/30);if(current>=target){el.textContent=target.toLocaleString();return}el.textContent=current.toLocaleString();requestAnimationFrame(step)};el.textContent='0';requestAnimationFrame(step)});
}

/* ── Init ──────────────────────────────────────────────────────────────── */
window.closeModal=closeModal;window.openModal=openModal;window.undoSwipe=undoSwipe;
S('#modalBg').addEventListener('click',e=>{if(e.target.id==='modalBg')closeModal()});
S('#cmdBg').addEventListener('click',e=>{if(e.target.id==='cmdBg')closeCmd()});
S('#cmdInput').addEventListener('input',e=>cmdSearch(e.target.value));
S('#search').addEventListener('input',debounce(filterAndRender,150));
S('#sort').addEventListener('change',()=>{const v=S('#sort').value;if(v!=='date'&&v!=='rsvps'&&v!=='name'){activePerson=v;SA('.person-chip').forEach(x=>x.classList.toggle('active',x.textContent.toLowerCase()===v))}filterAndRender()});
SA('.mode-btn').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
buildChips();
setMode(isMobile?'swipe':'discover');
animateStats();
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
<canvas id="confetti"></canvas>
<div class="wrap">
  <header>
    <div class="header-row">
      <div>
        <h1>Luma Bay Area Events</h1>
        <div class="sub">{total} events &middot; updated {html.escape(fetched[:10])}</div>
      </div>
      <div class="mode-toggle">
        <button class="mode-btn active" data-mode="discover">Discover</button>
        <button class="mode-btn" data-mode="swipe">Swipe</button>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><div class="n" data-val="{total}">{total}</div><div class="l">Events</div></div>
      <div class="stat"><div class="n" data-val="{total_rsvps}">{total_rsvps:,}</div><div class="l">RSVPs</div></div>
      <div class="stat"><div class="n" data-val="{open_count}">{open_count}</div><div class="l">Open</div></div>
      <div class="stat"><div class="n" data-val="{sold_count}">{sold_count}</div><div class="l">Sold out</div></div>
    </div>
  </header>

  <div class="controls">
    <input type="search" id="search" placeholder="Search events..." onfocus="this.placeholder=''" onblur="this.placeholder='Search events...'"/>
    <label>Sort: <select id="sort">
      <option value="date">Date</option>
      <option value="rsvps">RSVPs</option>
      <option value="sumeet">Sumeet</option>
      <option value="ayushi">Ayushi</option>
      <option value="name">Name</option>
    </select></label>
    <div class="person-chips" id="personChips"><span class="label">For:</span></div>
    <div class="chips" id="statusChips"></div>
    <div class="chips" id="catChips"></div>
    <div class="chips" id="cityChips"></div>
  </div>

  <!-- Discover mode -->
  <div id="discoverView">
    <div class="hero" id="hero"></div>
    <div class="count" id="count"></div>
    <div id="grid"></div>
  </div>

  <!-- Swipe mode -->
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

<!-- Modal -->
<div class="modal-bg" id="modalBg"><div id="modal"></div></div>

<!-- Command palette -->
<div class="cmd-bg" id="cmdBg">
  <div class="cmd-box">
    <input class="cmd-input" id="cmdInput" placeholder="Search events..." autocomplete="off"/>
    <div class="cmd-results" id="cmdResults"></div>
  </div>
</div>

<!-- Keyboard hints -->
<div class="kb-hint">
  <kbd>/</kbd> search &nbsp; <kbd>s</kbd> swipe &nbsp; <kbd>1</kbd><kbd>2</kbd> person
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
