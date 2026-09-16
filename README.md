# YMCA of Central Massachusetts — Per-Branch Calendars

Clean, daily auto-synced iCal feeds for **YMCA of Central Massachusetts** (GroupexPro `a=1045`).

- **Separate calendar per branch** (subscribe individually in Google/Apple Calendar)
- Daily auto-sync via GitHub Actions
- No brainer: URLs stay stable, Google re-fetches every 12h

## Branches

| Branch | Address | Location ID | Calendar |
|---|---|---|---|
| **Greendale** | 75 Shore Dr, Worcester, MA 01605 | 7023 | `calendars/greendale.ics` |
| **Central** | 766 Main St, Worcester, MA 01610 | 7022 | `calendars/central.ics` |
| Boroughs | 4 Valente Dr, Westborough | 7021 | `calendars/boroughs.ics` |
| Leominster | 108 Adams St, Leominster | 7024 | `calendars/leominster.ics` |
| Montachusett | 55 Wallace Ave, Fitchburg | 7025 | `calendars/montachusett.ics` |
| Tri-Community | 43 Everett St, Southbridge | 7026 | `calendars/tricommunity.ics` |
| All | — | — | `calendars/all_branches.ics` |

## Subscribe (Google Calendar)

**Static (daily snapshot, no filtering):**
1. Copy a raw URL, e.g. Greendale:
   ```
   https://raw.githubusercontent.com/besartbytyqi/ymca-central-ma-calendars/main/calendars/greendale.ics
   ```
2. Google Calendar → `Other calendars + → From URL` → Paste → `Add`
3. Repeat for Central

The static URLs update daily at 9am UTC via GitHub Actions. Google re-fetches automatically. For **instant check**: `Settings → Import & Export → Import` and upload the `.ics` file directly.

**Dynamic (filtered via URL params — recommended):**

Deploy the included FastAPI server (Vercel/Railway/Fly) or run locally:
```bash
pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
# then visit http://localhost:8000/
```

Use the hosted URL (e.g. `https://ymca-central-ma-calendars.vercel.app`) with params:

```
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise
```

Google Calendar → `From URL` → paste the **filtered** URL → Add. Each filtered URL is its own calendar — keep Greendale and Central separate as before, now with your interests dialed in.

## Filtering via URL Parameters

Every `/calendars/{branch}.ics` endpoint supports filtering. Events have `category`, `studio`, and `class_name` fields. Categories are the primary grouping GroupexPro uses.

**Discover categories/studios for any branch:**
```bash
curl "https://ymca-central-ma-calendars.vercel.app/api/categories?branch=greendale&days=7"
# or locally: curl "http://localhost:8000/api/categories?branch=greendale"
```
Response:
```json
{
  "branch": "greendale",
  "categories": [{"category": "Group Exercise", "count": 42}, {"category": "Aquatics", "count": 42}, ...],
  "studios": [{"studio": "Main Studio (Lower Level)", "count": 15}, ...]
}
```
Greendale sample (7 days): `Group Exercise` (42), `Aquatics` (42), `Basketball Court` (31), `Family` (9), `Adult Exercise`, `General`, `Sports`, `Youth`.

| Param | Example | Description |
|---|---|---|
| `category` / `categories` | `?category=Group%20Exercise` <br> `?categories=Group%20Exercise,Aquatics` | **Exact, case-insensitive**. OR across list. Use `/api/categories` to see values. Single category is most common. |
| `exclude_category` | `?exclude_category=Basketball%20Court` | Exclude exact categories (comma-separated). |
| `studio` / `studios` | `?studio=Spin%20Studio` <br> `?studios=Main%20Studio,SMB` | **Substring, case-insensitive**. `SMB` matches `SMB Studio (Main Level)`. |
| `exclude_studio` | `?exclude_studio=Hot%20Tub` | Exclude studios (substring). |
| `class` / `q` | `?class=Yoga` <br> `?q=HIIT` | **Substring on class name**, case-insensitive. `Yoga` matches `Wake Up Yoga w/ Walter`. |
| `days` | `?days=14` | Days ahead (1-31, default 7). |
| `start` | `?start=2026-09-20` | Start date `YYYY-MM-DD` (default today ET). |

**Examples (copy-paste as Google Calendar URLs):**

```bash
# Only Group Exercise at Greendale (your daily filtered calendars)
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise
https://ymca-central-ma-calendars.vercel.app/calendars/central.ics?category=Group%20Exercise

# Only Yoga everywhere
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?class=Yoga
https://ymca-central-ma-calendars.vercel.app/calendars/central.ics?class=Yoga

# Spin classes at Central
https://ymca-central-ma-calendars.vercel.app/calendars/central.ics?studio=Spin%20Studio

# Greendale Yoga in SMB Studio
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Group%20Exercise&class=Yoga&studio=SMB

# All branches, no basketball
https://ymca-central-ma-calendars.vercel.app/calendars/all_branches.ics?exclude_category=Basketball%20Court

# Aquatics only, next 14 days
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?category=Aquatics&days=14

# Multiple categories
https://ymca-central-ma-calendars.vercel.app/calendars/greendale.ics?categories=Group%20Exercise,Aquatics
```

Each filtered URL is **separate per branch** — keep them as separate Google Calendars so you can toggle, like you wanted for Greendale vs Central.

## CLI (static generation)

```bash
pip install requests icalendar

# Your two favorites (default) - 7 days
python scripts/crawl_ymca.py --branches greendale,central --days 7 --output calendars

# All 6 branches
python scripts/crawl_ymca.py --all --days 7 --output calendars

# Only Group Exercise (excludes lap lanes, reservations) — same as ?category=Group%20Exercise
python scripts/crawl_ymca.py --all --only-classes --output calendars

# Custom filters (mirror URL params)
python scripts/crawl_ymca.py --category "Group Exercise" --output calendars
python scripts/crawl_ymca.py --category "Group Exercise,Aquatics" --exclude-category "Basketball Court" --output calendars
python scripts/crawl_ymca.py --branches greendale --class Yoga --days 14 --output calendars
```

See `python scripts/crawl_ymca.py --help` for all options.

## How it works

GroupexPro JSON: `https://groupexpro.com/schedule/embed/json_schedule.php?schedule&format=json&a=1045&location=7023&start=...&end=...`

Parsed via `src/ymca_groupexpro.py`, converted to iCal with `src/ymca_ical.py` (UTC `DTSTART:20260916T093000Z` for max Google/Apple compatibility).

## Prior Art

No existing public repo specifically for **YMCA of Central Massachusetts / Worcester** was found. Closest generic is `open-y-subprojects/openy_daxko_gxp_syncer` (Drupal Open Y Daxko GroupExPro syncer) and various GroupexPro scrapers. This repo is intentionally minimal: one Python script, no DB, just ics.

## License

MIT
