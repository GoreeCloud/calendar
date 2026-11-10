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
        bad=base % "RRULE:FREQ=DAILY\\n"
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
