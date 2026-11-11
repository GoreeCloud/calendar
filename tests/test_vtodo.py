"""Strict VTODO subset and roundtrip coverage."""
import unittest
from calendar_app.vtodo import parse_tasks,export_tasks
from calendar_app.ical import ImportErrorCalendar

class VTODOTests(unittest.TestCase):
    def test_roundtrip_utc_unicode_status_and_priorities(self):
        items=[
            {"id":"t1","title":"Café, milk; tea\nBring it","priority":1,"done":0,
             "due_at":"2026-11-10T16:15:00Z"},
            {"id":"t2","title":"Done","priority":4,"done":1,"due_at":None},
        ]
        exported=export_tasks(items)
        self.assertTrue(exported.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        parsed=parse_tasks(exported)
        self.assertEqual([(x["title"],x["priority"],x["done"],x["due_at"])
                          for x in parsed],
                         [(x["title"],x["priority"],x["done"],x["due_at"])
                          for x in items])
        self.assertIn("PRIORITY:9",exported)

    def test_timezone_due_is_normalized(self):
        source=("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VTODO\r\n"
                "UID:1@example.test\r\nSUMMARY:Time zone check\r\n"
                "DUE;TZID=America/Chicago:20261110T101500\r\n"
                "END:VTODO\r\nEND:VCALENDAR\r\n")
        self.assertEqual(parse_tasks(source)[0]["due_at"],"2026-11-10T16:15:00Z")

    def test_unknown_fields_duplicates_and_all_day_due_rejected(self):
        base=("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VTODO\r\n"
              "UID:x@example.test\r\nSUMMARY:Work\r\nEND:VTODO\r\nEND:VCALENDAR\r\n")
        cases=[
            base.replace("END:VTODO","DESCRIPTION:Not supported\r\nEND:VTODO"),
            base.replace("END:VTODO","DUE;VALUE=DATE:20261110\r\nEND:VTODO"),
            base.replace("END:VTODO","STATUS:CANCELLED\r\nEND:VTODO"),
            base.replace("END:VTODO","RRULE:FREQ=DAILY\r\nEND:VTODO"),
            base.replace("END:VTODO","UID:duplicate\r\nEND:VTODO"),
            base.replace("BEGIN:VTODO","BEGIN:VEVENT"),
            base.replace("END:VCALENDAR","BEGIN:VTODO\r\nUID:x@example.test\r\n"
                         "SUMMARY:Duplicate\r\nEND:VTODO\r\nEND:VCALENDAR"),
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ImportErrorCalendar):
                    parse_tasks(case)

    def test_title_free_importability_report_distinguishes_tasks_preview(self):
        from calendar_app.vtodo import task_importability_report
        source=("BEGIN:VCALENDAR\\r\\nVERSION:2.0\\r\\nBEGIN:VTODO\\r\\n"
                "UID:urn:uuid:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa\\r\\n"
                "DTSTAMP:20261111T120000Z\\r\\nSEQUENCE:3\\r\\n"
                "CLASS:PRIVATE\\r\\nSTATUS:NEEDS-ACTION\\r\\n"
                "SUMMARY:PRIVATE TASK TITLE MUST NOT LEAK\\r\\n"
                "DUE;VALUE=DATE:20261112\\r\\nEND:VTODO\\r\\nEND:VCALENDAR\\r\\n")
        report=task_importability_report(source)
        self.assertEqual(report,{"importable":False,"reason_codes":[
            "classification_not_supported","date_only_due_not_supported",
            "sequence_not_supported"]})
        self.assertNotIn("PRIVATE TASK TITLE",str(report))
        self.assertNotIn("aaaaaaaa",str(report))
        simple=("BEGIN:VCALENDAR\\r\\nVERSION:2.0\\r\\nBEGIN:VTODO\\r\\n"
                "UID:good@example.invalid\\r\\nSUMMARY:Visible locally only\\r\\n"
                "END:VTODO\\r\\nEND:VCALENDAR\\r\\n")
        self.assertEqual(task_importability_report(simple),
                         {"importable":True,"reason_codes":[]})
        self.assertEqual(task_importability_report(simple.replace(
            "END:VTODO","ATTENDEE:mailto:private@example.invalid\\r\\nEND:VTODO")),
            {"importable":False,"reason_codes":["invalid_or_unsupported_ics"]})
        self.assertEqual(task_importability_report("bad input"),
                         {"importable":False,"reason_codes":["invalid_or_unsupported_ics"]})

    def test_utf8_folded_lines_roundtrip(self):
        title="Task "+("é"*90)
        serialized=export_tasks([{"id":"utf8","title":title,"priority":3,
                                  "done":0,"due_at":None}])
        self.assertTrue(all(len(line.encode("utf-8"))<=75
                            for line in serialized.split("\r\n") if line))
        self.assertEqual(parse_tasks(serialized)[0]["title"],title)

if __name__=="__main__":
    unittest.main()
