# Scoring Improvements Spec

Based on a three-expert audit of 312 scored events and independent re-scoring of 20 representative events. This spec contains exact changes to implement.

---

## 1. PROMPT IMPROVEMENTS

### 1A. Replace the scoring criteria block in `build_prompt()` (lines 148-162)

**Current code (lines 148-162):**
```python
Score this event 0-100 for EACH person. Consider:
- How relevant is the topic to their specific interests and goals?
- Would attending help their current objectives?
- Is the event high-quality (reputable host, strong attendance, good speakers)?
- For job seekers: does the event offer networking with potential employers?

Scoring guide:
- 90-100: Must-attend. Directly aligned with core interests/goals.
- 70-89: Strongly recommended. Clearly relevant.
- 50-69: Worth considering. Tangentially relevant or good networking.
- 30-49: Low relevance. Only attend if nothing better.
- 0-29: Not relevant. Wrong domain or audience.

Respond ONLY with valid JSON, no other text:
{{{response_schema}}}
```

**New code:**
```python
Score this event 0-100 for EACH person. Weight these factors:

RELEVANCE (50% of score):
- How precisely does the topic match their CORE interests (not just same broad domain)?
- A "product design teardown" is different from a "general design meetup".
- A "vector database conference" is different from a "general AI event".
- Check the person's Low Interest list -- events matching those topics should score 5-20.

NETWORKING VALUE (25% of score):
- Who specifically will be there? Named speakers/guests with relevant titles matter.
- For job seekers: does the event offer face-time with hiring managers at target companies?
- Small/intimate events (under 30 people) with senior attendees score higher than large generic ones.
- Founder/startup social events can score 45-55 for job seekers IF the crowd includes potential employers.

QUALITY & LOGISTICS (15% of score):
- Reputable host? Strong attendance relative to capacity? Paid events signal higher commitment.
- Is it actually available (not sold out or waitlist-only)?
- Events restricted to students/educators score 15-20 points lower than equivalent open events.

FORMAT FIT (10% of score):
- In-person events in SF Bay Area score higher than virtual for networking.
- Hackathons/workshops score higher than passive talks for builders.

HARD RULES (apply after calculating base score):
- If the event is SOLD OUT or waitlist-only, cap the score at 40 max.
- If the event is virtual/online, reduce networking value component by half.
- If a featured guest or host is from one of the person's target companies, add +10.
- Do NOT apply a "minimum floor". Events completely outside someone's interests should score 3-10, not 15-25.
- Engineering-only events (agent infra, vector DBs, MLOps) with no design leaders = score 10-20 for designers, never 40-50.
- Pure design/UX events with no AI angle = score 5-15 for engineers, never above 20.

CALIBRATION INSTRUCTIONS:
- Use the FULL 0-100 scale. Do not round to multiples of 5.
- Use odd numbers, decimal-like precision: 37, 63, 81 are better than 35, 65, 80.
- The 90-100 range is for PERFECT matches: core topic + exceptional speakers + right format.
- Differentiate within buckets: if 5 events are "vaguely relevant networking", they should NOT all get the same score. Rank them relative to each other.

Scoring guide:
- 90-100: Must-attend. Core topic + exceptional speakers/networking + right format.
- 75-89: Strong recommendation. Clearly relevant topic with good networking potential.
- 60-74: Worth considering. Relevant but generic, or tangential topic with great people.
- 40-59: Marginal. Only tangentially related, or relevant topic but poor format/access.
- 20-39: Low relevance. Wrong audience or domain, weak networking.
- 0-19: Not relevant at all. Completely different field.

Respond ONLY with valid JSON, no other text:
{{{response_schema}}}
```

### 1B. Why this works

The current prompt has four flat bullet points with no weighting. The LLM randomly decides how much each factor matters per call, producing inconsistent scores. The new prompt:

1. Assigns explicit percentage weights (50/25/15/10) so relevance always dominates.
2. Adds HARD RULES that mechanically cap/boost scores for specific conditions.
3. Adds CALIBRATION INSTRUCTIONS that directly combat the quantization problem (62.8% of Ayushi scores are divisible by 5; 41 events at exactly 52).
4. Differentiates "wrong audience" events -- pure engineering events should score low for designers and vice versa, with explicit score ranges stated.

---

