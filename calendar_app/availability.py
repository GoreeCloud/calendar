"""Pure UTC interval normalization for authenticated calendar free/busy responses."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc

def _parse(instant: str) -> dt.datetime:
    return dt.datetime.fromisoformat(instant.replace("Z","+00:00")).astimezone(UTC)

def _stamp(instant: dt.datetime) -> str:
    return instant.isoformat(timespec="seconds").replace("+00:00","Z")

def busy_intervals(events: list[dict], beginning: str, ending: str,
                   tzid: str | None = None) -> list[dict]:
    lower,upper=_parse(beginning),_parse(ending)
    timezone=ZoneInfo(tzid) if tzid else UTC
    clipped=[]
    for item in events:
        a,b=_parse(item["start_at"]),_parse(item["end_at"])
        if item.get("all_day"):
            # An all-day event represents local civil dates, not UTC elapsed
            # time. Reconstruct local midnights in the viewer's timezone.
            a=dt.datetime.combine(a.date(),dt.time.min,tzinfo=timezone).astimezone(UTC)
            b=dt.datetime.combine(b.date(),dt.time.min,tzinfo=timezone).astimezone(UTC)
        if a>=upper or b<=lower:
            continue
        clipped.append((max(a,lower),min(b,upper)))
    clipped.sort()
    merged=[]
    for a,b in clipped:
        if merged and a<=merged[-1][1]:
            merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:
            merged.append((a,b))
    return [{"start_at":_stamp(a),"end_at":_stamp(b)} for a,b in merged]
