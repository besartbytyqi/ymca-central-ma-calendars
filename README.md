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

1. Copy a raw URL, e.g. Greendale:
   ```
   https://raw.githubusercontent.com/besartbytyqi/ymca-central-ma-calendars/main/calendars/greendale.ics
   ```
2. Google Calendar → `Other calendars + → From URL` → Paste → `Add`
3. Repeat for Central

The URLs update daily at 9am UTC via GitHub Actions. Google re-fetches automatically.

For **instant check**: `Settings → Import & Export → Import` and upload the `.ics` file directly.

## CLI

```bash
pip install requests icalendar

# Your two favorites (default) - 7 days
python scripts/crawl_ymca.py --branches greendale,central --days 7 --output calendars

# All 6 branches
python scripts/crawl_ymca.py --all --days 7 --output calendars

# Only Group Exercise (excludes lap lanes, reservations)
python scripts/crawl_ymca.py --all --only-classes --output calendars

# Custom category filter
python scripts/crawl_ymca.py --category "Aquatics" --output calendars
```

See `python scripts/crawl_ymca.py --help` for all options.

## How it works

GroupexPro JSON: `https://groupexpro.com/schedule/embed/json_schedule.php?schedule&format=json&a=1045&location=7023&start=...&end=...`

Parsed via `src/ymca_groupexpro.py`, converted to iCal with `src/ymca_ical.py` (UTC `DTSTART:20260916T093000Z` for max Google/Apple compatibility).

## Prior Art

No existing public repo specifically for **YMCA of Central Massachusetts / Worcester** was found. Closest generic is `open-y-subprojects/openy_daxko_gxp_syncer` (Drupal Open Y Daxko GroupExPro syncer) and various GroupexPro scrapers. This repo is intentionally minimal: one Python script, no DB, just ics.

## License

MIT
