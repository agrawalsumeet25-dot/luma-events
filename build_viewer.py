"""
build_viewer.py — Generate a self-contained HTML viewer for the Luma event dump.

Reads the latest output/luma_raw_*.json and writes output/viewer.html with all
event data embedded. The HTML has client-side search, filters (city, category,
status), and sort (date / RSVPs / name). Zero dependencies, opens by double-click.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

OUT_DIR = Path(__file__).parent / "output"


def prosemirror_to_html(node: dict) -> str:
    """Convert Luma's description_mirror ProseMirror JSON tree to HTML."""
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

    if ntype == "doc":
        return children
    if ntype == "paragraph":
        return f"<p>{children}</p>" if children else "<p></p>"
    if ntype == "heading":
        level = max(1, min(6, attrs.get("level") or 2))
        return f"<h{level}>{children}</h{level}>"
    if ntype == "hard_break":
        return "<br/>"
    if ntype == "bullet_list":
        return f"<ul>{children}</ul>"
    if ntype == "ordered_list":
        return f"<ol>{children}</ol>"
    if ntype == "list_item":
        return f"<li>{children}</li>"
    if ntype == "horizontal_rule":
        return "<hr/>"
    if ntype == "blockquote":
        return f"<blockquote>{children}</blockquote>"
    if ntype == "image":
        src = html.escape(attrs.get("src") or "")
        alt = html.escape(attrs.get("alt") or "")
        return f'<img src="{src}" alt="{alt}" loading="lazy"/>'
    if ntype == "code_block":
        return f"<pre><code>{children}</code></pre>"
    return children  # unknown node — render children only


def latest_dump() -> Path:
    for pattern in ["luma_scored_*.json", "luma_raw_recursive_*_merged.json",
                    "luma_raw_recursive_*.json", "luma_raw_*.json"]:
        dumps = sorted(OUT_DIR.glob(pattern))
        if dumps:
            return dumps[-1]
    raise SystemExit("No event data found. Run scrape_luma.py first.")


