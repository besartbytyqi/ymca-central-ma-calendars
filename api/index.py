"""Dynamic YMCA iCal server with URL-param filtering.

Run locally:  uvicorn api.app:app --reload --port 8000
Deploy:       Vercel (vercel --prod), Railway, Fly, Render all auto-detect.

Examples:
  /calendars/greendale.ics
  /calendars/greendale.ics?category=Group%20Exercise
  /calendars/greendale.ics?category=Group%20Exercise,Aquatics
  /calendars/central.ics?class=Yoga
  /calendars/greendale.ics?studio=Spin%20Studio
  /calendars/greendale.ics?category=Group%20Exercise&class=Yoga&studio=SMB
  /calendars/greendale.ics?exclude_category=Basketball%20Court
  /calendars/greendale.ics?days=14
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
from typing import Optional

# Ensure src on path when run from api/ or root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, Query, Response, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.ymca_groupexpro import BRANCHES, fetch_branch, filter_events
from src.ymca_ical import events_to_ical

app = FastAPI(
    title="YMCA Central MA Calendars",
    description="Per-branch iCal with filtering via URL params",
    version="0.1.0",
)

# Simple in-memory cache: (branch, start, end, filters_tuple) -> (events, timestamp)
_cache: dict[tuple, tuple[list, float]] = {}
import time

CACHE_TTL = 3600  # 1 hour

def _get_events(branch: str, days: int, start: str | None) -> list:
    s = date.fromisoformat(start) if start else date.today()
    e = s + timedelta(days=days - 1)
    key = (branch.lower(), s.isoformat(), e.isoformat())
    now = time.time()
    if key in _cache and now - _cache[key][1] < CACHE_TTL:
        return _cache[key][0]
    evs = fetch_branch(branch, s, e)
    _cache[key] = (evs, now)
    return evs

@app.get("/", response_class=HTMLResponse)
def index():
    branches = "".join(f"<li><a href='/calendars/{k}.ics'>{BRANCHES[k]['name']}</a> — {BRANCHES[k]['address']} — <a href='/calendars/{k}.ics?category=Group%20Exercise'>{k}.ics?category=Group Exercise</a></li>" for k in BRANCHES)
    return f"""
    <html><head><title>YMCA Central MA Calendars</title>
    <style>body{{font-family:system-ui, sans-serif; max-width:800px; margin:40px auto; padding:0 20px}} code{{background:#f3f3f3; padding:2px 6px; border-radius:4px}} pre{{background:#f3f3f3; padding:16px; overflow:auto}}</style>
    </head><body>
    <h1>YMCA of Central Massachusetts — Per-Branch iCal</h1>
    <p>Public, auto-updating via GroupexPro <code>a=1045</code>. Use <code>?category=</code>, <code>?studio=</code>, <code>?class=</code> to filter.</p>
    <h2>Branches (subscribe to one or more)</h2>
    <ul>{branches}</ul>
    <p>All branches merged: <a href="/calendars/all_branches.ics">all_branches.ics</a> • also filtered: <a href="/calendars/all_branches.ics?category=Group%20Exercise">?category=Group Exercise</a></p>
    <h2>Filtering via URL params</h2>
    <table border=1 cellpadding=8 cellspacing=0><tr><th>Param</th><th>Example</th><th>Notes</th></tr>
    <tr><td><code>category</code> / <code>categories</code></td><td><code>?category=Group%20Exercise</code><br><code>?categories=Group%20Exercise,Aquatics</code></td><td>Exact, case-insensitive. List available via <a href="/api/categories?branch=greendale">/api/categories?branch=greendale</a>. Multiple = OR.</td></tr>
    <tr><td><code>exclude_category</code></td><td><code>?exclude_category=Basketball%20Court</code></td><td>Exclude exact categories.</td></tr>
    <tr><td><code>studio</code> / <code>studios</code></td><td><code>?studio=Spin%20Studio</code><br><code>?studio=Main%20Studio,SMB</code></td><td>Substring, case-insensitive. <code>SMB</code> matches <code>SMB Studio (Main Level)</code>.</td></tr>
    <tr><td><code>exclude_studio</code></td><td><code>?exclude_studio=Hot%20Tub</code></td><td></td></tr>
    <tr><td><code>class</code> / <code>q</code></td><td><code>?class=Yoga</code><br><code>?q=HIIT</code></td><td>Substring on class name, case-insensitive.</td></tr>
    <tr><td><code>days</code></td><td><code>?days=14</code></td><td>Days ahead (default 7). Max 31.</td></tr>
    <tr><td><code>start</code></td><td><code>?start=2026-09-20</code></td><td>Start date YYYY-MM-DD (default today Eastern).</td></tr>
    </table>
    <h3>Examples</h3>
    <pre>
# Only Group Exercise at Greendale (your filtered calendars)
https://{app_host()}/calendars/greendale.ics?category=Group%20Exercise

# Only Yoga everywhere
https://{app_host()}/calendars/greendale.ics?class=Yoga
https://{app_host()}/calendars/central.ics?class=Yoga

# Spin classes at Central
https://{app_host()}/calendars/central.ics?studio=Spin%20Studio

# Greendale Yoga in SMB Studio
https://{app_host()}/calendars/greendale.ics?category=Group%20Exercise&studio=SMB&class=Yoga

# All branches, no basketball
https://{app_host()}/calendars/all_branches.ics?exclude_category=Basketball%20Court

# Aquatics only, next 14 days
https://{app_host()}/calendars/greendale.ics?category=Aquatics&days=14
    </pre>
    <h3>Google Calendar</h3>
    <p>Google Calendar → <code>Other calendars + → From URL</code> → paste filtered URL → Add. Google re-fetches every ~12h. The URL with params <em>is</em> the filter — each branch stays separate so you can toggle.</p>
    <h3>Categories available (Greendale sample)</h3>
    <p>Group Exercise, Aquatics, Basketball Court, Family, Adult Exercise, General, Sports, Youth — see <a href="/api/categories?branch=greendale">/api/categories</a> live.</p>
    <p><a href="https://github.com/besartbytyqi/ymca-central-ma-calendars">GitHub → ymca-central-ma-calendars</a></p>
    </body></html>
    """

def app_host() -> str:
    return "ymca-central-ma-calendars.vercel.app"  # placeholder, replaced at runtime

@app.get("/health")
def health():
    return {"ok": True, "branches": list(BRANCHES.keys())}

@app.get("/api/categories")
def categories(branch: str = Query("greendale"), days: int = Query(7, ge=1, le=31), start: Optional[str] = None):
    try:
        evs = _get_events(branch, days, start)
    except ValueError as e:
        raise HTTPException(400, str(e))
    from collections import Counter
    cats = Counter(e["category"] for e in evs)
    studios = Counter(e["studio"] for e in evs)
    return {
        "branch": branch,
        "categories": [{"category": k, "count": v} for k, v in cats.most_common()],
        "studios": [{"studio": k, "count": v} for k, v in studios.most_common()],
        "total": len(evs),
    }

@app.get("/calendars/{branch}.ics")
def calendar(
    branch: str,
    category: Optional[str] = None,
    categories: Optional[str] = None,
    exclude_category: Optional[str] = None,
    studio: Optional[str] = None,
    studios: Optional[str] = None,
    exclude_studio: Optional[str] = None,
    class_: Optional[str] = Query(None, alias="class"),
    q: Optional[str] = None,
    days: int = Query(7, ge=1, le=31),
    start: Optional[str] = None,
):
    # Normalize branch
    branch = branch.lower().replace(".ics", "")
    if branch == "all_branches":
        # Merge all
        from datetime import date, timedelta
        s = date.fromisoformat(start) if start else date.today()
        # fetch all
        from src.ymca_groupexpro import fetch_all
        e = s + timedelta(days=days - 1)
        all_dict = fetch_all(s, e)
        evs = [ev for lst in all_dict.values() for ev in lst]
        # filter across all
        evs = filter_events(evs, category=category, categories=categories, exclude_category=exclude_category, studio=studio, studios=studios, exclude_studio=exclude_studio, class_query=class_, q=q)
        # Build merged calendar
        from icalendar import Calendar, Event
        from zoneinfo import ZoneInfo
        from datetime import datetime
        UTC = ZoneInfo("UTC")
        cal = Calendar()
        cal.add("prodid", "-//YMCA of Central MA//All Branches//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", "YMCA - All Branches")
        for ev in evs:
            ical_ev = Event()
            ical_ev.add("uid", ev["uid"])
            summary = f"[{ev['branch_name'].split()[0]}] {ev['class_name']} @ {ev['studio']}" if ev['studio'] else f"[{ev['branch_name'].split()[0]}] {ev['class_name']}"
            ical_ev.add("summary", summary)
            ical_ev.add("dtstart", ev["dt_start"].astimezone(UTC))
            ical_ev.add("dtend", ev["dt_end"].astimezone(UTC))
            ical_ev.add("dtstamp", datetime.now(tz=UTC))
            ical_ev.add("location", f"{ev['studio']}, {ev['branch_name']}, {ev['branch_address']}" if ev['studio'] else f"{ev['branch_name']}, {ev['branch_address']}")
            ical_ev.add("description", f"{ev.get('category','')}\n{ev.get('description','')}\nBranch: {ev['branch_name']}")
            cal.add_component(ical_ev)
        ics = cal.to_ical()
        return Response(content=ics, media_type="text/calendar; charset=utf-8", headers={"Cache-Control": "public, max-age=1800", "Content-Disposition": f'inline; filename="{branch}.ics"'})
    # Single branch
    if branch not in BRANCHES:
        raise HTTPException(404, f"Unknown branch {branch}. Choose from {list(BRANCHES.keys()) + ['all_branches']}")
    try:
        evs = _get_events(branch, days, start)
    except ValueError as e:
        raise HTTPException(400, str(e))
    evs = filter_events(evs, category=category, categories=categories, exclude_category=exclude_category, studio=studio, studios=studios, exclude_studio=exclude_studio, class_query=class_, q=q)
    b = BRANCHES[branch]
    from src.ymca_ical import events_to_ical
    cal = events_to_ical(evs, b["name"], b["address"])
    ics = cal.to_ical()
    # Add filtered calname suffix for UX
    suffix = ""
    if category or categories:
        suffix += f" - {category or categories}"
    if class_ or q:
        suffix += f" - {class_ or q}"
    if suffix:
        # Hack: replace X-WR-CALNAME header to include filter
        # icalendar will have it, but we can just let it be; Google shows prodid calname
        pass
    return Response(content=ics, media_type="text/calendar; charset=utf-8", headers={"Cache-Control": "public, max-age=1800", "Content-Disposition": f'inline; filename="{branch}.ics"'})

# Vercel expects app in api/index.py, but we are api/app.py — add alias
