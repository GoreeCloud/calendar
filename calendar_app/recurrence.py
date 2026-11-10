"""Count-bounded calendar recurrence; supports local wall-clock IANA timezones.

This subset is not a full RFC 5545 recurrence engine: no BYDAY, EXDATE,
unlimited rules or per-instance edits. COUNT includes the original occurrence.
"""
from __future__ import annotations

import calendar
import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class RecurrenceError(ValueError):
    pass

def validate_rule(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"freq","interval","count","tzid"}:
        raise RecurrenceError("Recurrence requires freq, interval, count and tzid")
    freq=value.get("freq")
    interval=value.get("interval")
    count=value.get("count")
    tzid=value.get("tzid")
    if freq not in ("DAILY","WEEKLY","MONTHLY","YEARLY"):
        raise RecurrenceError("Unsupported recurrence frequency")
    if type(interval) is not int or not 1<=interval<=24:
        raise RecurrenceError("Recurrence interval must be 1–24")
    if type(count) is not int or not 2<=count<=366:
        raise RecurrenceError("Recurrence count must be 2–366")
    if tzid is not None:
        if not isinstance(tzid,str) or len(tzid)>100 or ".." in tzid:
            raise RecurrenceError("Invalid recurrence timezone")
        try:
            ZoneInfo(tzid)
        except (ValueError, KeyError, ZoneInfoNotFoundError):
            raise RecurrenceError("Unsupported recurrence timezone") from None
    return {"freq":freq,"interval":interval,"count":count,"tzid":tzid}

def _candidate(first: dt.datetime, freq: str, interval: int, index: int):
    step=index*interval
    try:
        if freq=="DAILY":
            return first+dt.timedelta(days=step)
        if freq=="WEEKLY":
            return first+dt.timedelta(weeks=step)
        if freq=="MONTHLY":
            base=first.year*12+first.month-1+step
            year,month=divmod(base,12)
            month+=1
            if year>9999 or year<1 or first.day>calendar.monthrange(year,month)[1]:
                return None
            return first.replace(year=year,month=month)
        if freq=="YEARLY":
            year=first.year+step
            if year>9999 or first.day>calendar.monthrange(year,first.month)[1]:
                return None
            return first.replace(year=year)
    except (ValueError,OverflowError):
        return None
    return None

def expand(event: dict, rule: dict, range_start: dt.datetime, range_end: dt.datetime):
    tz=ZoneInfo(rule["tzid"]) if rule["tzid"] else dt.timezone.utc
    first_utc=dt.datetime.fromisoformat(event["start_at"].replace("Z","+00:00"))
    last_utc=dt.datetime.fromisoformat(event["end_at"].replace("Z","+00:00"))
    duration=last_utc-first_utc
    first_local=first_utc.astimezone(tz).replace(tzinfo=None)
    yielded=0
    seen=0
    max_attempts=rule["count"]*4+4
    for idx in range(max_attempts):
        wall_time=_candidate(first_local,rule["freq"],rule["interval"],idx)
        if wall_time is None:
            continue
        try:
            local=wall_time.replace(tzinfo=tz)
            occ_start=local.astimezone(dt.timezone.utc)
        except (OverflowError,ValueError):
            continue
        # Invalid wall clock time during spring-forward DST is skipped.
        if occ_start.astimezone(tz).replace(tzinfo=None)!=wall_time:
            continue
        if idx==0 and occ_start!=first_utc:
            raise RecurrenceError("Original event timezone does not match its recurrence rule")
        seen+=1
        if seen>rule["count"]:
            break
        if occ_start>=range_end:
            break
        if occ_start+duration<=range_start:
            continue
        occurrence=dict(event)
        occurrence["start_at"]=occ_start.isoformat(timespec="seconds").replace("+00:00","Z")
        occurrence["end_at"]=(occ_start+duration).isoformat(timespec="seconds").replace("+00:00","Z")
        occurrence["series_start_at"]=event["start_at"]
        occurrence["series_end_at"]=event["end_at"]
        occurrence["occurrence_start_at"]=occurrence["start_at"]
        occurrence["recurrence"]=rule
        yielded+=1
        yield occurrence
