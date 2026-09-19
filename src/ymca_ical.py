"""Generate per-branch iCal files from GroupexPro events."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

EASTERN = ZoneInfo("America/New_York")

def events_to_ical(events: list[dict], branch_name: str, branch_address: str, cal_name: str | None = None) -> Calendar:
    cal = Calendar()
    cal.add("prodid", f"-//YMCA of Central MA//{branch_name}//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", cal_name or f"YMCA - {branch_name}")
    cal.add("x-wr-timezone", "America/New_York")
    cal.add("description", f"Schedule for {branch_name} - {branch_address}")

    for ev in events:
        ical_ev = Event()
        # UID stable: hash of branch+class+start
        uid = ev.get("uid") or hashlib.md5(f"{branch_name}{ev['class_name']}{ev['dt_start']}".encode()).hexdigest() + f"@ymcaofcm.org"
        ical_ev.add("uid", uid)
        # Summary: Class Name [Category] @ Studio
        summary = ev["class_name"]
        if ev.get("studio"):
            summary += f" @ {ev['studio']}"
        ical_ev.add("summary", summary)
        # Use UTC for max Google compatibility (DTSTAMP must be UTC, DTSTART/DTEND as UTC)
        ical_ev.add("dtstart", ev["dt_start"].astimezone(ZoneInfo("UTC")))
        ical_ev.add("dtend", ev["dt_end"].astimezone(ZoneInfo("UTC")))
        ical_ev.add("dtstamp", datetime.now(tz=ZoneInfo("UTC")))
        location = f"{ev.get('branch_name', branch_name)}, {branch_address}"
        if ev.get("studio"):
            location = f"{ev['studio']}, {location}"
        ical_ev.add("location", location)
        # Description includes category + description
        desc_parts = []
        if ev.get("category"):
            desc_parts.append(f"Category: {ev['category']}")
        if ev.get("studio"):
            desc_parts.append(f"Studio: {ev['studio']}")
        if ev.get("description"):
            desc_parts.append(ev["description"])
        desc_parts.append(f"Branch: {branch_name}")
        ical_ev.add("description", "\n".join(desc_parts))
        ical_ev.add("categories", ev.get("category", ""))
        # Use class name as fallback
        ical_ev.add("status", "CONFIRMED")
        cal.add_component(ical_ev)
    return cal

def write_cal(cal: Calendar, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(cal.to_ical())