## 2. PROFILE UPDATES

### 2A. Additions to `profiles/ayushi.md`

Add under "Low Interest" section:

```markdown
- Engineering-only events (agent infra, vector DBs, inference optimization, MLOps, kernel engineering, CUDA) with no design leaders, product managers, or hiring opportunities in attendance -- score 10-20, not 40-50
- Events restricted to students/educators should be scored 15-20 points lower than equivalent open events, even if hosted by a target company (networking pool is wrong for job search)
```

Add under "Moderate Interest" section:

```markdown
- Founder/startup social events (running clubs, casual meetups) IF the crowd includes potential employers -- score 45-55 for the networking access even if the activity itself is not design-related
```

Strengthen the "Job Search Bonus" section by adding:

```markdown
- Exclusive/intimate dinners and small-group events (under 30 people) with design leaders from target companies should score 90-95. The smaller the group, the higher the networking value.
- Config-adjacent events (Figma Config side events, dinners, parties) with design leaders from target companies should score 85-95 depending on exclusivity.
```

### 2B. Additions to `profiles/sumeet.md`

Add under "Core Interests" section:

```markdown
- When an event title or description contains an EXACT keyword match from core interests (MCP, vector database, RAG, physical AI, robotics, Claude Code, agentic systems), the base score should be 85+. These are signal-rich events.
```

Strengthen "Low Interest" section by adding:

```markdown
- Pure design/UX events (Config parties, Figma gatherings, portfolio reviews, design teardowns) with no AI/engineering angle should score 5-15, never above 20. Do not add a "networking floor" -- the networking audience is wrong.
- Pure fitness, wellness, arts, spiritual events should score 3-10 at most.
```

Add a new section:

```markdown
## Scoring Calibration
- Do not apply a minimum floor. Events completely outside interests (wellness, arts, pure design) should score 3-10, not 15-25.
- The top of the scale (90-100) should be used for events that are a near-perfect match: core topic + strong speakers + right format + convenient location.
```

---

## 3. NEW SCORING SIGNALS

### 3A. Add event format/scale context to `event_summary()`

Replace line 121 (`lines.append(f"RSVPs: {det.get('guest_count', 0)}")`) with:

```python
# Event format and scale signals
ti = entry.get("ticket_info") or {}
capacity = entry.get("ticket_count") or 0
rsvps = det.get("guest_count", 0)
loc_type = ev.get("location_type") or det_ev.get("location_type") or "unknown"
is_free = ti.get("is_free", True)
price = ti.get("price")
sold_out = ti.get("is_sold_out", False)
reg = entry.get("registration_availability") or det.get("registration_availability") or "unknown"

scale = "small (intimate)" if capacity and capacity <= 30 else "medium" if capacity and capacity <= 150 else "large" if capacity else "unknown size"
lines.append(f"Format: {loc_type}, {scale}")
lines.append(f"RSVPs: {rsvps}" + (f" / {capacity} capacity" if capacity else ""))
lines.append(f"Price: {'Free' if is_free else f'${price}' if price else 'Paid (price unknown)'}")
if sold_out or reg == "waitlist":
    lines.append(f"Availability: {'SOLD OUT' if sold_out else 'Waitlist only'}")
```

### 3B. Surface featured guest bios

Replace lines 119-120 (`if guests: lines.append(...)`) with:

```python
if guests:
    guest_parts = []
    for g in guests[:5]:
        name = g.get("name") or "?"
        bio = (g.get("bio_short") or "").strip()
        if bio:
            guest_parts.append(f"{name} ({bio[:80]})")
        else:
            guest_parts.append(name)
    lines.append(f"Featured guests: {'; '.join(guest_parts)}")
```

### 3C. Add host credibility signal

After line 114 (`lines.append(f"Host calendar: {cal.get('name') or '?'}")`), add:

```python
cal_plan = cal.get("luma_plan") or "free"
cal_verified = bool(cal.get("verified_at"))
credibility_parts = []
if cal_verified:
    credibility_parts.append("Verified")
if cal_plan == "plus":
    credibility_parts.append("Premium account")
if credibility_parts:
    lines.append(f"Host credibility: {' + '.join(credibility_parts)}")
```

### 3D. Add one_to_one / small-group format flag

After the format/scale block, add:

