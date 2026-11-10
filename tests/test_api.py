import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from calendar_app.core import create_user, make_server

class CalendarAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=str(Path(self.tmp.name)/"calendar.sqlite3")
        create_user(self.db,"owner@example.test","very-long-owner-password")
        create_user(self.db,"other@example.test","very-long-other-password")
        self.server=make_server(self.db,port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_address[1]}"
        self.owner=self.login("owner@example.test","very-long-owner-password")
        self.other=self.login("other@example.test","very-long-other-password")

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3); self.tmp.cleanup()

    def request(self,method,path,token=None,body=None,ics=False):
        headers={}
        if token:headers["Authorization"]="Bearer "+token
        if body is not None:headers["Content-Type"]="application/json"
        req=urllib.request.Request(self.base+path,method=method,headers=headers,
                                   data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req,timeout=3) as response:
                raw=response.read()
                return response.status,raw.decode() if ics else json.loads(raw)
        except urllib.error.HTTPError as error:
            return error.code,json.loads(error.read())

    def login(self,email,password):
        status,data=self.request("POST","/api/v1/login",body={"email":email,"password":password})
        self.assertEqual(status,200,data)
        return data["token"]

    def calendar(self,token):
        status,data=self.request("GET","/api/v1/calendars",token)
        self.assertEqual(status,200)
        return data["calendars"][0]["id"]

    def test_events_crud_conflicts_and_isolation(self):
        cid=self.calendar(self.owner)
        self.assertNotEqual(cid,self.calendar(self.other))
        status,data=self.request("POST","/api/v1/events",self.owner,{"calendar_id":cid,
            "title":"Appointment","start_at":"2026-11-10T10:00:00-06:00",
            "end_at":"2026-11-10T11:00:00-06:00"})
        self.assertEqual(status,201,data)
        eid=data["id"]
        window="?start=2026-11-01T00:00:00Z&end=2026-12-01T00:00:00Z"
        owner_events=self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        self.assertEqual(len(owner_events),1)
        self.assertEqual(owner_events[0]["start_at"],"2026-11-10T16:00:00Z")
        self.assertEqual(self.request("GET","/api/v1/events"+window,self.other)[1]["events"],[])
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.other,{"version":1,"title":"Stolen"})[0],404)
        status,result=self.request("PATCH","/api/v1/events/"+eid,self.owner,{"version":1,"title":"Updated"})
        self.assertEqual((status,result["version"]),(200,2))
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.owner,{"version":1,"title":"Conflict"})[0],409)
        self.assertEqual(self.request("DELETE","/api/v1/events/"+eid,self.owner)[0],200)
        self.assertEqual(self.request("GET","/api/v1/events"+window,self.owner)[1]["events"],[])

    def test_tasks_and_calendar_isolation(self):
        cid=self.calendar(self.owner)
        status,data=self.request("POST","/api/v1/tasks",self.owner,{"calendar_id":cid,"title":"Prepare dinner"})
        self.assertEqual(status,201)
        tid=data["id"]
        self.assertEqual(len(self.request("GET","/api/v1/tasks",self.owner)[1]["tasks"]),1)
        self.assertEqual(self.request("GET","/api/v1/tasks",self.other)[1]["tasks"],[])
        self.assertEqual(self.request("PATCH","/api/v1/tasks/"+tid,self.other,{"done":True})[0],404)
        self.assertEqual(self.request("PATCH","/api/v1/tasks/"+tid,self.owner,{"done":True})[0],200)
        self.assertEqual(self.request("DELETE","/api/v1/tasks/"+tid,self.owner)[0],200)
        self.assertEqual(self.request("DELETE","/api/v1/calendars/"+cid,self.other)[0],404)

    def test_ics_and_input_validation(self):
        cid=self.calendar(self.owner)
        self.request("POST","/api/v1/events",self.owner,{"calendar_id":cid,
            "title":"Bring milk, eggs; soap\nPlease","start_at":"2026-11-10T16:00:00Z",
            "end_at":"2026-11-10T17:00:00Z"})
        status,content=self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.owner,ics=True)
        self.assertEqual(status,200)
        self.assertIn("BEGIN:VCALENDAR",content)
        self.assertIn(r"SUMMARY:Bring milk\, eggs\; soap\nPlease",content)
        self.assertEqual(self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.other)[0],404)
        invalid={"calendar_id":cid,"title":"Bad","start_at":"2026-11-10T10:00:00",
                 "end_at":"2026-11-10T11:00:00"}
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,invalid)[0],400)
        invalid["start_at"]="2026-11-10T10:00:00Z"
        invalid["end_at"]="2026-11-10T09:00:00Z"
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,invalid)[0],400)

    def test_ics_import_idempotent_and_timezone(self):
        cid=self.calendar(self.owner)
        body="\\r\\n".join([
            "BEGIN:VCALENDAR","VERSION:2.0","BEGIN:VEVENT",
            "UID:test-1@example.test","DTSTART;TZID=America/Chicago:20261110T090000",
            "DTEND;TZID=America/Chicago:20261110T100000",
            r"SUMMARY:Team\, planning","END:VEVENT","END:VCALENDAR",""])
        # Convert escaped source markers to real iCalendar CRLF.
        body=body.replace("\\r\\n","\r\n")
        status,result=self.request("POST","/api/v1/import.ics",self.owner,
                                    {"calendar_id":cid,"ics":body})
        self.assertEqual(status,201,result)
        self.assertEqual(result,{"imported":1,"skipped":0})
        self.assertEqual(self.request("POST","/api/v1/import.ics",self.owner,
                         {"calendar_id":cid,"ics":body})[1],{"imported":0,"skipped":1})
        window="?start=2026-11-01T00:00:00Z&end=2026-12-01T00:00:00Z"
        event=self.request("GET","/api/v1/events"+window,self.owner)[1]["events"][0]
        self.assertEqual(event["start_at"],"2026-11-10T15:00:00Z")
        self.assertEqual(event["title"],"Team, planning")
        self.assertEqual(self.request("GET","/api/v1/events"+window,self.other)[1]["events"],[])

    def test_ics_rejects_unsupported_recurrence_and_bad_dates(self):
        cid=self.calendar(self.owner)
        base="BEGIN:VCALENDAR\\nBEGIN:VEVENT\\nUID:a@b\\nDTSTART:20261110T090000Z\\nDTEND:20261110T100000Z\\nSUMMARY:Test\\n%sEND:VEVENT\\nEND:VCALENDAR\\n"
        bad=base % "RRULE:FREQ=DAILY;BYDAY=TU\\n"
        status,result=self.request("POST","/api/v1/import.ics",self.owner,
                                    {"calendar_id":cid,"ics":bad.replace("\\n","\n")})
        self.assertEqual(status,400,result)
        bad=base % ""
        self.assertEqual(self.request("POST","/api/v1/import.ics",self.other,
                         {"calendar_id":cid,"ics":bad.replace("\\n","\n")})[0],404)

    def test_count_bounded_recurring_events_preserve_local_hour(self):
        cid=self.calendar(self.owner)
        status,data=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid, "title":"Weekly planning",
            "start_at":"2026-03-01T15:00:00Z", "end_at":"2026-03-01T16:00:00Z",
            "recurrence":{"freq":"WEEKLY","interval":1,"count":3,"tzid":"America/Chicago"}
        })
        self.assertEqual(status,201,data)
        eid=data["id"]
        window="?start=2026-03-01T00:00:00Z&end=2026-03-31T00:00:00Z"
        events=self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        self.assertEqual(len(events),3,events)
        self.assertEqual([e["start_at"] for e in events],
                         ["2026-03-01T15:00:00Z","2026-03-08T14:00:00Z",
                          "2026-03-15T14:00:00Z"])
        self.assertTrue(all(e["id"]==eid and e["recurrence"]["count"]==3 for e in events))
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.owner,
                          {"version":1,"title":"Updated recurring title"})[0],200)
        again=self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        self.assertTrue(all(e["title"]=="Updated recurring title" for e in again))
        self.assertEqual(self.request("DELETE","/api/v1/events/"+eid,self.owner)[0],200)
        self.assertEqual(self.request("GET","/api/v1/events"+window,self.owner)[1]["events"],[])

    def test_recurrence_validates_and_skips_impossible_monthly_days(self):
        cid=self.calendar(self.owner)
        base={"calendar_id":cid,"title":"Monthly bills",
              "start_at":"2026-01-31T09:00:00Z","end_at":"2026-01-31T09:30:00Z"}
        bad=dict(base,recurrence={"freq":"DAILY","interval":0,"count":3,"tzid":None})
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,bad)[0],400)
        good=dict(base,recurrence={"freq":"MONTHLY","interval":1,"count":3,"tzid":None})
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,good)[0],201)
        events=self.request("GET","/api/v1/events?start=2026-01-01T00:00:00Z&end=2026-05-31T00:00:00Z",
                            self.owner)[1]["events"]
        self.assertEqual([e["start_at"][:10] for e in events],
                         ["2026-01-31","2026-03-31","2026-05-31"][:len(events)])

    def test_sharing_enforces_read_edit_and_revocation(self):
        cid=self.calendar(self.owner)
        status,data=self.request("POST","/api/v1/events",self.owner,
            {"calendar_id":cid,"title":"Shared planning",
             "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z"})
        self.assertEqual(status,201,data)
        eid=data["id"]
        members="/api/v1/calendars/"+cid+"/members"
        self.assertEqual(self.request("POST",members,self.other,
            {"email":"other@example.test","role":"edit"})[0],404)
        status,result=self.request("POST",members,self.owner,
            {"email":"other@example.test","role":"read"})
        self.assertEqual(status,200,result)
        status,other_calendars=self.request("GET","/api/v1/calendars",self.other)
        self.assertEqual(status,200)
        shared=[c for c in other_calendars["calendars"] if c["id"]==cid]
        self.assertEqual(len(shared),1)
        self.assertEqual(shared[0]["role"],"read")
        q="?start=2026-11-01T00:00:00Z&end=2026-12-01T00:00:00Z"
        self.assertEqual(len(self.request("GET","/api/v1/events"+q,self.other)[1]["events"]),1)
        self.assertEqual(self.request("POST","/api/v1/events",self.other,
            {"calendar_id":cid,"title":"Forbidden",
             "start_at":"2026-11-10T18:00:00Z","end_at":"2026-11-10T19:00:00Z"})[0],403)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.other,
            {"version":1,"title":"Forbidden"})[0],404)
        self.assertEqual(self.request("POST",members,self.owner,
            {"email":"other@example.test","role":"edit"})[0],200)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.other,
            {"version":1,"title":"Shared update"})[0],200)
        member=self.request("GET",members,self.owner)[1]["members"][0]
        self.assertEqual(member["role"],"edit")
        self.assertEqual(self.request("DELETE",members+"/"+member["user_id"],self.owner)[0],200)
        self.assertFalse(any(c["id"]==cid for c in self.request("GET","/api/v1/calendars",self.other)[1]["calendars"]))
        self.assertEqual(self.request("GET","/api/v1/events"+q,self.other)[1]["events"],[])

    def test_ics_roundtrip_all_day_and_timezone_recurrence(self):
        cid=self.calendar(self.owner)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Holiday",
            "start_at":"2026-11-10T00:00:00Z","end_at":"2026-11-11T00:00:00Z",
            "all_day":True
        })[0],201)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Weekly sync",
            "start_at":"2026-03-01T15:00:00Z","end_at":"2026-03-01T16:00:00Z",
            "recurrence":{"freq":"WEEKLY","interval":1,"count":3,"tzid":"America/Chicago"}
        })[0],201)
        status,ics=self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.owner,ics=True)
        self.assertEqual(status,200)
        self.assertIn("DTSTART;VALUE=DATE:20261110",ics)
        self.assertIn("DTEND;VALUE=DATE:20261111",ics)
        self.assertIn("DTSTART;TZID=America/Chicago:20260301T090000",ics)
        self.assertIn("RRULE:FREQ=WEEKLY;INTERVAL=1;COUNT=3",ics)
        status,new=self.request("POST","/api/v1/calendars",self.owner,
                                 {"name":"Imported calendar"})
        self.assertEqual(status,201)
        newcid=new["id"]
        status,result=self.request("POST","/api/v1/import.ics",self.owner,
                                    {"calendar_id":newcid,"ics":ics})
        self.assertEqual(status,201,result)
        self.assertEqual(result["imported"],2)
        window="?start=2026-03-01T00:00:00Z&end=2026-03-31T00:00:00Z"
        recurring=self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        imported=[e for e in recurring if e["calendar_id"]==newcid]
        self.assertEqual(len(imported),3)
        self.assertEqual(imported[1]["start_at"],"2026-03-08T14:00:00Z")
        imported_again=self.request("POST","/api/v1/import.ics",self.owner,
                                    {"calendar_id":newcid,"ics":ics})[1]
        self.assertEqual(imported_again["skipped"],2)

    def test_search_is_authenticated_scoped_and_literal(self):
        cid=self.calendar(self.owner)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Annual planning",
            "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z"})[0],201)
        self.assertEqual(self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Planning notes"})[0],201)
        status,found=self.request("GET","/api/v1/search?q=planning",self.owner)
        self.assertEqual(status,200,found)
        self.assertEqual((len(found["events"]),len(found["tasks"])),(1,1))
        self.assertEqual(self.request("GET","/api/v1/search?q=planning",self.other)[1],
                         {"events":[],"tasks":[]})
        self.assertEqual(self.request("GET","/api/v1/search?q=planning")[0],401)
        self.assertEqual(self.request("GET","/api/v1/search?q=%25",self.owner)[0],400)
        self.assertEqual(self.request("GET","/api/v1/search?q=%25%25",self.owner)[1],
                         {"events":[],"tasks":[]})
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,
                         {"email":"other@example.test","role":"read"})[0],200)
        self.assertEqual(len(self.request("GET","/api/v1/search?q=planning",self.other)[1]["events"]),1)

    def test_login_throttle_after_repeated_failures(self):
        for _ in range(10):
            status,_response=self.request("POST","/api/v1/login",body={
                "email":"owner@example.test","password":"incorrect-password"})
            self.assertEqual(status,401)
        self.assertEqual(self.request("POST","/api/v1/login",body={
            "email":"owner@example.test","password":"incorrect-password"})[0],429)
        self.assertEqual(self.request("GET","/healthz")[0],200)

    def test_readiness_checks_persistent_database(self):
        status,data=self.request("GET","/healthz")
        self.assertEqual((status,data),(200,{"status":"ok"}))
        status,data=self.request("GET","/readyz")
        self.assertEqual((status,data),(200,{"status":"ready"}))

    def test_recurring_occurrence_skip_restore_and_roundtrip(self):
        cid=self.calendar(self.owner)
        status,new=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Weekly sync",
            "start_at":"2026-03-01T15:00:00Z","end_at":"2026-03-01T16:00:00Z",
            "recurrence":{"freq":"WEEKLY","interval":1,"count":3,"tzid":"America/Chicago"}})
        self.assertEqual(status,201,new)
        eid=new["id"]
        route="/api/v1/events/"+eid+"/exclusions"
        second="2026-03-08T14:00:00Z"
        window="?start=2026-03-01T00:00:00Z&end=2026-03-31T00:00:00Z"
        events=lambda: self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        self.assertEqual(len(events()),3)
        self.assertEqual(self.request("POST",route,self.owner,{"occurrence_start_at":second,"version":1})[1],
                         {"ok":True,"changed":True,"version":2})
        self.assertEqual([e["start_at"] for e in events()],
                         ["2026-03-01T15:00:00Z","2026-03-15T14:00:00Z"])
        self.assertEqual(self.request("POST",route,self.owner,{"occurrence_start_at":second,"version":1})[0],409)
        self.assertEqual(self.request("GET",route,self.owner)[1]["exclusions"],[second])
        self.assertEqual(self.request("POST",route,self.other,{"occurrence_start_at":second,"version":2})[0],404)
        status,ical=self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.owner,ics=True)
        self.assertEqual(status,200)
        self.assertIn("EXDATE;TZID=America/Chicago:20260308T090000",ical)
        status,new_cal=self.request("POST","/api/v1/calendars",self.owner,{"name":"ICS copy"})
        self.assertEqual(status,201)
        status,imported=self.request("POST","/api/v1/import.ics",self.owner,
                                     {"calendar_id":new_cal["id"],"ics":ical})
        self.assertEqual(status,201,imported)
        copy=[e for e in events() if e["calendar_id"]==new_cal["id"]]
        self.assertEqual(len(copy),2)
        self.assertEqual(self.request("DELETE",route+"?occurrence_start_at="+second+"&version=2",self.owner)[1],
                         {"ok":True,"changed":True,"version":3})
        self.assertEqual(len([e for e in events() if e["calendar_id"]==cid]),3)
        self.assertEqual(self.request("GET",route,self.owner)[1]["exclusions"],[])

    def test_skip_rejects_invalid_dates_and_read_only_members(self):
        cid=self.calendar(self.owner)
        status,created=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Daily check",
            "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z",
            "recurrence":{"freq":"DAILY","interval":1,"count":2,"tzid":None}})
        self.assertEqual(status,201)
        path="/api/v1/events/"+created["id"]+"/exclusions"
        self.assertEqual(self.request("POST",path,self.owner,
            {"occurrence_start_at":"2026-11-20T16:00:00Z","version":1})[0],400)
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,
            {"email":"other@example.test","role":"read"})[0],200)
        self.assertEqual(self.request("POST",path,self.other,
            {"occurrence_start_at":"2026-11-11T16:00:00Z","version":1})[0],404)
        self.assertEqual(self.request("POST",path,self.owner,
            {"occurrence_start_at":"2026-11-11T16:00:00Z","version":1})[0],200)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+created["id"],self.owner,
            {"version":2,"start_at":"2026-11-10T17:00:00Z","end_at":"2026-11-10T18:00:00Z"})[0],200)
        self.assertEqual(self.request("GET",path,self.owner)[1]["exclusions"],[])

    def test_reminders_create_update_export_import_and_recurrence(self):
        cid=self.calendar(self.owner)
        status,new=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Dentist",
            "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z",
            "reminder_minutes":15})
        self.assertEqual(status,201,new)
        eid=new["id"]
        window="?start=2026-11-01T00:00:00Z&end=2026-12-01T00:00:00Z"
        owner=lambda:self.request("GET","/api/v1/events"+window,self.owner)[1]["events"]
        self.assertEqual(owner()[0]["reminder_minutes"],15)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Bad reminder",
            "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z",
            "reminder_minutes":True})[0],400)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.owner,
            {"version":1,"reminder_minutes":30})[0],200)
        self.assertEqual(owner()[0]["reminder_minutes"],30)
        status,ics=self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.owner,ics=True)
        self.assertEqual(status,200)
        self.assertIn("BEGIN:VALARM",ics)
        self.assertIn("TRIGGER:-PT30M",ics)
        status,new_cal=self.request("POST","/api/v1/calendars",self.owner,{"name":"Reminders copy"})
        self.assertEqual(status,201)
        status,result=self.request("POST","/api/v1/import.ics",self.owner,
            {"calendar_id":new_cal["id"],"ics":ics})
        self.assertEqual(status,201,result)
        imported=[e for e in owner() if e["calendar_id"]==new_cal["id"]]
        self.assertEqual(len(imported),1)
        self.assertEqual(imported[0]["reminder_minutes"],30)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+eid,self.owner,
            {"version":2,"reminder_minutes":None})[0],200)
        self.assertIsNone(next(e for e in owner() if e["id"]==eid)["reminder_minutes"])

    def test_ics_alarm_rejects_unsupported_action(self):
        cid=self.calendar(self.owner)
        ics="\r\n".join([
            "BEGIN:VCALENDAR","BEGIN:VEVENT","UID:alarm@example.test",
            "DTSTART:20261110T160000Z","DTEND:20261110T170000Z",
            "SUMMARY:Event","BEGIN:VALARM","ACTION:EMAIL","TRIGGER:-PT15M",
            "END:VALARM","END:VEVENT","END:VCALENDAR",""])
        self.assertEqual(self.request("POST","/api/v1/import.ics",self.owner,
            {"calendar_id":cid,"ics":ics})[0],400)

    def test_freebusy_role_redacts_calendar_events_tasks_and_search(self):
        cid=self.calendar(self.owner)
        status,created=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Sensitive medical appointment",
            "description":"Private notes","location":"Private address",
            "start_at":"2026-11-10T16:00:00Z","end_at":"2026-11-10T17:00:00Z",
            "reminder_minutes":15})
        self.assertEqual(status,201,created)
        self.assertEqual(self.request("POST","/api/v1/tasks",self.owner,
            {"calendar_id":cid,"title":"Private task"})[0],201)
        members="/api/v1/calendars/"+cid+"/members"
        self.assertEqual(self.request("POST",members,self.owner,
            {"email":"other@example.test","role":"freebusy"})[0],200)
        calendars=self.request("GET","/api/v1/calendars",self.other)[1]["calendars"]
        shared=next(c for c in calendars if c["id"]==cid)
        self.assertEqual(shared["role"],"freebusy")
        self.assertNotIn("description",shared)
        self.assertNotIn("owner_id",shared)
        qs="?start=2026-11-01T00:00:00Z&end=2026-12-01T00:00:00Z"
        blocks=self.request("GET","/api/v1/events"+qs,self.other)[1]["events"]
        self.assertEqual(len(blocks),1)
        self.assertEqual(blocks[0]["title"],"Busy")
        self.assertEqual(blocks[0]["description"],"")
        self.assertEqual(blocks[0]["location"],"")
        self.assertEqual(blocks[0]["start_at"],"2026-11-10T16:00:00Z")
        self.assertIsNone(blocks[0]["reminder_minutes"])
        self.assertNotIn("version",blocks[0])
        self.assertNotIn(created["id"],str(blocks))
        self.assertEqual(self.request("GET","/api/v1/tasks",self.other)[1]["tasks"],[])
        self.assertEqual(self.request("GET","/api/v1/search?q=private",self.other)[1],
                         {"events":[],"tasks":[]})
        self.assertEqual(self.request("GET","/api/v1/export.ics?calendar_id="+cid,self.other)[0],403)
        self.assertEqual(self.request("PATCH","/api/v1/events/"+created["id"],self.other,
                         {"version":1,"title":"Guess"})[0],404)
        self.assertEqual(self.request("POST",members,self.owner,
                         {"email":"other@example.test","role":"read"})[0],200)
        full=self.request("GET","/api/v1/events"+qs,self.other)[1]["events"][0]
        self.assertEqual(full["title"],"Sensitive medical appointment")
        self.assertEqual(full["reminder_minutes"],15)

    def test_availability_merges_intervals_and_redacts_event_details(self):
        cid=self.calendar(self.owner)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Private appointment",
            "description":"Sensitive details","start_at":"2026-11-10T16:00:00Z",
            "end_at":"2026-11-10T17:00:00Z"})[0],201)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Overlapping event",
            "start_at":"2026-11-10T16:30:00Z",
            "end_at":"2026-11-10T18:00:00Z"})[0],201)
        path=("/api/v1/availability?calendar_id="+cid+
              "&start=2026-11-10T15:00:00Z&end=2026-11-10T19:00:00Z")
        self.assertEqual(self.request("GET",path,self.other)[0],404)
        self.assertEqual(self.request("GET",path)[0],401)
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,
            {"email":"other@example.test","role":"freebusy"})[0],200)
        status,result=self.request("GET",path,self.other)
        self.assertEqual(status,200,result)
        self.assertEqual(result["busy"],[{
            "start_at":"2026-11-10T16:00:00Z",
            "end_at":"2026-11-10T18:00:00Z"}])
        self.assertNotIn("Private appointment",str(result))
        self.assertNotIn("Sensitive details",str(result))
        self.assertEqual(self.request("GET","/api/v1/availability?calendar_id="+cid+
            "&start=2026-01-01T00:00:00Z&end=2026-12-31T00:00:00Z",self.other)[0],400)

    def test_availability_respects_recurrence_exclusions(self):
        cid=self.calendar(self.owner)
        status,created=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Weekly",
            "start_at":"2026-03-01T15:00:00Z","end_at":"2026-03-01T16:00:00Z",
            "recurrence":{"freq":"WEEKLY","interval":1,"count":3,"tzid":"America/Chicago"}})
        self.assertEqual(status,201)
        self.assertEqual(self.request("POST","/api/v1/events/"+created["id"]+"/exclusions",self.owner,
            {"occurrence_start_at":"2026-03-08T14:00:00Z","version":1})[0],200)
        status,result=self.request("GET","/api/v1/availability?calendar_id="+cid+
            "&start=2026-03-01T00:00:00Z&end=2026-03-22T00:00:00Z",self.owner)
        self.assertEqual(status,200,result)
        self.assertEqual([x["start_at"] for x in result["busy"]],
                         ["2026-03-01T15:00:00Z","2026-03-15T14:00:00Z"])

    def test_calendar_settings_restricted_to_owner_and_delete_cascades(self):
        cid=self.calendar(self.owner)
        othercid=self.calendar(self.other)
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,
            {"email":"other@example.test","role":"edit"})[0],200)
        self.assertEqual(self.request("PATCH","/api/v1/calendars/"+cid,self.other,
            {"name":"Stolen calendar"})[0],404)
        status,data=self.request("PATCH","/api/v1/calendars/"+cid,self.owner,{
            "name":"Team schedule","description":"A better calendar name","color":"#123abc"})
        self.assertEqual(status,200,data)
        current=next(c for c in self.request("GET","/api/v1/calendars",self.owner)[1]["calendars"]
                     if c["id"]==cid)
        self.assertEqual((current["name"],current["color"],current["description"]),
                         ("Team schedule","#123abc","A better calendar name"))
        self.assertEqual(self.request("PATCH","/api/v1/calendars/"+cid,self.owner,
            {"name":"Oops","color":"javascript:invalid"})[0],400)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"To be deleted",
            "start_at":"2026-11-10T12:00:00Z","end_at":"2026-11-10T13:00:00Z"})[0],201)
        self.assertEqual(self.request("DELETE","/api/v1/calendars/"+cid,self.other)[0],404)
        self.assertEqual(self.request("DELETE","/api/v1/calendars/"+cid,self.owner)[0],200)
        self.assertEqual(self.request("GET","/api/v1/calendars",self.other)[1]["calendars"][0]["id"],othercid)
        window="?start=2026-11-10T00:00:00Z&end=2026-11-12T00:00:00Z"
        self.assertEqual(self.request("GET","/api/v1/events"+window,self.owner)[1]["events"],[])

    def test_task_priorities_default_update_and_access(self):
        cid=self.calendar(self.owner)
        status,normal=self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Normal task"})
        self.assertEqual(status,201,normal)
        status,urgent=self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Urgent task","priority":1})
        self.assertEqual(status,201,urgent)
        tasks=self.request("GET","/api/v1/tasks",self.owner)[1]["tasks"]
        self.assertEqual({t["title"]:t["priority"] for t in tasks},
                         {"Normal task":3,"Urgent task":1})
        self.assertEqual(self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Invalid","priority":True})[0],400)
        self.assertEqual(self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Invalid","priority":5})[0],400)
        self.assertEqual(self.request("PATCH","/api/v1/tasks/"+urgent["id"],self.owner,
                         {"priority":4})[0],200)
        self.assertEqual(self.request("PATCH","/api/v1/tasks/"+urgent["id"],self.other,
                         {"priority":1})[0],404)
        result=self.request("GET","/api/v1/tasks",self.owner)[1]["tasks"]
        self.assertEqual(next(t["priority"] for t in result if t["id"]==urgent["id"]),4)

    def test_all_day_availability_uses_local_midnights_and_dst(self):
        cid=self.calendar(self.owner)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Whole day",
            "start_at":"2026-11-10T00:00:00Z","end_at":"2026-11-11T00:00:00Z",
            "all_day":True})[0],201)
        chicago=("/api/v1/availability?calendar_id="+cid+
            "&start=2026-11-10T06:00:00Z&end=2026-11-11T06:00:00Z"
            "&tzid=America%2FChicago")
        status,result=self.request("GET",chicago,self.owner)
        self.assertEqual(status,200,result)
        self.assertEqual(result["busy"],[{
            "start_at":"2026-11-10T06:00:00Z",
            "end_at":"2026-11-11T06:00:00Z"}])
        tokyo=("/api/v1/availability?calendar_id="+cid+
            "&start=2026-11-09T15:00:00Z&end=2026-11-10T15:00:00Z"
            "&tzid=Asia%2FTokyo")
        self.assertEqual(self.request("GET",tokyo,self.owner)[1]["busy"],[{
            "start_at":"2026-11-09T15:00:00Z",
            "end_at":"2026-11-10T15:00:00Z"}])
        self.assertEqual(self.request("GET",chicago.replace("America%2FChicago","Unknown%2FZone"),
                         self.owner)[0],400)
        status,new=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"DST start",
            "start_at":"2026-03-08T00:00:00Z","end_at":"2026-03-09T00:00:00Z",
            "all_day":True})
        self.assertEqual(status,201)
        spring=("/api/v1/availability?calendar_id="+cid+
            "&start=2026-03-08T06:00:00Z&end=2026-03-09T05:00:00Z"
            "&tzid=America%2FChicago")
        status,result=self.request("GET",spring,self.owner)
        self.assertEqual(status,200,result)
        self.assertEqual(result["busy"],[{
            "start_at":"2026-03-08T06:00:00Z",
            "end_at":"2026-03-09T05:00:00Z"}])

    def test_password_change_revokes_all_sessions_and_requires_reauthentication(self):
        second=self.login("owner@example.test","very-long-owner-password")
        count=self.request("GET","/api/v1/sessions",self.owner)
        self.assertEqual(count[0],200)
        self.assertEqual(count[1]["active_sessions"],2)
        path="/api/v1/account/change-password"
        self.assertEqual(self.request("POST",path,self.owner,{"current_password":"wrong",
            "new_password":"new-super-secret-password"})[0],403)
        self.assertEqual(self.request("POST",path,self.owner,{"current_password":"very-long-owner-password",
            "new_password":"tiny"})[0],400)
        self.assertEqual(self.request("POST",path,self.owner,{"current_password":"very-long-owner-password",
            "new_password":"very-long-owner-password"})[0],400)
        status,changed=self.request("POST",path,self.owner,{
            "current_password":"very-long-owner-password",
            "new_password":"new-super-secret-password"})
        self.assertEqual((status,changed),(200,{"ok":True,"signed_out":True}))
        self.assertEqual(self.request("GET","/api/v1/me",self.owner)[0],401)
        self.assertEqual(self.request("GET","/api/v1/me",second)[0],401)
        self.assertEqual(self.request("POST","/api/v1/login",body={
            "email":"owner@example.test","password":"very-long-owner-password"})[0],401)
        fresh=self.login("owner@example.test","new-super-secret-password")
        self.assertEqual(self.request("GET","/api/v1/me",fresh)[0],200)
        self.assertEqual(self.request("GET","/api/v1/me",self.other)[0],200)

    def test_session_revocation_keeps_current_token_only(self):
        extra=self.login("owner@example.test","very-long-owner-password")
        third=self.login("owner@example.test","very-long-owner-password")
        self.assertEqual(self.request("GET","/api/v1/sessions",self.owner)[1]["active_sessions"],3)
        status,response=self.request("POST","/api/v1/sessions/revoke-others",self.owner)
        self.assertEqual((status,response),(200,{"revoked":2}))
        self.assertEqual(self.request("GET","/api/v1/me",self.owner)[0],200)
        self.assertEqual(self.request("GET","/api/v1/me",extra)[0],401)
        self.assertEqual(self.request("GET","/api/v1/me",third)[0],401)
        self.assertEqual(self.request("GET","/api/v1/sessions",self.owner)[1]["active_sessions"],1)
        self.assertEqual(self.request("POST","/api/v1/sessions/revoke-others",self.other)[1],
                         {"revoked":0})
        self.assertEqual(self.request("POST","/api/v1/sessions/revoke-others")[0],401)

    def test_suggestions_respect_permissions_and_merge_calendar_conflicts(self):
        cid=self.calendar(self.owner)
        status,new=self.request("POST","/api/v1/calendars",self.owner,
            {"name":"Additional schedule"})
        self.assertEqual(status,201,new)
        second=new["id"]
        for calendar_id,start_at,end_at in [
            (cid,"2026-11-10T15:00:00Z","2026-11-10T16:00:00Z"),
            (second,"2026-11-10T16:00:00Z","2026-11-10T17:00:00Z")
        ]:
            self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
                "calendar_id":calendar_id,"title":"Private details",
                "start_at":start_at,"end_at":end_at})[0],201)
        base=("/api/v1/suggestions?calendar_ids="+cid+","+second+
              "&start=2026-11-10T06:00:00Z&end=2026-11-11T06:00:00Z"+
              "&tzid=America%2FChicago&duration_minutes=60")
        self.assertEqual(self.request("GET",base,self.other)[0],404)
        status,response=self.request("GET",base,self.owner)
        self.assertEqual(status,200,response)
        self.assertEqual(response["calendar_count"],2)
        self.assertEqual(response["slots"][0],{
            "start_at":"2026-11-10T17:00:00Z","end_at":"2026-11-10T18:00:00Z"})
        self.assertNotIn("Private details",str(response))
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,{
            "email":"other@example.test","role":"freebusy"})[0],200)
        single=base.replace(cid+","+second,cid)
        status,member=self.request("GET",single,self.other)
        self.assertEqual(status,200,member)
        self.assertIn("slots",member)
        self.assertNotIn("title",str(member))
        self.assertEqual(self.request("GET",base.replace("&duration_minutes=60",
                         "&duration_minutes=61"),self.owner)[0],400)
        self.assertEqual(self.request("GET",base.replace("America%2FChicago",
                         "Unknown%2FZone"),self.owner)[0],400)

    def test_suggestions_dismiss_all_day_and_handle_dst(self):
        cid=self.calendar(self.owner)
        self.assertEqual(self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Unavailable all day",
            "start_at":"2026-03-09T00:00:00Z","end_at":"2026-03-10T00:00:00Z",
            "all_day":True})[0],201)
        base=("/api/v1/suggestions?calendar_ids="+cid+
              "&start=2026-03-08T06:00:00Z&end=2026-03-10T05:00:00Z"+
              "&tzid=America%2FChicago&duration_minutes=60")
        status,response=self.request("GET",base,self.owner)
        self.assertEqual(status,200,response)
        self.assertEqual(response["slots"][0]["start_at"],"2026-03-08T14:00:00Z")
        self.assertTrue(all(x["start_at"].startswith("2026-03-08") for x in response["slots"]))
        self.assertEqual(self.request("GET",base.replace(
            "2026-03-10T05:00:00Z","2026-04-10T05:00:00Z"),self.owner)[0],400)

    def test_owner_only_portability_export_preserves_data_without_secrets(self):
        cid=self.calendar(self.owner)
        status,created=self.request("POST","/api/v1/events",self.owner,{
            "calendar_id":cid,"title":"Private planning notes",
            "description":"Keep sensitive data private",
            "start_at":"2026-11-10T15:00:00Z","end_at":"2026-11-10T16:00:00Z",
            "reminder_minutes":15,
            "recurrence":{"freq":"DAILY","interval":1,"count":3,"tzid":None}})
        self.assertEqual(status,201,created)
        eid=created["id"]
        self.assertEqual(self.request("POST","/api/v1/events/"+eid+"/exclusions",
            self.owner,{"occurrence_start_at":"2026-11-11T15:00:00Z","version":1})[0],200)
        self.assertEqual(self.request("POST","/api/v1/tasks",self.owner,{
            "calendar_id":cid,"title":"Private task","priority":1})[0],201)
        self.assertEqual(self.request("POST","/api/v1/calendars/"+cid+"/members",self.owner,{
            "email":"other@example.test","role":"read"})[0],200)
        status,exported=self.request("GET","/api/v1/export.json",self.owner)
        self.assertEqual(status,200,exported)
        self.assertEqual((exported["format"],exported["version"]),
                         ("goreecloud-calendar-data",1))
        personal=next(c for c in exported["calendars"] if c["id"]==cid)
        self.assertEqual(personal["events"][0]["title"],"Private planning notes")
        self.assertEqual(personal["events"][0]["reminder_minutes"],15)
        self.assertEqual(personal["events"][0]["recurrence"]["freq"],"DAILY")
        self.assertEqual(personal["events"][0]["excluded_occurrences"],
                         ["2026-11-11T15:00:00Z"])
        self.assertEqual(personal["tasks"][0]["priority"],1)
        self.assertNotIn("owner_id",personal)
        serial=json.dumps(exported)
        for secret in ("very-long-owner-password","password_hash","token_hash","salt",
                       "calendar_members","other@example.test"):
            self.assertNotIn(secret,serial)
        other=self.request("GET","/api/v1/export.json",self.other)
        self.assertEqual(other[0],200)
        self.assertFalse(any(c["id"]==cid for c in other[1]["calendars"]))
        self.assertNotIn("Private planning notes",json.dumps(other[1]))
        self.assertEqual(self.request("GET","/api/v1/export.json")[0],401)

    def test_logout_and_security_headers(self):
        self.assertEqual(self.request("GET","/api/v1/calendars")[0],401)
        self.assertEqual(self.request("POST","/api/v1/register",body={})[0],401)
        with urllib.request.urlopen(self.base+"/",timeout=3) as response:
            self.assertIn(b"GoreeCloud Calendar",response.read())
            self.assertIn("default-src 'none'",response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["X-Content-Type-Options"],"nosniff")
        self.assertEqual(self.request("POST","/api/v1/logout",self.owner)[0],200)
        self.assertEqual(self.request("GET","/api/v1/calendars",self.owner)[0],401)

if __name__=="__main__":unittest.main()
