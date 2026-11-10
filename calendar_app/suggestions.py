"""Private meeting-time suggestions from already-authorized busy intervals.

No event titles, calendar metadata, or task contents enter this calculation.
Unscheduled slots are only candidates; there is no reservation or holding lock.
"""
from __future__ import annotations
import datetime as dt

UTC=dt.timezone.utc
WORK_START=dt.time(9,0)
WORK_END=dt.time(17,0)

def _instant(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(UTC)

def _utc(s: dt.datetime) -> str:
    return s.isoformat(timespec="seconds").replace("+00:00","Z")

def suggest_slots(busy: list[dict], start: str, end: str,
                  zone: dt.tzinfo, duration_minutes: int,
                  limit: int = 20) -> list[dict]:
    """Return up to 20 candidate slots during 09:00–17:00 local time.

    The caller must enforce access checks and bounded inputs. Time intervals
    are half-open, so an event ending exactly when a slot begins is not busy.
    """
    lower,upper=_instant(start),_instant(end)
    if upper<=lower or duration_minutes<=0 or not 1<=limit<=20:
        raise ValueError("Invalid suggestion window or duration")
    occupied=sorted((_instant(b["start_at"]),_instant(b["end_at"])) for b in busy)
    slots=[]
    day=lower.astimezone(zone).date()
    last=upper.astimezone(zone).date()
    delta=dt.timedelta(minutes=duration_minutes)
    step=dt.timedelta(minutes=15)
    while day<=last:
        begin=dt.datetime.combine(day,WORK_START,tzinfo=zone).astimezone(UTC)
        finish=dt.datetime.combine(day,WORK_END,tzinfo=zone).astimezone(UTC)
        candidate=begin
        while candidate+delta<=min(finish,upper):
            if candidate>=lower and all(candidate+delta<=a or candidate>=b for a,b in occupied):
                slots.append({"start_at":_utc(candidate),"end_at":_utc(candidate+delta)})
                if len(slots)>=limit:
                    return slots
            candidate+=step
        day+=dt.timedelta(days=1)
    return slots
