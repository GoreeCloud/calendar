"""Static browser contract checks: selectors, labels and script safety.

These tests do not substitute for end-to-end interaction or accessibility audits.
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

WEB=Path(__file__).resolve().parents[1]/"web"

class BrowserMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.labels=[]
        self.scripts=[]
        self.inline_handlers=[]
        self.external_assets=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag=="label" and "for" in values:
            self.labels.append(values["for"])
        if tag=="script":
            self.scripts.append(values.get("src"))
        for key,_value in attrs:
            if key.lower().startswith("on"):
                self.inline_handlers.append((tag,key))
        if tag=="link" and values.get("rel")=="stylesheet":
            self.external_assets.append(values.get("href"))

class WebContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(WEB/"index.html").read_text(encoding="utf-8")
        cls.js=(WEB/"app.js").read_text(encoding="utf-8")
        cls.parser=BrowserMarkup()
        cls.parser.feed(cls.html)

    def test_unique_ids_and_existing_js_references(self):
        ids=self.parser.ids
        self.assertEqual(len(ids),len(set(ids)),"HTML IDs must be unique")
        references=set(re.findall(r'\$\("([\w-]+)"\)',self.js))
        self.assertFalse(references-set(ids),
            "JS references nonexistent HTML IDs: "+str(references-set(ids)))

    def test_explicit_labels_resolve(self):
        self.assertFalse(set(self.parser.labels)-set(self.parser.ids))
        for required in ("availability-calendar","availability-date",
                         "settings-calendar-name","task-priority"):
            self.assertIn(required,self.parser.labels)

    def test_no_inline_execution_or_remote_browser_assets(self):
        self.assertEqual(self.parser.inline_handlers,[])
        self.assertEqual(self.parser.scripts,["/app.js"])
        self.assertEqual(self.parser.external_assets,["/styles.css"])

    def test_privacy_controls_are_visible_in_markup(self):
        for control in ("availability-dialog","calendar-settings-dialog",
                        "share-role","task-priority","event-reminder"):
            self.assertIn(control,self.parser.ids)
        self.assertIn('value="freebusy"',self.html)
        self.assertIn("Unscheduled",self.js)
        self.assertIn("not a public booking link",self.html)

if __name__=="__main__":
    unittest.main()
