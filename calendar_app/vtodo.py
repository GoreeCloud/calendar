"""Conservative VTODO-only iCalendar interchange for GoreeCloud Calendar.

This is manual import/export, NOT CalDAV synchronization. Unknown task fields,
recurrences, invitations, attachments and custom properties are rejected to
avoid pretending they can be preserved in the local task model.
"""
from __future__ import annotations

import datetime as dt
import re

from .ical import (_read_lines, _property, _unescape, _escape, _fold,
                   _date, ImportErrorCalendar, UTC)

MAX_TASKS = 100
MAX_EXPORT_TASKS = 500

def _task_priority(value: str) -> int:
    if not re.fullmatch(r"[0-9]",value):
        raise ImportErrorCalendar("Invalid VTODO priority")
    rank=int(value)
    if rank==0:
        return 3
    if rank<=2:
        return 1
    if rank<=4:
        return 2
    if rank<=6:
        return 3
    return 4

def _normalize(props: dict) -> dict:
    if "UID" not in props or "SUMMARY" not in props:
        raise ImportErrorCalendar("VTODO requires UID and SUMMARY")
    uid=_unescape(props["UID"][1])
    title=_unescape(props["SUMMARY"][1]).strip()
    if (not uid or len(uid)>255 or "\r" in uid or "\n" in uid or
            not title or len(title)>160):
        raise ImportErrorCalendar("Invalid VTODO UID or title")
    for key in ("UID","SUMMARY","STATUS","PRIORITY"):
        if key in props and props[key][0]:
            raise ImportErrorCalendar("Unsupported VTODO property parameters")
    status=props.get("STATUS",({},"NEEDS-ACTION"))[1].upper()
    if status not in ("NEEDS-ACTION","COMPLETED"):
        raise ImportErrorCalendar("Unsupported VTODO status")
    priority=_task_priority(props.get("PRIORITY",({},"0"))[1])
    due=None
    if "DUE" in props:
        instant,all_day=_date("DUE",*props["DUE"])
        if all_day:
            raise ImportErrorCalendar("All-day VTODO DUE dates are unsupported")
        due=instant.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00","Z")
    if "DTSTAMP" in props:
        if props["DTSTAMP"][0]:
            raise ImportErrorCalendar("Unsupported VTODO DTSTAMP parameters")
        _,all_day=_date("DTSTAMP",*props["DTSTAMP"])
        if all_day:
            raise ImportErrorCalendar("Invalid VTODO DTSTAMP date")
    return {"uid":uid,"title":title,"due_at":due,
            "done":int(status=="COMPLETED"),"priority":priority}

def parse_tasks(content: str) -> list[dict]:
    lines=_read_lines(content)
    if (not lines or lines[0].upper()!="BEGIN:VCALENDAR" or
            lines[-1].upper()!="END:VCALENDAR"):
        raise ImportErrorCalendar("Expected complete VTODO VCALENDAR")
    current=None
    entries=[]
    uids=set()
    version=False
    for line in lines[1:-1]:
        name,params,value=_property(line)
        if name=="BEGIN":
            if value.upper()!="VTODO" or current is not None or params:
                raise ImportErrorCalendar("Unsupported nested iCalendar component")
            current={}
            continue
        if name=="END":
            if value.upper()!="VTODO" or current is None or params:
                raise ImportErrorCalendar("Malformed VTODO component")
            item=_normalize(current)
            if item["uid"] in uids:
                raise ImportErrorCalendar("Duplicate task UID in import file")
            uids.add(item["uid"])
            entries.append(item)
            if len(entries)>MAX_TASKS:
                raise ImportErrorCalendar("Import at most 100 tasks at a time")
            current=None
            continue
        if current is None:
            if params or name not in ("VERSION","PRODID","CALSCALE"):
                raise ImportErrorCalendar("Unsupported VCALENDAR task property")
            if name=="VERSION":
                if version or value!="2.0":
                    raise ImportErrorCalendar("Expected iCalendar VERSION:2.0")
                version=True
            continue
        if name not in ("UID","SUMMARY","DUE","STATUS","PRIORITY","DTSTAMP"):
            raise ImportErrorCalendar("Unsupported VTODO field: "+name)
        if name in current:
            raise ImportErrorCalendar("Duplicate VTODO property")
        current[name]=(params,value)
    if current is not None or not version or not entries:
        raise ImportErrorCalendar("Incomplete or empty VTODO calendar")
    return entries

def export_tasks(entries: list[dict]) -> str:
    if len(entries)>MAX_EXPORT_TASKS:
        raise ImportErrorCalendar("Export at most 500 tasks at a time")
    stamp=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    priorities={1:1,2:3,3:5,4:9}
    lines=["BEGIN:VCALENDAR","VERSION:2.0",
           "PRODID:-//GoreeCloud//Calendar Tasks//EN"]
    for task in entries:
        uid=task.get("original_uid") or (task["id"]+"@goreecloud.local")
        priority=task["priority"]
        if priority not in priorities:
            raise ImportErrorCalendar("Unsupported saved task priority")
        lines.extend(["BEGIN:VTODO","UID:"+_escape(uid),"DTSTAMP:"+stamp,
                      "SUMMARY:"+_escape(task["title"]),
                      "STATUS:"+("COMPLETED" if task["done"] else "NEEDS-ACTION"),
                      "PRIORITY:"+str(priorities[priority])])
        if task.get("due_at"):
            due=dt.datetime.fromisoformat(task["due_at"].replace("Z","+00:00"))
            if due.tzinfo is None:
                raise ImportErrorCalendar("Invalid saved task due date")
            lines.append("DUE:"+due.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"))
        lines.append("END:VTODO")
    lines.append("END:VCALENDAR")
    physical=[]
    for line in lines:
        physical.extend(_fold(line))
    return "\r\n".join(physical)+"\r\n"
