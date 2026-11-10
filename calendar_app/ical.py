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

def _alarm_minutes(raw: str) -> int:
    if raw=="PT0S":
        return 0
    match=re.fullmatch(r"-PT([0-9]+)([MH])",raw)
    if match:
        number=int(match.group(1))
        minutes=number*(60 if match.group(2)=="H" else 1)
    else:
        match=re.fullmatch(r"-P([0-9]+)D",raw)
        if not match:
            raise ImportErrorCalendar("Only display reminders before an event are supported")
        minutes=int(match.group(1))*1440
    if minutes>43200:
        raise ImportErrorCalendar("Reminder must be at most 30 days before an event")
    return minutes

def _normalize(props: dict) -> dict:
    for field in ("UID", "DTSTART", "DTEND"):
        if field not in props:
            raise ImportErrorCalendar("VEVENT requires UID, DTSTART and DTEND")
    for field in ("RDATE", "RECURRENCE-ID", "DURATION"):
        if field in props:
            raise ImportErrorCalendar("Recurrence exceptions and duration-only events are unsupported")
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
    recurrence=None
    if "RRULE" in props:
        from .recurrence import validate_rule, RecurrenceError
        fields={}
        for item in props["RRULE"][1].split(";"):
            if "=" not in item:
                raise ImportErrorCalendar("Malformed RRULE")
            key, val=item.split("=",1)
            key=key.upper()
            if key in fields or key not in ("FREQ","INTERVAL","COUNT"):
                raise ImportErrorCalendar("RRULE uses unsupported parameters")
            fields[key]=val
        if "FREQ" not in fields or "COUNT" not in fields:
            raise ImportErrorCalendar("RRULE requires FREQ and COUNT")
        if not fields["COUNT"].isdigit() or not fields.get("INTERVAL","1").isdigit():
            raise ImportErrorCalendar("Invalid RRULE interval or count")
        try:
            recurrence=validate_rule({
                "freq":fields["FREQ"].upper(), "interval":int(fields.get("INTERVAL","1")),
                "count":int(fields["COUNT"]),
                "tzid":None if all_day else props["DTSTART"][0].get("TZID")
            })
        except RecurrenceError as error:
            raise ImportErrorCalendar(str(error)) from None
    exclusions=[]
    if "EXDATE" in props:
        if recurrence is None:
            raise ImportErrorCalendar("EXDATE requires a supported recurring series")
        from .recurrence import expand
        params,values=props["EXDATE"]
        if not values or len(values.split(","))>366:
            raise ImportErrorCalendar("Invalid EXDATE list")
        for value in values.split(","):
            instant,is_all_day=_date("EXDATE",params,value)
            if is_all_day!=all_day:
                raise ImportErrorCalendar("EXDATE must match event date type")
            stamp=instant.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z")
            candidate=instant.astimezone(UTC)
            prototype={"start_at":start.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z"),
                       "end_at":end.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z")}
            if not any(o["occurrence_start_at"]==stamp for o in expand(
                prototype,recurrence,candidate,candidate+dt.timedelta(seconds=1))):
                raise ImportErrorCalendar("EXDATE is not an occurrence in the recurring series")
            exclusions.append(stamp)
        if len(set(exclusions))!=len(exclusions):
            raise ImportErrorCalendar("Duplicate EXDATE")
    reminder_minutes=_alarm_minutes(props["_ALARM"][1]) if "_ALARM" in props else None
    return {
        "uid":uid, "title":title.strip(), "description":description, "location":location,
        "start_at":start.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z"),
        "end_at":end.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z"),
        "all_day":all_day, "recurrence":recurrence,"exclusions":exclusions,
        "reminder_minutes":reminder_minutes
    }

def parse_calendar(content: str) -> list[dict]:
    lines = _read_lines(content)
    if not lines or lines[0].upper() != "BEGIN:VCALENDAR" or lines[-1].upper() != "END:VCALENDAR":
        raise ImportErrorCalendar("Expected a complete VCALENDAR")
    events, current, alarm, seen = [], None, None, set()
    for line in lines[1:-1]:
        name,params,value = _property(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            if current is not None:
                raise ImportErrorCalendar("Nested VEVENT is unsupported")
            current = {}
            continue
        if name == "END" and value.upper() == "VEVENT":
            if current is None or alarm is not None:
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
                if alarm is not None or "_ALARM" in current:
                    raise ImportErrorCalendar("Multiple or nested VALARM is unsupported")
                alarm = {}
            elif name == "END" and value.upper() == "VALARM":
                if alarm is None or alarm.get("ACTION", ({}, ""))[1].upper() != "DISPLAY" or "TRIGGER" not in alarm:
                    raise ImportErrorCalendar("Only display alarms with a relative trigger are supported")
                if alarm["TRIGGER"][0]:
                    raise ImportErrorCalendar("Parameterized alarm triggers are unsupported")
                current["_ALARM"]=({},alarm["TRIGGER"][1])
                alarm=None
            elif alarm is not None:
                if name in alarm:
                    raise ImportErrorCalendar("Duplicate VALARM property")
                alarm[name]=(params,value)
            else:
                if name in current:
                    raise ImportErrorCalendar("Duplicate event property")
                current[name] = (params,value)
    if current is not None:
        raise ImportErrorCalendar("Unterminated VEVENT")
    if not events:
        raise ImportErrorCalendar("Calendar contains no supported events")
    return events

def _fold(line: str) -> list[str]:
    """Fold physical lines to at most 75 UTF-8 octets (RFC 5545)."""
    chunks, current, length = [], "", 0
    for char in line:
        n=len(char.encode("utf-8"))
        if length+n>75:
            chunks.append(current)
            current=" "+char
            length=1+n
        else:
            current+=char
            length+=n
    chunks.append(current)
    return chunks

def _escape(value: str) -> str:
    return (value.replace("\\","\\\\").replace("\r","")
            .replace("\n","\\n").replace(";","\\;").replace(",","\\,"))

def export_calendar(entries: list[dict]) -> str:
    """Export owned or shared calendar events, all-day dates and bounded RRULEs."""
    import json
    lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//GoreeCloud//Calendar//EN"]
    timestamp=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    for event in entries:
        uid=event.get("original_uid") or (event["id"]+"@goreecloud.local")
        start=dt.datetime.fromisoformat(event["start_at"].replace("Z","+00:00"))
        end=dt.datetime.fromisoformat(event["end_at"].replace("Z","+00:00"))
        rule=json.loads(event["rule_json"]) if event.get("rule_json") else None
        if event["all_day"]:
            start_line="DTSTART;VALUE=DATE:"+start.strftime("%Y%m%d")
            end_line="DTEND;VALUE=DATE:"+end.strftime("%Y%m%d")
        elif rule and rule.get("tzid"):
            tz=ZoneInfo(rule["tzid"])
            start_line="DTSTART;TZID="+rule["tzid"]+":"+start.astimezone(tz).strftime("%Y%m%dT%H%M%S")
            end_line="DTEND;TZID="+rule["tzid"]+":"+end.astimezone(tz).strftime("%Y%m%dT%H%M%S")
        else:
            start_line="DTSTART:"+start.strftime("%Y%m%dT%H%M%SZ")
            end_line="DTEND:"+end.strftime("%Y%m%dT%H%M%SZ")
        lines.extend(["BEGIN:VEVENT","UID:"+_escape(uid),"DTSTAMP:"+timestamp,
                      start_line,end_line,"SUMMARY:"+_escape(event["title"]),
                      "DESCRIPTION:"+_escape(event["description"]),
                      "LOCATION:"+_escape(event["location"])])
        if rule:
            lines.append("RRULE:FREQ="+rule["freq"]+";INTERVAL="+str(rule["interval"])+";COUNT="+str(rule["count"]))
        exclusions=event.get("exclusions") or []
        if exclusions and not rule:
            raise ImportErrorCalendar("Cannot export recurrence exceptions for a single event")
        if exclusions:
            if event["all_day"]:
                formatted=[dt.datetime.fromisoformat(t.replace("Z","+00:00")).strftime("%Y%m%d")
                           for t in exclusions]
                lines.append("EXDATE;VALUE=DATE:"+",".join(formatted))
            elif rule.get("tzid"):
                tz=ZoneInfo(rule["tzid"])
                formatted=[dt.datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(tz)
                           .strftime("%Y%m%dT%H%M%S") for t in exclusions]
                lines.append("EXDATE;TZID="+rule["tzid"]+":"+ ",".join(formatted))
            else:
                formatted=[dt.datetime.fromisoformat(t.replace("Z","+00:00")).strftime("%Y%m%dT%H%M%SZ")
                           for t in exclusions]
                lines.append("EXDATE:"+",".join(formatted))
        reminder=event.get("reminder_minutes")
        if reminder is not None:
            if type(reminder) is not int or not 0<=reminder<=43200:
                raise ImportErrorCalendar("Invalid saved reminder")
            trigger="PT0S" if reminder==0 else "-PT"+str(reminder)+"M"
            lines.extend(["BEGIN:VALARM","TRIGGER:"+trigger,"ACTION:DISPLAY",
                          "DESCRIPTION:"+_escape(event["title"]),"END:VALARM"])
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    physical=[]
    for line in lines:
        physical.extend(_fold(line))
    return "\r\n".join(physical)+"\r\n"