```python
one_to_one = entry.get("one_to_one") or det.get("one_to_one")
if one_to_one:
    lines.append("Format note: 1:1 or small-group format")
```

### 3E. Summary of new fields surfaced

| Field | Source | What it tells the LLM |
|-------|--------|----------------------|
| `ticket_info.is_free` / `.price` | list_entry | Free vs. paid ($50+) = quality/commitment signal |
| `ticket_info.is_sold_out` | list_entry | Useless to recommend if sold out |
| `registration_availability` | list_entry/detail | Open vs. waitlist |
| `ticket_count` (capacity) | list_entry | 10-person dinner vs. 2900-person summit |
| `featured_guests[].bio_short` | detail | "Jeffrey Paine" -> "Managing Partner, Golden Gate Ventures" |
| `location_type` | event | In-person vs. virtual vs. hybrid |
| `calendar.luma_plan` | detail | Premium (plus) vs. free host account |
| `calendar.verified_at` | detail | Host verification status |
| `one_to_one` | list_entry/detail | 1:1 or small-group event format |

---

## 4. CALIBRATION FIX

### 4A. Problem statement

The scorer uses ~30 distinct values instead of 100. 62.8% of Ayushi scores are divisible by 5. 41 events (13.1%) all score exactly 52 for Ayushi -- a "vaguely relevant networking" dumping ground.

### 4B. Solution: Anti-quantization prompt instruction

Already included in Section 1A above. The key lines are:

```
CALIBRATION INSTRUCTIONS:
- Use the FULL 0-100 scale. Do not round to multiples of 5.
- Use odd numbers, decimal-like precision: 37, 63, 81 are better than 35, 65, 80.
- Differentiate within buckets: if 5 events are "vaguely relevant networking", they should NOT all get the same score. Rank them relative to each other.
```

### 4C. Validation metric

After implementing, re-score the full corpus with `--force` and measure:

```python
import json
from collections import Counter

data = json.load(open("output/luma_scored_LATEST.json"))
for person in ["ayushi", "sumeet"]:
    scores = [e["scores"][person]["score"] for e in data["events"]]
    unique = len(set(scores))
    div5 = sum(1 for s in scores if s % 5 == 0) / len(scores)
    top_freq = Counter(scores).most_common(1)[0]
    print(f"{person}: {unique} unique values (target: 60+), "
          f"{div5:.0%} div-by-5 (target: <30%), "
          f"most common: {top_freq[0]} appears {top_freq[1]}x (target: <15x)")
```

**Targets after fix:**
- Unique values: 60+ (currently 28/33)
- Divisible-by-5 percentage: <30% (currently 62.8%/51.9%)
- Most common single score: <15 occurrences (currently 42/29)

### 4D. Secondary calibration: post-hoc score spreading

If the prompt-level fix does not sufficiently spread scores, add a post-processing step in `score_one()` that adds small random jitter (+/- 2) to break ties. This is a last resort -- the prompt fix should handle it.

---

## 5. VALIDATION

### 5A. 20-event spot-check protocol

After every re-score, run this validation against the 20 benchmark events from the audit. Expected score ranges:

```
EVENT                                          SUMEET      AYUSHI
AI Engineer World's Fair Orientation           78-85       30-40
AI-tonomy Summit: Models and Agents            85-92       20-30
Agents & Bagels                                82-88       12-20
Vector Space Day SF                            88-95       8-15
Fork it Branch it Bop it                       78-84       8-15
AI Design Leaders Dinner @ Config 2026         18-25       90-96
design is a breakfast party at config          8-15        88-94
Off the Record: Design Edition                 10-18       92-98
Dark UX Academy                                5-12        72-80
Figma for Education Mixer                      3-8         40-50
MCP Connect SF                                 90-96       22-30
Japan x Global Tech Meetup                     22-30       60-70
Physical AI Superconnect 2026                  75-83       26-35
FDE Happy Hour                                 72-80       12-20
Make It Visible: Accessibility Meetup          8-14        50-58
AI Agents + Crypto Buildathon                  50-60       5-12
Embodied AI + Creative Machines                36-44       40-50
Circadian Rhythms, Sleep, Well-Being           3-8         5-10
Founders Running Club SF                       26-34       44-52
The Art & Joy of Clowning                      2-5         2-5
```

