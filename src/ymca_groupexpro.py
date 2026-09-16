"""YMCA of Central Massachusetts — GroupexPro crawler.

All 6 branches share account a=1045, locations 7021-7026.
We fetch via public JSONP JSON endpoint (no auth) and generate per-branch iCal.

Branches:
  Boroughs:      7021 - 4 Valente Drive, Westborough
  Central:       7022 - 766 Main St, Worcester (your Main Street)
  Greendale:     7023 - 75 Shore Dr, Worcester (your Greendale)
  Leominster:    7024 - 108 Adams St, Leominster
  Montachusett:  7025 - 55 Wallace Ave, Fitchburg
  Tri-Community: 7026 - 43 Everett St, Southbridge
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

ACCOUNT_ID = 1045
BRANCHES = {
    "boroughs": {"location_id": 7021, "name": "Boroughs Family Branch", "address": "4 Valente Drive, Westborough, MA 01581"},
    "central": {"location_id": 7022, "name": "Central Community Branch", "address": "766 Main St, Worcester, MA 01610"},
    "greendale": {"location_id": 7023, "name": "Greendale Family Branch", "address": "75 Shore Dr, Worcester, MA 01605"},
    "leominster": {"location_id": 7024, "name": "Leominster Community Branch", "address": "108 Adams St, Leominster, MA 01453"},
    "montachusett": {"location_id": 7025, "name": "Montachusett Community Branch", "address": "55 Wallace Ave, Fitchburg, MA 01420"},
    "tricommunity": {"location_id": 7026, "name": "Tri-Community Family Branch", "address": "43 Everett St, Southbridge, MA 01550"},
}
# Friendly aliases
BRANCH_ALIASES = {"main_street": "central", "greendale": "greendale", "worcester": "central"}

EASTERN = ZoneInfo("America/New_York")

BASE_URL = "https://groupexpro.com/schedule/embed/json_schedule.php"

def _decode_description(b64: str) -> str:
    if not b64:
        return ""
    try:
        # GroupexPro gives base64 without padding sometimes, with HTML
        padded = b64 + "=" * (-len(b64) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        # Strip HTML tags briefly
        decoded = re.sub(r"<[^>]+>", " ", decoded)
        decoded = decoded.replace("&nbsp;", " ").replace("&amp;", "&").strip()
        decoded = re.sub(r"\s+", " ", decoded)
        return decoded
    except Exception:
        return ""

def _parse_time_range(date_str: str, time_range: str) -> tuple[datetime, datetime] | None:
    """Parse '5:30am-6:15am' + 'Wednesday, September 16, 2026' into ET datetimes."""
    try:
        # date_str like "Wednesday, September 16, 2026"
        d = datetime.strptime(date_str.strip(), "%A, %B %d, %Y").date()
        # time_range like "5:30am-6:15am" or "5:15am-10:50am"
        parts = time_range.strip().lower().split("-")
        if len(parts) != 2:
            return None
        def parse_t(s: str) -> time:
            s = s.strip()
            # Handle 5:30am, 5:30 am, 5am
            s = s.replace(" ", "")
            for fmt in ("%I:%M%p", "%I%p"):
                try:
                    return datetime.strptime(s, fmt).time()
                except ValueError:
                    continue
            raise ValueError(s)
        t0 = parse_t(parts[0])
        t1 = parse_t(parts[1])
        dt0 = datetime.combine(d, t0, tzinfo=EASTERN)
        dt1 = datetime.combine(d, t1, tzinfo=EASTERN)
        # Handle overnight (end earlier than start -> next day)
        if dt1 <= dt0:
            dt1 += timedelta(days=1)
        return dt0, dt1
    except Exception as e:
        logger.debug(f"Failed to parse time {date_str} {time_range}: {e}")
        return None

def fetch_branch(branch_key: str, start: date, end: date) -> list[dict]:
    """Fetch raw GroupexPro events for one branch between start and end inclusive."""
    branch = BRANCHES.get(branch_key.lower())
    if not branch:
        # try alias
        alias = BRANCH_ALIASES.get(branch_key.lower())
        if alias:
            branch = BRANCHES[alias]
        else:
            raise ValueError(f"Unknown branch {branch_key}. Choose from {list(BRANCHES.keys())}")
    location_id = branch["location_id"]
    start_ts = int(datetime.combine(start, time.min, tzinfo=EASTERN).timestamp())
    # end is exclusive in GroupexPro, so use end+1 day
    end_ts = int(datetime.combine(end + timedelta(days=1), time.min, tzinfo=EASTERN).timestamp())
    params = {
        "schedule": "",
        "instructor_id": "true",
        "format": "json",
        "a": ACCOUNT_ID,
        "location": location_id,
        "category": "",
        "studio": "",
        "class": "",
        "instructor": "",
        "start": start_ts,
        "end": end_ts,
    }
    url = BASE_URL
    resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.ymcaofcm.org/schedules/"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    events = []
    for row in data.get("aaData", []):
        # row is list with 16 cols as discovered
        if len(row) < 9:
            continue
        date_str = row[0]          # "Wednesday, September 16, 2026"
        time_range = row[1]        # "5:30am-6:15am"
        class_name = row[2].strip()
        studio = re.sub(r"<[^>]+>", "", row[4]).replace("&nbsp;", " ").strip() if row[4] else ""
        category = row[5].strip() if len(row) > 5 else ""
        # row[6] maybe shortened category, row[7] maybe duration? row[8] is branch name
        branch_name = row[8] if len(row) > 8 else branch["name"]
        description_b64 = row[10] if len(row) > 10 else ""
        description = _decode_description(description_b64)
        parsed = _parse_time_range(date_str, time_range)
        if not parsed:
            continue
        dt_start, dt_end = parsed
        # Some events like "Reserved" or "6 Lap Lanes" are not classes but pool/gym reservations - include all as requested
        # Build unique id: branch + date + time + class
        uid_base = f"{branch_key}-{date_str}-{time_range}-{class_name}".lower().replace(" ", "-")
        # Clean studio
        events.append({
            "branch_key": branch_key,
            "branch_name": branch_name or branch["name"],
            "branch_address": branch["address"],
            "location_id": location_id,
            "date_str": date_str,
            "time_range": time_range,
            "class_name": class_name,
            "studio": studio,
            "category": category,
            "description": description,
            "dt_start": dt_start,
            "dt_end": dt_end,
            "uid": re.sub(r"[^a-z0-9\-]", "", uid_base) + f"@ymcaofcm-{location_id}",
        })
    return events

def fetch_all(start: date, end: date, branches: list[str] | None = None) -> dict[str, list[dict]]:
    """Fetch all branches, returns dict branch_key -> events."""
    keys = branches or list(BRANCHES.keys())
    result = {}
    for k in keys:
        try:
            result[k] = fetch_branch(k, start, end)
            logger.info(f"Fetched {len(result[k])} events for {k}")
        except Exception as e:
            logger.error(f"Failed fetch {k}: {e}")
            result[k] = []
    return result
