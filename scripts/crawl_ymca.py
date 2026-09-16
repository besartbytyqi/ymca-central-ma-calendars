#!/usr/bin/env python3
"""Crawl YMCA Central MA GroupexPro schedules -> per-branch iCal files."""
from __future__ import annotations
import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ymca_groupexpro import BRANCHES, BRANCH_ALIASES, fetch_all
from src.ymca_ical import events_to_ical, write_cal
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)
def main():
    p = argparse.ArgumentParser(description="Crawl YMCA schedules -> iCal")
    p.add_argument("--branches", help="Comma-separated: boroughs,central,greendale,leominster,montachusett,tricommunity (default: greendale,central)", default=None)
    p.add_argument("--all", action="store_true", help="Crawl all 6 branches")
    p.add_argument("--days", type=int, default=7, help="Days ahead (7=week, 14=two weeks)")
    p.add_argument("--output", default="calendars", help="Output directory for .ics files")
    p.add_argument("--start", help="Start date YYYY-MM-DD (default today)")
    p.add_argument("--category", help="Only include categories (comma-separated)", default=None)
    p.add_argument("--exclude-category", help="Exclude categories", default=None)
    p.add_argument("--only-classes", action="store_true", help="Only Group Exercise classes")
    args = p.parse_args()
    if args.all:
        branch_keys = list(BRANCHES.keys())
    elif args.branches:
        branch_keys = [b.strip().lower() for b in args.branches.split(",")]
        for b in branch_keys:
            if b not in BRANCHES and b not in BRANCH_ALIASES:
                raise SystemExit(f"Unknown branch {b}. Choose from {list(BRANCHES.keys())}")
    else:
        branch_keys = ["greendale", "central"]
    start = date.fromisoformat(args.start) if args.start else date.today()
    end = start + timedelta(days=args.days - 1)
    logger.info(f"Fetching {branch_keys} from {start} to {end} ({args.days} days)")
    result = fetch_all(start, end, branches=branch_keys)
    only = set()
    exclude = set()
    if args.only_classes:
        only.add("group exercise")
    if args.category:
        only.update(c.strip().lower() for c in args.category.split(","))
    if args.exclude_category:
        exclude.update(c.strip().lower() for c in args.exclude_category.split(","))
    if only or exclude:
        for key in list(result.keys()):
            filtered = [ev for ev in result[key] if (not only or (ev.get("category") or "").strip().lower() in only) and (ev.get("category") or "").strip().lower() not in exclude]
            logger.info(f"Filtered {key}: {len(result[key])} -> {len(filtered)}")
            result[key] = filtered
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for key, events in result.items():
        branch = BRANCHES[key]
        cal = events_to_ical(events, branch["name"], branch["address"])
        path = out_dir / f"{key}.ics"
        write_cal(cal, path)
        logger.info(f"Wrote {len(events)} events -> {path}")
        total += len(events)
        txt_path = out_dir / f"{key}.txt"
        with open(txt_path, "w") as f:
            f.write(f"# {branch['name']} - {branch['address']} - {start} to {end}\n# {len(events)} events\n\n")
            for ev in sorted(events, key=lambda e: e["dt_start"]):
                f.write(f"{ev['dt_start'].strftime('%a %m/%d %I:%M%p')} - {ev['dt_end'].strftime('%I:%M%p')} | {ev['class_name']} @ {ev['studio']} [{ev['category']}]\n")
    all_events = [ev for lst in result.values() for ev in lst]
    if len(branch_keys) > 1:
        from icalendar import Calendar, Event
        from zoneinfo import ZoneInfo
        from datetime import datetime
        EASTERN = ZoneInfo("America/New_York")
        UTC = ZoneInfo("UTC")
        cal_all = Calendar()
        cal_all.add("prodid", "-//YMCA of Central MA//All Branches//EN")
        cal_all.add("version", "2.0")
        cal_all.add("calscale", "GREGORIAN")
        cal_all.add("method", "PUBLISH")
        cal_all.add("x-wr-calname", "YMCA - All Branches")
        for ev in all_events:
            ical_ev = Event()
            ical_ev.add("uid", ev["uid"])
            summary = f"[{ev['branch_name'].split()[0]}] {ev['class_name']} @ {ev['studio']}" if ev['studio'] else f"[{ev['branch_name'].split()[0]}] {ev['class_name']}"
            ical_ev.add("summary", summary)
            ical_ev.add("dtstart", ev["dt_start"].astimezone(UTC))
            ical_ev.add("dtend", ev["dt_end"].astimezone(UTC))
            ical_ev.add("dtstamp", datetime.now(tz=UTC))
            ical_ev.add("location", f"{ev['studio']}, {ev['branch_name']}, {ev['branch_address']}" if ev['studio'] else f"{ev['branch_name']}, {ev['branch_address']}")
            ical_ev.add("description", f"{ev.get('category','')}\n{ev.get('description','')}\nBranch: {ev['branch_name']}")
            cal_all.add_component(ical_ev)
        path_all = out_dir / "all_branches.ics"
        write_cal(cal_all, path_all)
        logger.info(f"Wrote combined {len(all_events)} events -> {path_all}")
    logger.info(f"Done. Total events: {total}. Output dir: {out_dir.resolve()}")
if __name__ == "__main__":
    main()