### 5B. Automated drift detection

Add to `score_events.py` main() after scoring completes:

```python
# Distribution health check
for name in profiles:
    scores_list = [r["scores"][name]["score"] for r in records if r.get("scores")]
    unique = len(set(scores_list))
    avg = sum(scores_list) / len(scores_list)
    div5_pct = sum(1 for s in scores_list if s % 5 == 0) / len(scores_list) * 100
    top_score, top_count = Counter(scores_list).most_common(1)[0]

    warnings = []
    if unique < 40:
        warnings.append(f"LOW DIVERSITY: only {unique} unique values (want 60+)")
    if div5_pct > 40:
        warnings.append(f"QUANTIZED: {div5_pct:.0f}% divisible by 5 (want <30%)")
    if top_count > 20:
        warnings.append(f"CLUSTERING: score {top_score} appears {top_count}x (want <15)")
    if avg < 25 or avg > 55:
        warnings.append(f"SKEWED: avg={avg:.0f} (want 30-50)")

    if warnings:
        print(f"\n  WARNING ({name}): {'; '.join(warnings)}")
```

### 5C. Correlation check

After scoring, verify that Ayushi and Sumeet scores are not too correlated:

```python
ayushi_scores = [r["scores"]["ayushi"]["score"] for r in records]
sumeet_scores = [r["scores"]["sumeet"]["score"] for r in records]
# Pearson correlation
n = len(ayushi_scores)
mean_a = sum(ayushi_scores) / n
mean_s = sum(sumeet_scores) / n
cov = sum((a - mean_a) * (s - mean_s) for a, s in zip(ayushi_scores, sumeet_scores)) / n
std_a = (sum((a - mean_a)**2 for a in ayushi_scores) / n) ** 0.5
std_s = (sum((s - mean_s)**2 for s in sumeet_scores) / n) ** 0.5
r = cov / (std_a * std_s) if std_a and std_s else 0
print(f"  Ayushi-Sumeet correlation: r={r:.3f} (want <0.40, currently 0.268)")
```

Target: r < 0.40 (currently 0.268, which is healthy -- ensure it stays low).

### 5D. Sold-out event check

After scoring, verify no sold-out events score above 40:

```python
for r in records:
    ti = (r.get("list_entry") or {}).get("ticket_info") or {}
    if ti.get("is_sold_out"):
        for name in profiles:
            score = r["scores"][name]["score"]
            if score > 40:
                ev_name = r["list_entry"]["event"].get("name", "?")[:50]
                print(f"  SOLD-OUT VIOLATION: {ev_name} scored {score} for {name} (cap=40)")
```

---

## 6. IMPLEMENTATION ORDER

1. **Profile updates** (Section 2) -- edit `profiles/ayushi.md` and `profiles/sumeet.md`
2. **Event summary signals** (Section 3) -- edit `event_summary()` in `score_events.py`
3. **Prompt rewrite** (Section 1) -- edit `build_prompt()` in `score_events.py`
4. **Validation hooks** (Section 5B-5D) -- add to `main()` in `score_events.py`
5. **Full re-score** -- run `python score_events.py --force`
6. **Spot-check** -- run validation against 20 benchmark events (Section 5A)

Estimated impact:
- Improvement 1 (weighted prompt): Eliminates flat-list ambiguity, forces consistent factor weighting
- Improvement 2 (profile sharpening): Fixes systematic Ayushi over-scoring on engineering events (+10-20 delta)
- Improvement 3 (new signals): Format/scale/price/availability data enables dinner-vs-conference differentiation
- Improvement 4 (anti-quantization): Expands effective scale from ~30 to 60+ unique values
- Improvement 5 (validation): Automated drift/clustering/sold-out detection prevents regression

---

## 7. FILES TO MODIFY

| File | Changes |
|------|---------|
| `C:/Users/suagraw/luma-events/score_events.py` | Lines 93-126 (event_summary), lines 128-162 (build_prompt), post-scoring validation in main() |
| `C:/Users/suagraw/luma-events/profiles/ayushi.md` | Add to Low Interest, Moderate Interest, Job Search Bonus sections |
| `C:/Users/suagraw/luma-events/profiles/sumeet.md` | Add to Core Interests, Low Interest, new Scoring Calibration section |
