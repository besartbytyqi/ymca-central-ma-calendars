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
    # Keep a simple fallback for curl, but the real page is the interactive generator
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YMCA Central MA — Calendar Builder</title>
<style>
  :root{--ymca-red:#ed1c24;--ymca-blue:#0060af;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#ffffff;--radius:16px}
  *{box-sizing:border-box} body{margin:0;font-family:ui-sans-system,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:var(--ink);background:var(--bg);line-height:1.5}
  header{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
  .wrap{max-width:1100px;margin:0 auto;padding:0 20px}
  .nav{display:flex;align-items:center;justify-content:space-between;padding:14px 0}
  .brand{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:.2px}
  .brand .dot{width:10px;height:10px;background:var(--ymca-red);border-radius:50%}
  .brand span{font-size:18px}
  .brand small{font-weight:600;color:var(--muted);margin-left:8px}
  .btn{appearance:none;border:1px solid var(--line);background:var(--card);padding:10px 14px;border-radius:999px;font-weight:600;cursor:pointer}
  .btn-primary{background:var(--ink);color:#fff;border-color:var(--ink)}
  .btn-ghost{background:transparent}
  .grid{display:grid;grid-template-columns:1.15fr .85fr;gap:24px;padding:28px 0}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
  .card h2{margin:4px 0 12px;font-size:18px}
  .muted{color:var(--muted);font-size:14px}
  .branches{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  @media(max-width:600px){.branches{grid-template-columns:1fr}}
  .branch{position:relative;border:1px solid var(--line);border-radius:12px;padding:12px 12px 10px;cursor:pointer;background:#fff}
  .branch.active{border-color:var(--ymca-blue);box-shadow:0 0 0 3px rgba(0,96,175,.12)}
  .branch input{position:absolute;opacity:0}
  .branch strong{display:block;font-size:14px}
  .branch span{font-size:12px;color:var(--muted)}
  .branch .addr{font-size:12px;color:#334155;margin-top:4px}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  label{font-size:13px;font-weight:600;color:#334155}
  select,input[type="text"],input[type="number"],input[type="date"]{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:#fff;font-size:14px}
  .field{flex:1;min-width:140px}
  .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
  .chip{font-size:12px;border:1px solid var(--line);background:#fff;padding:6px 10px;border-radius:999px;cursor:pointer}
  .chip.active{background:var(--ink);color:#fff;border-color:var(--ink)}
  .urlbox{display:flex;gap:10px;align-items:stretch;margin-top:12px}
  .urlbox code{flex:1;overflow:auto;white-space:nowrap;background:#0f172a;color:#e2e8f0;padding:12px 14px;border-radius:12px;font-size:13px}
  .preview{font-size:13px;color:var(--muted);margin-top:8px}
  .steps{counter-reset:step}
  .step{display:flex;gap:12px;margin:14px 0}
  .step i{counter-increment:step;content:counter(step);width:28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;display:grid;place-items:center;font-style:normal;font-weight:800;font-size:13px;flex:none;margin-top:2px}
  .step i::before{content:counter(step)}
  .kicker{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ymca-red);font-weight:800}
  h1{font-size:32px;line-height:1.15;margin:6px 0 8px;letter-spacing:-.02em}
  .hero{padding:18px 0 6px}
  .hero p{color:#334155;max-width:60ch}
  .badge{display:inline-flex;gap:6px;align-items:center;font-size:12px;font-weight:700;color:var(--ymca-blue);background:rgba(0,96,175,.08);border:1px solid rgba(0,96,175,.15);padding:6px 10px;border-radius:999px}
  .foot{padding:24px 0;color:var(--muted);font-size:13px}
  a{color:var(--ymca-blue);text-decoration:none} a:hover{text-decoration:underline}
</style>
</head>
<body>
<header>
  <div class="wrap nav">
    <div class="brand"><span class="dot"></span><span>YMCA Central MA</span> <small>Calendar Builder</small></div>
    <div class="row">
      <a class="btn btn-ghost" href="https://github.com/besartbytyqi/ymca-central-ma-calendars" target="_blank">GitHub</a>
      <a class="btn btn-primary" href="#generate">Generate URL</a>
    </div>
  </div>
</header>

<div class="wrap hero">
  <div class="badge">GroupexPro • a=1045 • live • filtered via URL params</div>
  <h1>Add YMCA classes to Google, Outlook & Apple in one click</h1>
  <p>Pick your branch(es), filter by what you actually do, and subscribe. Each branch stays <em>separate</em> so you can toggle Greendale vs Central. Auto-updates daily.</p>
</div>

<div class="wrap grid" id="generate">
  <!-- LEFT: Builder -->
  <div class="card">
    <h2>1 — Pick branch</h2>
    <div class="branches" id="branches"></div>
    <p class="muted" style="margin-top:10px">Tip: keep Greendale + Central as separate calendars — you already do. Add others as needed.</p>

    <h2 style="margin-top:18px">2 — Filter what you care about</h2>
    <div class="row">
      <div class="field"><label>Category</label><select id="category" multiple><option value="">Any category</option></select></div>
      <div class="field"><label>Exclude category</label><select id="exclude_category" multiple><option value="">None</option></select></div>
    </div>
    <div class="row" style="margin-top:10px">
      <div class="field"><label>Studio</label><select id="studio" multiple><option value="">Any studio</option></select></div>
      <div class="field"><label>Exclude studio</label><select id="exclude_studio" multiple><option value="">None</option></select></div>
    </div>
    <div class="row" style="margin-top:10px">
      <div class="field"><label>Class (contains)</label><input id="q" type="text" placeholder="Yoga, HIIT, Zumba, Spin…"></div>
      <div class="field"><label>Days</label><input id="days" type="number" min="1" max="31" value="7"></div>
      <div class="field"><label>Start</label><input id="start" type="date"></div>
    </div>
    <div class="chips" id="quick">
      <button class="chip" data-preset="group">Group Exercise only</button>
      <button class="chip" data-preset="yoga">Yoga only</button>
      <button class="chip" data-preset="spin">Spin only</button>
      <button class="chip" data-preset="aquatics">Aquatics only</button>
      <button class="chip" data-preset="clear">Clear filters</button>
    </div>
    <p class="muted" id="counts" style="margin-top:10px"></p>
  </div>

  <!-- RIGHT: URL + Add -->
  <div class="card" style="position:sticky;top:76px;align-self:start">
    <h2>3 — Your calendar URL</h2>
    <div class="urlbox"><code id="url"></code><button class="btn btn-primary" id="copy">Copy</button></div>
    <div class="preview" id="preview">Choose a branch above.</div>
    <div class="row" style="margin-top:12px">
      <button class="btn btn-primary" id="addGoogle">Add to Google Calendar</button>
      <button class="btn" id="download">Download .ics</button>
    </div>
    <div class="row" style="margin-top:8px">
      <button class="btn" id="addOutlook">Add to Outlook</button>
      <button class="btn" id="addApple">Apple Calendar</button>
    </div>
    <div style="margin-top:14px;border-top:1px solid var(--line);padding-top:14px">
      <div class="kicker">How to add</div>
      <div class="step"><i></i><div><strong>Google:</strong> Copy URL → <a href="https://calendar.google.com" target="_blank">Google Calendar</a> → Other calendars <b>+</b> → <b>From URL</b> → Paste → Add. Re-color via ⋮.</div></div>
      <div class="step"><i></i><div><strong>Apple:</strong> Calendar → <b>File → New Calendar Subscription</b> → Paste → Subscribe (Every day). iPhone: Settings → Calendar → Add Subscribed Calendar.</div></div>
      <div class="step"><i></i><div><strong>Outlook:</strong> Calendar → <b>Add calendar → Subscribe from web</b> → Paste → Import. Desktop: <b>Add Calendar → From Internet</b>.</div></div>
      <p class="muted">Google re-fetches every 12–24h. The URL <em>is</em> the filter — keep each branch separate.</p>
    </div>
    <div style="margin-top:14px" class="muted">Static fallback (no filter): <a id="staticLink" href="#">raw.githubusercontent.com/…/calendars/greendale.ics</a></div>
  </div>
</div>

<div class="wrap foot">
  <span>GroupexPro JSON → <code>a=1045</code> • location 7021 Boroughs, 7022 Central, 7023 Greendale, 7024 Leominster, 7025 Montachusett, 7026 Tri-Community • iCal UTC <code>DTSTART:20260916T093000Z</code> • <a href="https://github.com/besartbytyqi/ymca-central-ma-calendars">GitHub</a> • <a href="/api/categories?branch=greendale">/api/categories</a></span>
</div>

<script>
const BRANCHES = {
  greendale: {name:"Greendale Family Branch", addr:"75 Shore Dr, Worcester, MA 01605"},
  central: {name:"Central Community Branch", addr:"766 Main St, Worcester, MA 01610"},
  boroughs: {name:"Boroughs Family Branch", addr:"4 Valente Dr, Westborough, MA 01581"},
  leominster: {name:"Leominster Community Branch", addr:"108 Adams St, Leominster, MA 01453"},
  montachusett: {name:"Montachusett Community Branch", addr:"55 Wallace Ave, Fitchburg, MA 01420"},
  tricommunity: {name:"Tri-Community Family Branch", addr:"43 Everett St, Southbridge, MA 01550"},
};
let activeBranch = localStorage.getItem("ymca_branch") || "greendale";
const els = {
  branches: document.getElementById("branches"),
  category: document.getElementById("category"),
  exclude_category: document.getElementById("exclude_category"),
  studio: document.getElementById("studio"),
  exclude_studio: document.getElementById("exclude_studio"),
  q: document.getElementById("q"),
  days: document.getElementById("days"),
  start: document.getElementById("start"),
  url: document.getElementById("url"),
  preview: document.getElementById("preview"),
  counts: document.getElementById("counts"),
  staticLink: document.getElementById("staticLink"),
  copy: document.getElementById("copy"),
  addGoogle: document.getElementById("addGoogle"),
  addOutlook: document.getElementById("addOutlook"),
  addApple: document.getElementById("addApple"),
  download: document.getElementById("download"),
};

function renderBranches(){
  els.branches.innerHTML = Object.entries(BRANCHES).map(([k,v])=>`
    <label class="branch ${k===activeBranch?'active':''}" data-branch="${k}">
      <input type="radio" name="branch" value="${k}" ${k===activeBranch?'checked':''}>
      <strong>${v.name}</strong>
      <span>${k} • ${v.addr}</span>
    </label>
  `).join("");
  els.branches.querySelectorAll(".branch").forEach(el=>{
    el.addEventListener("click", ()=>{
      activeBranch = el.dataset.branch;
      localStorage.setItem("ymca_branch", activeBranch);
      renderBranches();
      loadCategories();
      update();
    });
  });
}

async function loadCategories(){
  const branch = activeBranch;
  els.counts.textContent = "Loading categories…";
  try{
    const r = await fetch(`/api/categories?branch=${branch}&days=${els.days.value||7}`);
    const j = await r.json();
    const cats = j.categories || [];
    const studs = j.studios || [];
    const catOpts = ['<option value="">Any category</option>'].concat(cats.map(c=>`<option value="${c.category}">${c.category} (${c.count})</option>`)).join("");
    const studOpts = ['<option value="">Any studio</option>'].concat(studs.map(s=>`<option value="${s.studio}">${s.studio} (${s.count})</option>`)).join("");
    els.category.innerHTML = catOpts;
    els.exclude_category.innerHTML = '<option value="">None</option>' + cats.map(c=>`<option value="${c.category}">${c.category}</option>`).join("");
    els.studio.innerHTML = studOpts;
    els.exclude_studio.innerHTML = '<option value="">None</option>' + studs.map(s=>`<option value="${s.studio}">${s.studio}</option>`).join("");
    els.counts.textContent = `${j.total} events total • ${cats.length} categories • ${studs.length} studios`;
  }catch(e){
    els.counts.textContent = "Could not load categories";
  }
}

function buildUrl(){
  const base = `${location.origin}/calendars/${activeBranch}.ics`;
  const params = new URLSearchParams();
  const selCats = Array.from(els.category.selectedOptions).map(o=>o.value).filter(v=>v);
  const selExCats = Array.from(els.exclude_category.selectedOptions).map(o=>o.value).filter(v=>v);
  const selStuds = Array.from(els.studio.selectedOptions).map(o=>o.value).filter(v=>v);
  const selExStuds = Array.from(els.exclude_studio.selectedOptions).map(o=>o.value).filter(v=>v);
  if(selCats.length) params.set("categories", selCats.join(","));
  if(selExCats.length) params.set("exclude_category", selExCats.join(","));
  if(selStuds.length) params.set("studios", selStuds.join(","));
  if(selExStuds.length) params.set("exclude_studio", selExStuds.join(","));
  if(els.q.value.trim()) params.set("class", els.q.value.trim());
  if(els.days.value && els.days.value!="7") params.set("days", els.days.value);
  if(els.start.value) params.set("start", els.start.value);
  const qs = params.toString();
  return qs ? base + "?" + qs : base;
}

function update(){
  const url = buildUrl();
  els.url.textContent = url;
  els.staticLink.href = `https://raw.githubusercontent.com/besartbytyqi/ymca-central-ma-calendars/main/calendars/${activeBranch}.ics`;
  els.staticLink.textContent = els.staticLink.href;
  const b = BRANCHES[activeBranch];
  const selCats = Array.from(els.category.selectedOptions).map(o=>o.value).filter(v=>v);
  const selStuds = Array.from(els.studio.selectedOptions).map(o=>o.value).filter(v=>v);
  els.preview.textContent = `${b.name} • ${b.addr} • ${els.days.value||7} days` + (selCats.length ? ` • ${selCats.join(', ')}`:"") + (els.q.value ? ` • class~${els.q.value}`:"") + (selStuds.length ? ` • ${selStuds.join(', ')}`:"");
  els.addGoogle.onclick = ()=> window.open(`https://calendar.google.com/calendar/render?cid=${encodeURIComponent(url)}`,"_blank");
  els.addOutlook.onclick = ()=> window.open(`https://outlook.live.com/calendar/0/addfromweb?url=${encodeURIComponent(url)}&name=${encodeURIComponent(b.name)}`,"_blank");
  els.addApple.onclick = ()=> window.open(url,"_blank");
  els.download.onclick = ()=> { const a=document.createElement("a"); a.href=url; a.download=`${activeBranch}.ics`; document.body.appendChild(a); a.click(); a.remove(); };
  history.replaceState(null,"", location.pathname + "?" + new URLSearchParams({branch:activeBranch}).toString());
}

document.getElementById("copy").addEventListener("click", async ()=>{
  const url = buildUrl();
  await navigator.clipboard.writeText(url);
  const btn = document.getElementById("copy");
  btn.textContent="Copied!"; setTimeout(()=>btn.textContent="Copy",1200);
});
document.getElementById("quick").addEventListener("click", (e)=>{
  const b = e.target.closest("[data-preset]");
  if(!b) return;
  const p = b.dataset.preset;
  if(p==="group"){ els.category.value="Group Exercise"; els.exclude_category.value=""; els.q.value=""; els.studio.value=""; }
  if(p==="yoga"){ els.category.value="Group Exercise"; els.q.value="Yoga"; }
  if(p==="spin"){ els.studio.value="Spin Studio"; els.category.value=""; els.q.value=""; }
  if(p==="aquatics"){ els.category.value="Aquatics"; els.q.value=""; }
  if(p==="clear"){ els.category.value=""; els.exclude_category.value=""; els.studio.value=""; els.exclude_studio.value=""; els.q.value=""; }
  update();
});
["change","input"].forEach(ev=>{
  ["category","exclude_category","studio","exclude_studio","q","days","start"].forEach(id=>{
    document.getElementById(id).addEventListener(ev, update);
  });
});

// init from URL ?branch=
const u = new URL(location.href);
if(u.searchParams.get("branch") && BRANCHES[u.searchParams.get("branch")]) activeBranch = u.searchParams.get("branch");
renderBranches();
loadCategories().then(update);
update();
</script>
</body>
</html>
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
