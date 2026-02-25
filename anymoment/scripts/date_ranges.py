#!/usr/bin/env python3
"""
date_ranges.py

Small helper to print common date ranges in ISO format for a given timezone.
Usage:
  python date_ranges.py next-week --tz Europe/Madrid
  python date_ranges.py --days-back 4 --days-forward 8 --tz Europe/Madrid
  python date_ranges.py --days-back 4  # -> start = 4 days ago (00:00), end = now
  python date_ranges.py --weeks-back 1 --hours-forward 5
Outputs JSON with start/end ISO datetimes.
"""
import sys
import argparse
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    from backports.zoneinfo import ZoneInfo  # type: ignore
import json


def next_week_range(tz_name: str):
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    this_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = this_monday + timedelta(days=7)
    start = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


def relative_range(days_back: int, days_forward: int, weeks_back: int, weeks_forward: int, hours_back: int, hours_forward: int, tz_name: str):
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # aggregate offsets
    back_delta = timedelta()
    forward_delta = timedelta()

    if weeks_back:
        back_delta += timedelta(weeks=weeks_back)
    if days_back:
        back_delta += timedelta(days=days_back)
    if hours_back:
        back_delta += timedelta(hours=hours_back)

    if weeks_forward:
        forward_delta += timedelta(weeks=weeks_forward)
    if days_forward:
        forward_delta += timedelta(days=days_forward)
    if hours_forward:
        forward_delta += timedelta(hours=hours_forward)

    # If only back provided (no forward), end = now
    if (back_delta and not forward_delta):
        start = (now - back_delta).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.isoformat()
        return start.isoformat(), end

    # If only forward provided (no back), start = now
    if (forward_delta and not back_delta):
        start = now.isoformat()
        end_dt = (now + forward_delta).replace(hour=23, minute=59, second=59, microsecond=0)
        return start, end_dt.isoformat()

    # Both provided or neither -> full-day bounds around deltas
    if not back_delta and not forward_delta:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return start.isoformat(), end.isoformat()

    start = (now - back_delta).replace(hour=0, minute=0, second=0, microsecond=0)
    end = (now + forward_delta).replace(hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument('range', nargs='?', choices=['next-week'], help='Named range (optional)')
    p.add_argument('--tz', default='Europe/Madrid', help='IANA timezone name')
    p.add_argument('--days-back', type=int, default=0, help='Days before today (inclusive)')
    p.add_argument('--days-forward', type=int, default=0, help='Days after today (inclusive)')
    p.add_argument('--weeks-back', type=int, default=0, help='Weeks before today')
    p.add_argument('--weeks-forward', type=int, default=0, help='Weeks after today')
    p.add_argument('--hours-back', type=int, default=0, help='Hours before now')
    p.add_argument('--hours-forward', type=int, default=0, help='Hours after now')
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if args.range == 'next-week':
        start, end = next_week_range(args.tz)
    elif any([args.days_back, args.days_forward, args.weeks_back, args.weeks_forward, args.hours_back, args.hours_forward]):
        start, end = relative_range(args.days_back, args.days_forward, args.weeks_back, args.weeks_forward, args.hours_back, args.hours_forward, args.tz)
    else:
        # default: today only
        tz = ZoneInfo(args.tz)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    print(json.dumps({'start': start, 'end': end}))

if __name__ == '__main__':
    main(sys.argv[1:])
