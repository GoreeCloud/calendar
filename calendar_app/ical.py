"""Conservative RFC 5545 iCalendar import for GoreeCloud Calendar.

Supports VEVENT DTSTART/DTEND in UTC, IANA TZID local time, and VALUE=DATE
(all-day, end exclusive). Unsupported recurrence is rejected rather than
silently flattening a series. It does not fetch external resources or URLs.
"""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_ICAL_CHARS = 55000
MAX_EVENTS = 100
UTC = dt.timezone.utc

class ImportErrorCalendar(ValueError):
    pass

def _unescape(value: str) -> str:
    if re.search(r"\\(?![nN,;\\])", value):
        raise ImportErrorCalendar("Unsupported iCalendar text escape")
    mapping = {"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}
    return re.sub(r"\\([nN,;\\])", lambda match: mapping[match.group(1)], value)

def _date(property_name: str, params: dict, value: str):
    if params.get("VALUE") == "DATE":
        if not re.fullmatch(r"\d{8}", value):
            raise ImportErrorCalendar("Invalid all-day date")
        try:
            d = dt.datetime.strptime(value, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            raise ImportErrorCalendar("Invalid all-day date") from None
        return d, True
    if params.get("VALUE", "DATE-TIME") != "DATE-TIME":
        raise ImportErrorCalendar("Unsupported date value type")
    if not re.fullmatch(r"\d{8}T\d{6}Z?", value):
        raise ImportErrorCalendar("Invalid date-time format")
    try:
        parsed = dt.datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
    except ValueError:
        raise ImportErrorCalendar("Invalid date-time value") from None
    if value.endswith("Z"):
        if "TZID" in params:
            raise ImportErrorCalendar("UTC date-time cannot specify TZID")
        return parsed.replace(tzinfo=UTC), False
    tzid = params.get("TZID")
    if not tzid or len(tzid) > 100 or ".." in tzid:
        raise ImportErrorCalendar("Floating times are unsupported; use UTC or IANA TZID")
    try:
        tz = ZoneInfo(tzid)
    except (ValueError, ZoneInfoNotFoundError, KeyError):
        raise ImportErrorCalendar("Unsupported timezone identifier") from None
    aware = parsed.replace(tzinfo=tz)
    # The same wall time can be ambiguous around a DST transition; reject
    # nonexistent times rather than silently scheduling at another wall time.
    roundtrip = aware.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    if roundtrip != parsed:
        raise ImportErrorCalendar("Nonexistent local time at daylight saving transition")
    return aware.astimezone(UTC), False

def _read_lines(content: str) -> list[str]:
    if not isinstance(content, str) or not content.strip() or len(content) > MAX_ICAL_CHARS:
        raise ImportErrorCalendar("Invalid or oversized iCalendar content")
    if "\x00" in content:
        raise ImportErrorCalendar("Invalid iCalendar content")
    lines: list[str] = []
    for raw in content.splitlines():
        if len(raw) > 10000:
            raise ImportErrorCalendar("Oversized iCalendar line")
        if raw.startswith((" ", "\t")):
            if not lines:
                raise ImportErrorCalendar("Invalid folded iCalendar line")
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines

def _property(line: str):
    if ":" not in line:
        raise ImportErrorCalendar("Malformed iCalendar property")
    header, value = line.split(":", 1)
    parts = header.split(";")
    name = parts[0].upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{0,60}", name):
        raise ImportErrorCalendar("Invalid iCalendar property name")
    params={}
    for item in parts[1:]:
        if "=" not in item:
            raise ImportErrorCalendar("Malformed iCalendar parameter")
        key, val = item.split("=", 1)
        key = key.upper()
        if not key or not val or key in params:
            raise ImportErrorCalendar("Malformed iCalendar parameter")
        params[key] = val.strip('"')
    return name, params, value

def _normalize(props: dict) -> dict:
    for field in ("UID", "DTSTART", "DTEND"):
        if field not in props:
            raise ImportErrorCalendar("VEVENT requires UID, DTSTART and DTEND")
    for field in ("RRULE", "RDATE", "EXDATE", "RECURRENCE-ID", "DURATION"):
        if field in props:
            raise ImportErrorCalendar("Recurring or duration-only events require a future import version")
    uid = props["UID"][1].strip()
    if not uid or len(uid) > 255 or "\r" in uid or "\n" in uid:
        raise ImportErrorCalendar("Invalid event UID")
    start, all_day = _date("DTSTART", props["DTSTART"][0], props["DTSTART"][1])
    end, end_all_day = _date("DTEND", props["DTEND"][0], props["DTEND"][1])
    if all_day != end_all_day or end <= start:
        raise ImportErrorCalendar("Event start/end types or dates are invalid")
    title = _unescape(props.get("SUMMARY",({}, "(Untitled event)"))[1])
    description = _unescape(props.get("DESCRIPTION",({}, ""))[1])
    location = _unescape(props.get("LOCATION",({}, ""))[1])
    if not title.strip() or len(title) > 160 or len(description) > 4000 or len(location) > 500:
        raise ImportErrorCalendar("Imported event exceeds calendar field limits")
    return {
        "uid":uid, "title":title.strip(), "description":description, "location":location,
        "start_at":start.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z"),
        "end_at":end.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z"),
        "all_day":all_day
    }

def parse_calendar(content: str) -> list[dict]:
    lines = _read_lines(content)
    if not lines or lines[0].upper() != "BEGIN:VCALENDAR" or lines[-1].upper() != "END:VCALENDAR":
        raise ImportErrorCalendar("Expected a complete VCALENDAR")
    events, current, in_alarm, seen = [], None, False, set()
    for line in lines[1:-1]:
        name,params,value = _property(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            if current is not None:
                raise ImportErrorCalendar("Nested VEVENT is unsupported")
            current = {}
            continue
        if name == "END" and value.upper() == "VEVENT":
            if current is None or in_alarm:
                raise ImportErrorCalendar("Malformed VEVENT")
            entry = _normalize(current)
            if entry["uid"] in seen:
                raise ImportErrorCalendar("Duplicate UID within import file")
            seen.add(entry["uid"])
            events.append(entry)
            if len(events) > MAX_EVENTS:
                raise ImportErrorCalendar("Too many events; import at most 100 at a time")
            current = None
            continue
        if current is not None:
            if name == "BEGIN" and value.upper() == "VALARM":
                if in_alarm:
                    raise ImportErrorCalendar("Nested VALARM")
                in_alarm = True
            elif name == "END" and value.upper() == "VALARM":
                in_alarm = False
            elif not in_alarm:
                if name in current:
                    raise ImportErrorCalendar("Duplicate event property")
                current[name] = (params,value)
    if current is not None:
        raise ImportErrorCalendar("Unterminated VEVENT")
    if not events:
        raise ImportErrorCalendar("Calendar contains no supported events")
    return events
