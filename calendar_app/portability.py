"""Private, bounded, owner-only Calendar JSON portability export.

Source data is retrieved only from calendars owned by the authenticated user.
Export intentionally excludes passwords, session tokens, user accounts,
calendar member lists and cross-account shared calendar content.
"""
from __future__ import annotations

import json
import sqlite3

FORMAT="goreecloud-calendar-data"
VERSION=1
MAX_CALENDARS=200
MAX_RECORDS=5000
MAX_BYTES=5*1024*1024

class ExportLimitError(ValueError):
    pass

def export_owned_data(db: sqlite3.Connection, user_id: str, exported_at: str) -> dict:
    calendars=db.execute(
        "SELECT id,name,color,description,created_at FROM calendars "
        "WHERE owner_id=? ORDER BY name,id LIMIT ?",(user_id,MAX_CALENDARS+1)).fetchall()
    if len(calendars)>MAX_CALENDARS:
        raise ExportLimitError("Too many calendars for one export")
    result={"format":FORMAT,"version":VERSION,"exported_at":exported_at,"calendars":[]}
    total=0
    for calendar in calendars:
        cid=calendar["id"]
        event_rows=db.execute(
            "SELECT e.id,e.title,e.description,e.location,e.start_at,e.end_at,"
            "e.all_day,e.version,e.created_at,e.updated_at,r.rule_json,"
            "alarm.minutes_before AS reminder_minutes "
            "FROM events e LEFT JOIN event_recurrence r ON r.event_id=e.id "
            "LEFT JOIN event_reminders alarm ON alarm.event_id=e.id "
            "WHERE e.calendar_id=? ORDER BY e.start_at,e.id LIMIT ?",
            (cid,MAX_RECORDS+1)).fetchall()
        task_rows=db.execute(
            "SELECT id,title,due_at,done,priority,created_at,updated_at "
            "FROM tasks WHERE calendar_id=? ORDER BY created_at,id LIMIT ?",
            (cid,MAX_RECORDS+1)).fetchall()
        total+=len(event_rows)+len(task_rows)
        if total>MAX_RECORDS:
            raise ExportLimitError("Too many events or tasks for one export")
        record=dict(calendar)
        record["events"]=[]
        record["tasks"]=[dict(row) for row in task_rows]
        for event in event_rows:
            obj=dict(event)
            rule=obj.pop("rule_json")
            obj["recurrence"]=json.loads(rule) if rule else None
            obj["excluded_occurrences"]=[
                r["occurrence_at"] for r in db.execute(
                    "SELECT occurrence_at FROM event_exclusions "
                    "WHERE event_id=? ORDER BY occurrence_at",(obj["id"],))]
            record["events"].append(obj)
        result["calendars"].append(record)
    raw=json.dumps(result,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    if len(raw)>MAX_BYTES:
        raise ExportLimitError("Personal export exceeds the five-megabyte limit")
    return result