def slim(records: list[dict]) -> list[dict]:
    """Strip the raw dump down to the fields the viewer actually needs."""
    out: list[dict] = []
    for r in records:
        ev = (r.get("list_entry") or {}).get("event") or {}
        det = r.get("detail") or {}
        det_ev = det.get("event") or {}
        cal = det.get("calendar") or {}
        geo = ev.get("geo_address_info") or det_ev.get("geo_address_info") or {}
        ti = det.get("ticket_info") or {}
        hosts = det.get("hosts") or []
        cats = [c.get("name") for c in (det.get("categories") or []) if c.get("name")]
        guests = det.get("featured_guests") or []

        url_slug = ev.get("url") or det_ev.get("url") or ""
        rsvp_url = f"https://lu.ma/{url_slug}" if url_slug else ""

        # Compute derived tags from text (Luma has no Design/UX category)
        text_blob = " ".join([
            ev.get("name") or "",
            det_ev.get("name") or "",
            cal.get("name") or "",
            (det.get("event") or {}).get("description") or "",
        ]).lower()
        derived_tags: list[str] = []
        if any(t in text_blob for t in [
            "design", "ux ", "ui ", "ux/", "ui/", "/ux", "/ui",
            "figma", "framer", "sketch app", "prototype", "wireframe",
            "design system", "product designer", "user experience",
            "user interface", "interaction design",
        ]):
            derived_tags.append("Design")
        if any(t in text_blob for t in [
            " ai ", "a.i.", "agent", "llm", "ml ", "machine learning",
            "claude", "openai", "anthropic", "gpt", "gemini",
            "neural", "transformer", "rag ", "vector db",
        ]):
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
            "lat": (ev.get("coordinate") or {}).get("latitude"),
            "lng": (ev.get("coordinate") or {}).get("longitude"),
            "cover_url": ev.get("cover_url") or "",
            "tint": det.get("tint_color") or "#7c3aed",
            "calendar_name": cal.get("name") or "",
            "calendar_avatar": cal.get("avatar_url") or "",
            "hosts": [{"name": h.get("name"), "avatar": h.get("avatar_url")} for h in hosts],
            "guest_count": det.get("guest_count", 0) or 0,
            "ticket_count": det.get("ticket_count", 0) or 0,
            "categories": cats + derived_tags,
            "derived_tags": derived_tags,
            "description": det.get("event", {}).get("description") or "",
            "description_html": prosemirror_to_html(
                det.get("description_mirror") or {}
            ),
            "registration_availability": det.get("registration_availability"),
            "sold_out": det.get("sold_out", False),
            "waitlist_active": det.get("waitlist_active", False),
            "is_paid": (ti.get("price_cents") or 0) > 0,
            "price_cents": ti.get("price_cents") or 0,
            "featured_guests": [
                {"name": g.get("name"), "avatar": g.get("avatar_url")}
                for g in guests
            ][:8],
            "url": rsvp_url,
            "scores": r.get("scores") or {},
        })
    return out


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html { color-scheme: dark; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0a0a0f;
  color: #e8e8ec;
  line-height: 1.5;
  min-height: 100vh;
}
.wrap { max-width: 1400px; margin: 0 auto; padding: 24px; }
header { margin-bottom: 24px; }
h1 {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #ff6519, #ff9b6b, #ffd000);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}
.sub { color: #888894; font-size: 14px; }
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin: 20px 0;
}
.stat {
  background: #15151c;
  border: 1px solid #25252e;
  border-radius: 10px;
  padding: 12px 16px;
}
.stat .n { font-size: 24px; font-weight: 700; color: #fff; }
.stat .l { font-size: 11px; color: #888894; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 24px 0;
  padding: 16px;
  background: #15151c;
  border: 1px solid #25252e;
  border-radius: 12px;
}
.controls input, .controls select {
  background: #0a0a0f;
  color: #e8e8ec;
  border: 1px solid #25252e;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  font-family: inherit;
}
.controls input[type=search] { flex: 1; min-width: 200px; }
.controls label { font-size: 13px; color: #888894; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; width: 100%; }
.chip {
  background: #1f1f28;
  color: #b8b8c4;
  border: 1px solid #2a2a35;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}
.chip:hover { background: #2a2a35; color: #fff; }
.chip.active { background: #ff6519; color: #fff; border-color: #ff6519; }
.count {
  margin-bottom: 16px;
  color: #888894;
  font-size: 13px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}
.card {
  background: #15151c;
  border: 1px solid #25252e;
  border-radius: 14px;
  overflow: hidden;
  transition: transform 0.15s, border-color 0.15s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}
.card:hover { transform: translateY(-2px); border-color: #3a3a48; }
.score-badge {
  position: absolute; top: 10px; left: 10px;
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #fff; z-index: 1;
  backdrop-filter: blur(6px);
}
.score-badge.high { background: rgba(34, 197, 94, 0.85); }
.score-badge.mid  { background: rgba(234, 179, 8, 0.85); }
.score-badge.low  { background: rgba(100, 100, 110, 0.7); }
.score-badge.hidden { display: none; }
.person-chips { display: flex; gap: 6px; align-items: center; }
.person-chips .label { font-size: 12px; color: #888894; margin-right: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.person-chip {
  background: #1f1f28; color: #b8b8c4; border: 1px solid #2a2a35;
  border-radius: 999px; padding: 4px 14px; font-size: 13px; font-weight: 600;
  cursor: pointer; user-select: none; transition: all 0.15s;
}
.person-chip:hover { background: #2a2a35; color: #fff; }
.person-chip.active { background: #7c3aed; color: #fff; border-color: #7c3aed; }
.modal-scores {
  display: flex; gap: 16px; margin: 12px 0;
  padding: 12px; background: #1a1a22; border-radius: 10px;
}
.modal-score-item { flex: 1; }
.modal-score-item .name { font-size: 11px; color: #888894; text-transform: uppercase; letter-spacing: 0.05em; }
.modal-score-item .val { font-size: 22px; font-weight: 700; }
.modal-score-item .val.high { color: #22c55e; }
.modal-score-item .val.mid  { color: #eab308; }
.modal-score-item .val.low  { color: #666; }
.modal-score-item .why { font-size: 12px; color: #b8b8c4; margin-top: 2px; }
.cover {
  height: 160px;
  background-size: cover;
  background-position: center;
  background-color: #1f1f28;
  position: relative;
}
.badges {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
.badge {
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(6px);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge.sold { background: rgba(220, 38, 38, 0.85); }
.badge.waitlist { background: rgba(234, 88, 12, 0.85); }
.badge.open { background: rgba(34, 197, 94, 0.85); }
.body { padding: 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.title { font-size: 16px; font-weight: 600; color: #fff; line-height: 1.3; }
.meta { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: #b8b8c4; }
.meta .row { display: flex; align-items: center; gap: 6px; }
.icon { width: 14px; height: 14px; opacity: 0.6; flex-shrink: 0; }
.host {
  display: flex; align-items: center; gap: 8px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #25252e;
  font-size: 12px;
  color: #888894;
}
.host img { width: 22px; height: 22px; border-radius: 50%; }
.cats { display: flex; flex-wrap: wrap; gap: 4px; }
.cat {
  background: #1f1f28;
  color: #b8b8c4;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.rsvp-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}
.rsvp-count { color: #fff; font-weight: 600; }
.rsvp-count span { color: #888894; font-weight: 400; }

/* Modal */
.modal-bg {
  display: none;
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(8px);
  z-index: 100;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 20px;
  overflow-y: auto;
}
.modal-bg.open { display: flex; }
.modal {
  background: #15151c;
  border: 1px solid #25252e;
  border-radius: 16px;
  max-width: 680px;
  width: 100%;
  overflow: hidden;
}
.modal .cover { height: 240px; }
.modal-body { padding: 24px; }
.modal h2 { font-size: 24px; margin-bottom: 12px; color: #fff; }
.modal .meta { font-size: 14px; margin-bottom: 16px; }
.modal .desc {
  color: #d0d0dc;
  font-size: 14px;
  line-height: 1.6;
  margin: 16px 0;
  max-height: 400px;
  overflow-y: auto;
}
.modal .desc p { margin-bottom: 8px; }
.modal .desc a { color: #ff9b6b; }
.modal .desc img { max-width: 100%; border-radius: 8px; margin: 8px 0; }
.modal .actions { display: flex; gap: 12px; margin-top: 16px; }
.btn {
  display: inline-block;
  background: #ff6519;
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: background 0.15s;
}
.btn:hover { background: #ff7a36; }
.btn.ghost { background: transparent; border: 1px solid #25252e; color: #b8b8c4; }
.btn.ghost:hover { background: #1f1f28; color: #fff; }
.guests { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.guests img { width: 28px; height: 28px; border-radius: 50%; border: 2px solid #15151c; margin-left: -6px; }
.close {
  position: absolute; top: 16px; right: 16px;
  background: rgba(0,0,0,0.7); color: #fff;
  width: 32px; height: 32px;
  border-radius: 50%; border: none;
  cursor: pointer; font-size: 18px;
  z-index: 1;
}
.modal-wrap { position: relative; width: 100%; max-width: 680px; }
"""


JS = r"""
const EVENTS = window.__EVENTS__;
const $ = (s) => document.querySelector(s);
const grid = $('#grid');
const count = $('#count');
const search = $('#search');
const sortSel = $('#sort');
const cityFilter = new Set();
const catFilter = new Set();
const statusFilter = new Set();
let activePerson = null; // 'sumeet' | 'ayushi' | null

const fmtDate = (s) => {
  if (!s) return '?';
  const d = new Date(s);
  return d.toLocaleString('en-US', { weekday:'short', month:'short', day:'numeric', hour:'numeric', minute:'2-digit' });
};

const status = (e) => {
  if (e.sold_out) return 'sold';
  if (e.waitlist_active) return 'waitlist';
  return 'open';
};

const statusLabel = (s) => ({sold:'Sold out', waitlist:'Waitlist', open:'Open'}[s]);

const scoreClass = (n) => n >= 80 ? 'high' : n >= 50 ? 'mid' : 'low';
const getScore = (e, person) => ((e.scores||{})[person]||{}).score || 0;

function buildCard(e) {
  const stat = status(e);
  const cats = (e.categories||[]).map(c => `<span class="cat">${escapeHtml(c)}</span>`).join('');
  const cover = e.cover_url
    ? `style="background-image:url('${escapeAttr(e.cover_url)}'); background-color: ${escapeAttr(e.tint)};"`
    : `style="background-color: ${escapeAttr(e.tint)};"`;
  const hostName = e.calendar_name || (e.hosts[0]||{}).name || '';
  const hostAvatar = e.calendar_avatar || (e.hosts[0]||{}).avatar || '';
  const sc = activePerson ? getScore(e, activePerson) : 0;
  const scoreBadge = activePerson
    ? `<div class="score-badge ${scoreClass(sc)}">${sc}</div>`
    : '';
  return `
    <div class="card" data-id="${escapeAttr(e.id)}">
      <div class="cover" ${cover}>
        ${scoreBadge}
        <div class="badges">
          <span class="badge ${stat}">${statusLabel(stat)}</span>
        </div>
      </div>
      <div class="body">
        <div class="title">${escapeHtml(e.name||'?')}</div>
        <div class="meta">
          <div class="row">${iconCal()} ${escapeHtml(fmtDate(e.start_at))}</div>
          <div class="row">${iconPin()} ${escapeHtml(e.venue || e.city || (e.location_type==='online'?'Online':'?'))}${e.city && e.venue ? ', ' + escapeHtml(e.city) : ''}</div>
        </div>
        <div class="cats">${cats}</div>
        <div class="host">
          ${hostAvatar ? `<img src="${escapeAttr(hostAvatar)}" alt=""/>` : ''}
          <span>by ${escapeHtml(hostName)}</span>
        </div>
        <div class="rsvp-strip">
          <span class="rsvp-count">${e.guest_count.toLocaleString()} <span>RSVPs</span></span>
          ${activePerson ? `<span class="rsvp-count" style="color:${sc>=80?'#22c55e':sc>=50?'#eab308':'#666'}">${sc}</span>` : ''}
        </div>
      </div>
    </div>`;
}

function iconCal(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'}
function iconPin(){return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>'}

function escapeHtml(s){
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s){ return escapeHtml(s); }

function filterAndSort() {
  let list = EVENTS.slice();
  const q = (search.value||'').toLowerCase().trim();
  if (q) {
    list = list.filter(e =>
      (e.name||'').toLowerCase().includes(q) ||
      (e.description||'').toLowerCase().includes(q) ||
      (e.calendar_name||'').toLowerCase().includes(q) ||
      (e.city||'').toLowerCase().includes(q));
  }
  if (cityFilter.size) list = list.filter(e => cityFilter.has(e.city || 'TBD'));
  if (catFilter.size)  list = list.filter(e => (e.categories||[]).some(c => catFilter.has(c)));
  if (statusFilter.size) list = list.filter(e => statusFilter.has(status(e)));

  const s = sortSel.value;
  if (s === 'date') list.sort((a,b) => (a.start_at||'').localeCompare(b.start_at||''));
  else if (s === 'rsvps') list.sort((a,b) => (b.guest_count||0) - (a.guest_count||0));
  else if (s === 'name') list.sort((a,b) => (a.name||'').localeCompare(b.name||''));
  else if (s === 'sumeet') list.sort((a,b) => getScore(b,'sumeet') - getScore(a,'sumeet'));
  else if (s === 'ayushi') list.sort((a,b) => getScore(b,'ayushi') - getScore(a,'ayushi'));

  grid.innerHTML = list.map(buildCard).join('');
  count.textContent = `${list.length} of ${EVENTS.length} events`;
  attachCardHandlers();
}

function attachCardHandlers() {
  document.querySelectorAll('.card').forEach(c => {
    c.addEventListener('click', () => openModal(c.dataset.id));
  });
}

function buildScoresHtml(e) {
  const scores = e.scores || {};
  const names = Object.keys(scores);
  if (!names.length) return '';
  return `<div class="modal-scores">${names.map(n => {
    const s = scores[n] || {};
    const sc = s.score || 0;
    return `<div class="modal-score-item">
      <div class="name">${escapeHtml(n)}</div>
      <div class="val ${scoreClass(sc)}">${sc}</div>
      <div class="why">${escapeHtml(s.reason || '')}</div>
    </div>`;
  }).join('')}</div>`;
}

function openModal(id) {
  const e = EVENTS.find(x => x.id === id);
  if (!e) return;
  const stat = status(e);
  const cover = e.cover_url
    ? `style="background-image:url('${escapeAttr(e.cover_url)}'); background-color: ${escapeAttr(e.tint)};"`
    : `style="background-color: ${escapeAttr(e.tint)};"`;
  const guests = (e.featured_guests||[]).map(g =>
    `<img src="${escapeAttr(g.avatar||'')}" title="${escapeAttr(g.name||'')}" alt="${escapeAttr(g.name||'')}"/>`
  ).join('');
  const desc = e.description_html || (e.description ? `<p>${escapeHtml(e.description)}</p>` : '<p>No description.</p>');
  $('#modal').innerHTML = `
    <div class="modal-wrap">
      <button class="close" onclick="closeModal()">&times;</button>
      <div class="modal">
        <div class="cover" ${cover}>
          <div class="badges"><span class="badge ${stat}">${statusLabel(stat)}</span></div>
        </div>
        <div class="modal-body">
          <h2>${escapeHtml(e.name||'?')}</h2>
          <div class="meta">
            <div class="row">${iconCal()} ${escapeHtml(fmtDate(e.start_at))}</div>
            <div class="row">${iconPin()} ${escapeHtml(e.full_address || e.venue || e.city || (e.location_type==='online'?'Online':''))}</div>
          </div>
          ${buildScoresHtml(e)}
          ${guests ? `<div class="guests">${guests}</div>` : ''}
          <div class="desc">${desc}</div>
          <div class="actions">
            <a class="btn" href="${escapeAttr(e.url)}" target="_blank" rel="noopener">RSVP on Luma</a>
            <button class="btn ghost" onclick="closeModal()">Close</button>
          </div>
        </div>
      </div>
    </div>`;
  $('#modalBg').classList.add('open');
}
function closeModal() { $('#modalBg').classList.remove('open'); }

function buildChips() {
  const cities = new Map(); const cats = new Map();
  for (const e of EVENTS) {
    const c = e.city || 'TBD';
    cities.set(c, (cities.get(c)||0)+1);
    for (const cat of (e.categories||[])) {
      cats.set(cat, (cats.get(cat)||0)+1);
    }
  }
  // Person chips
  const personRow = $('#personChips');
  const people = new Set();
  for (const e of EVENTS) {
    for (const n of Object.keys(e.scores||{})) people.add(n);
  }
  for (const p of [...people].sort()) {
    const el = document.createElement('span');
    el.className = 'person-chip';
    el.textContent = p.charAt(0).toUpperCase() + p.slice(1);
    el.onclick = () => {
      if (activePerson === p) {
        activePerson = null;
        el.classList.remove('active');
        sortSel.value = 'date';
      } else {
        activePerson = p;
        personRow.querySelectorAll('.person-chip').forEach(x => x.classList.remove('active'));
        el.classList.add('active');
        sortSel.value = p;
      }
      filterAndSort();
    };
    personRow.appendChild(el);
  }

  const cityRow = $('#cityChips');
  [...cities.entries()].sort((a,b)=>b[1]-a[1]).forEach(([c,n]) => {
    const el = document.createElement('span');
    el.className = 'chip';
    el.textContent = `${c} (${n})`;
    el.onclick = () => { cityFilter.has(c) ? cityFilter.delete(c) : cityFilter.add(c); el.classList.toggle('active'); filterAndSort(); };
    cityRow.appendChild(el);
  });
  const catRow = $('#catChips');
  [...cats.entries()].sort((a,b)=>b[1]-a[1]).forEach(([c,n]) => {
    const el = document.createElement('span');
    el.className = 'chip';
    el.textContent = `${c} (${n})`;
    el.onclick = () => { catFilter.has(c) ? catFilter.delete(c) : catFilter.add(c); el.classList.toggle('active'); filterAndSort(); };
    catRow.appendChild(el);
  });
  const statusRow = $('#statusChips');
  for (const [s, label] of [['open','Open'],['waitlist','Waitlist'],['sold','Sold out']]) {
    const el = document.createElement('span');
    el.className = 'chip';
    const n = EVENTS.filter(e => status(e) === s).length;
    el.textContent = `${label} (${n})`;
    el.onclick = () => { statusFilter.has(s) ? statusFilter.delete(s) : statusFilter.add(s); el.classList.toggle('active'); filterAndSort(); };
    statusRow.appendChild(el);
  }
}

window.closeModal = closeModal;
document.getElementById('modalBg').addEventListener('click', (e) => { if (e.target.id === 'modalBg') closeModal(); });
search.addEventListener('input', filterAndSort);
sortSel.addEventListener('change', () => {
  const v = sortSel.value;
  if (v === 'sumeet' || v === 'ayushi') {
    activePerson = v;
    document.querySelectorAll('.person-chip').forEach(x => x.classList.toggle('active', x.textContent.toLowerCase() === v));
  }
  filterAndSort();
});
buildChips();
filterAndSort();
"""


def build_html(data: dict, slimmed: list[dict]) -> str:
    fetched = data.get("fetched_at", "")
    total = data.get("count", len(slimmed))
    total_rsvps = sum(e.get("guest_count", 0) or 0 for e in slimmed)
    open_count = sum(1 for e in slimmed if not e.get("sold_out") and not e.get("waitlist_active"))
    sold_count = sum(1 for e in slimmed if e.get("sold_out"))
    starts = [e["start_at"] for e in slimmed if e.get("start_at")]
    earliest = min(starts)[:10] if starts else "?"
    latest = max(starts)[:10] if starts else "?"

    data_json = json.dumps(slimmed, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Luma Bay Area Events — {fetched}</title>
<style>{CSS}</style>
</head><body>
<div class="wrap">
  <header>
    <h1>Luma Bay Area Events</h1>
    <div class="sub">Fetched {html.escape(fetched)} &middot; {earliest} → {latest}</div>
    <div class="stats">
      <div class="stat"><div class="n">{total}</div><div class="l">Total events</div></div>
      <div class="stat"><div class="n">{total_rsvps:,}</div><div class="l">Total RSVPs</div></div>
      <div class="stat"><div class="n">{open_count}</div><div class="l">Open registration</div></div>
      <div class="stat"><div class="n">{sold_count}</div><div class="l">Sold out</div></div>
    </div>
  </header>

  <div class="controls">
    <input type="search" id="search" placeholder="Search title, description, host, city…"/>
    <label>Sort:
      <select id="sort">
        <option value="date">Date (soonest)</option>
        <option value="rsvps">RSVPs (most)</option>
        <option value="sumeet">Sumeet's pick</option>
        <option value="ayushi">Ayushi's pick</option>
        <option value="name">Name (A-Z)</option>
      </select>
    </label>
    <div class="person-chips" id="personChips">
      <span class="label">For:</span>
    </div>
    <div class="chips" id="statusChips"></div>
    <div class="chips" id="catChips"></div>
    <div class="chips" id="cityChips"></div>
  </div>

  <div class="count" id="count"></div>
  <div class="grid" id="grid"></div>
</div>

<div class="modal-bg" id="modalBg"><div id="modal"></div></div>

<script type="application/json" id="data">{data_json}</script>
<script>window.__EVENTS__ = JSON.parse(document.getElementById('data').textContent);</script>
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
