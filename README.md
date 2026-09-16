# YMCA of Central Massachusetts — Per-Branch Calendars

Clean iCal feeds for **YMCA of Central Massachusetts** (Greendale, Central/Main St, Boroughs, Leominster, Montachusett, Tri-Community). Subscribe once — auto-updates daily.

## Add to your calendar

Deployed on Vercel — filtered via URL params, auto-updates. See [Filtering](#filtering-via-url-parameters) for `?category=`, `?class=`, etc.

| Branch | Subscribe URL (copy) |
|---|---|
| **Greendale** — 75 Shore Dr, Worcester | `https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics` |
| **Central** — 766 Main St, Worcester | `https://ymca-central-ma-calendars.vercel.app/calendars/central.ics` |
| Boroughs — Westborough | `https://ymca-central-ma-calendars.vercel.app/calendars/boroughs.ics` |
| Leominster | `https://ymca-central-ma-calendars.vercel.app/calendars/leominster.ics` |
| Montachusett — Fitchburg | `https://ymca-central-ma-calendars.vercel.app/calendars/montachusett.ics` |
| Tri-Community — Southbridge | `https://ymca-central-ma-calendars.vercel.app/calendars/tricommunity.ics` |
| All branches merged | `https://ymca-central-ma-calendars.vercel.app/calendars/all_branches.ics` |

Filtered example: `https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise` — see [Filtering via URL Parameters](#filtering-via-url-parameters) for all options.

Static fallback (GitHub, no filtering): `https://raw.githubusercontent.com/besartbytyqi/ymca-central-ma-calendars/main/calendars/greendale.ics`

### Google Calendar
1. Copy a URL from the table above.
2. Open [Google Calendar](https://calendar.google.com) → left sidebar → **Other calendars `+` → From URL** → Paste → **Add calendar**.
3. Repeat for each branch you want. Re-color via `⋮ → Settings`.
4. Google re-fetches every 12–24h (daily GitHub Action updates the file at 9am UTC). For instant check: `Settings → Import & Export → Import` and upload the `.ics` file.

### Apple Calendar (macOS / iOS)
1. Copy a URL.
2. **macOS:** Calendar → **File → New Calendar Subscription** → Paste → Subscribe. Choose auto-refresh `Every day`.
3. **iPhone/iPad:** Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar → Paste → Next → Save.
4. Keep Greendale and Central as separate subscriptions to toggle.

### Outlook (Web / Desktop)
1. Copy a URL.
2. **Outlook on the web:** Calendar → **Add calendar → Subscribe from web** → Paste → Import. Name it `YMCA Greendale`.
3. **Outlook Desktop (Windows/Mac):** Calendar → **Add Calendar → From Internet** → Paste → OK.
4. Outlook checks for updates automatically; you can also re-add the filtered URL variant for a focused view (e.g. `.../greendale.ics?category=Group%20Exercise`).

---

## Filtering via URL Parameters

> Works on the **dynamic server** (`https://ymca-central-ma-calendars.vercel.app`). Static `raw.githubusercontent` files are unfiltered snapshots; add `?category=...` only when using the server URL.

Events have `category`, `studio`, and `class_name`. Use the live discovery endpoint to see what's available:

```bash
curl "https://ymca-central-ma-calendars.vercel.app/api/categories?branch=greendale&days=7"
# → {"categories":[{"category":"Group Exercise","count":42},{"category":"Aquatics","count":42},...],
#     "studios":[{"studio":"Main Studio (Lower Level)","count":15},...]}
```

Sample 7-day counts: `Group Exercise` (42), `Aquatics` (42), `Basketball Court` (31), `Family` (9).

| Param | Example | Description |
|---|---|---|
| `category` / `categories` | `?category=Group%20Exercise` <br> `?categories=Group%20Exercise,Aquatics` | **Exact, case-insensitive**. OR across list. |
| `exclude_category` | `?exclude_category=Basketball%20Court` | Exclude categories. |
| `studio` / `studios` | `?studio=Spin%20Studio` | **Substring, case-insensitive**. `SMB` matches `SMB Studio (Main Level)`. |
| `exclude_studio` | `?exclude_studio=Hot%20Tub` | Exclude studios. |
| `class` / `q` | `?class=Yoga` | **Substring on class name**, case-insensitive. |
| `days` | `?days=14` | Days ahead (1-31, default 7). |
| `start` | `?start=2026-09-20` | Start date `YYYY-MM-DD` (default today ET). |

**Examples (use as Google/Apple/Outlook subscription URLs):**

```
# Only Group Exercise at Greendale (most popular)
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise
https://ymca-central-ma-calendars.vercel.app/calendars/central.ics?category=Group%20Exercise

# Only Yoga
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?class=Yoga

# Spin at Central
https://ymca-central-ma-calendars.vercel.app/calendars/central.ics?studio=Spin%20Studio

# Greendale Yoga in SMB Studio
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise&class=Yoga&studio=SMB

# All branches, no basketball
https://ymca-central-ma-calendars.vercel.app/calendars/all_branches.ics?exclude_category=Basketball%20Court

# Aquatics only, next 14 days
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Aquatics&days=14
```

Keep each filtered URL as a **separate** Google/Apple/Outlook calendar so you can toggle per branch and per interest.

---

## Development

_Technical details for contributors — below the user guide._

### How it works

GroupexPro JSON: `https://groupexpro.com/schedule/embed/json_schedule.php?schedule&format=json&a=1045&location=7023&start=...&end=...`

`location` = branch ID: `7021` Boroughs, `7022` Central, `7023` Greendale, `7024` Leominster, `7025` Montachusett, `7026` Tri-Community.

Parsed via `src/ymca_groupexpro.py` (`category`, `studio`, `class_name`, `description` + base64 decode), converted to iCal via `src/ymca_ical.py` with `UTC` `DTSTART:20260916T093000Z` for max Google/Apple/Outlook compatibility.

### Local setup

```bash
pip install -r requirements.txt  # requests, icalendar, fastapi, uvicorn

# Static generation (writes calendars/*.ics)
python scripts/crawl_ymca.py --branches greendale,central --days 7 --output calendars
python scripts/crawl_ymca.py --all --days 7 --only-classes --output calendars
python scripts/crawl_ymca.py --category "Group Exercise" --class Yoga --output calendars
python scripts/crawl_ymca.py --help  # all options

# Dynamic server with filtering
uvicorn api.app:app --reload --port 8000
# → http://localhost:8000/ (docs) and http://localhost:8000/calendars/greendale.ics?category=Group%20Exercise
# → http://localhost:8000/api/categories?branch=greendale
```

### Project layout

```
calendars/*.ics     — static snapshots (committed, updated daily by Action)
api/app.py          — FastAPI dynamic calendar server (URL-param filtering)
src/ymca_groupexpro.py — GroupexPro fetcher + filter_events()
src/ymca_ical.py    — iCal generation (UTC)
scripts/crawl_ymca.py — CLI for static generation
vercel.json         — Vercel deploy config
```

### Deploy the dynamic server

**Vercel (1 click):** `vercel --prod` in repo root or connect GitHub repo to Vercel dashboard. Env: none needed. Route: `api/index.py` → `api/app.py`.

**Other hosts:** Railway/Fly/Render auto-detect `requirements.txt` + `uvicorn api.app:app`.

### Daily auto-sync

`.github/workflows/sync.yml` runs daily 9am UTC: `python scripts/crawl_ymca.py --all --days 7 --only-classes --output calendars` and auto-commits. Change cron to `0 9 * * 1` for weekly.

### Prior Art

No existing public repo for **YMCA of Central Massachusetts / Worcester** was found. Closest generic is `open-y-subprojects/openy_daxko_gxp_syncer` (Drupal Open Y Daxko GroupExPro syncer). This repo is intentionally minimal.

### License

MIT
