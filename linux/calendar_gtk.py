#!/usr/bin/env python3
"""GoreeCloud Calendar native GTK4 Linux development client."""
import datetime as dt
import json
import threading
import urllib.parse
import urllib.request
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

def origin(text):
    value=urllib.parse.urlsplit(text.strip().rstrip("/"))
    if value.username or value.password or value.path not in ("","/") or value.query or value.fragment:
        raise ValueError("Enter a calendar server origin, without path or credentials")
    if value.scheme=="https" and value.hostname:
        return text.strip().rstrip("/")
    if value.scheme=="http" and value.hostname in ("localhost","127.0.0.1","::1"):
        return text.strip().rstrip("/")
    raise ValueError("HTTPS is required except on loopback")

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Block HTTP redirects; never forward an authorization token to a new origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_NO_REDIRECTS=urllib.request.build_opener(_NoRedirect())

class CalendarClient(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.goreecloud.Calendar")
        self.token=None
        self.api_url=None
        self.calendars=[]

    def do_activate(self):
        if getattr(self,"window",None):
            self.window.present();return
        css=Gtk.CssProvider()
        css.load_from_data(b"""window{background:#f5f7fc;color:#182340}
        .surface{background:white;border:1px solid #e1e6f0;border-radius:18px;padding:22px}
        .title{font-size:26px;font-weight:800}.hint{color:#64718b}
        button.suggested-action{background:#4d5cc8;color:white;border-radius:12px;padding:9px}""")
        display=Gdk.Display.get_default()
        if display:Gtk.StyleContext.add_provider_for_display(display,css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window=Gtk.ApplicationWindow(application=self,title="GoreeCloud Calendar")
        self.window.set_default_size(900,630)
        self.show_login()
        self.window.present()

    def box(self,vertical=True):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,spacing=14)
        return box

    def label(self,text,kind=""):
        obj=Gtk.Label(label=text,xalign=0)
        if kind:obj.add_css_class(kind)
        return obj

    def show_login(self):
        form=self.box()
        form.set_margin_top(40);form.set_margin_bottom(40)
        form.set_margin_start(40);form.set_margin_end(40)
        form.append(self.label("GoreeCloud Calendar","title"))
        form.append(self.label("Your time. Your cloud.","hint"))
        form.append(self.label("Server URL"))
        self.server_entry=Gtk.Entry()
        self.server_entry.set_text("http://127.0.0.1:8787")
        form.append(self.server_entry)
        form.append(self.label("Email"))
        self.email=Gtk.Entry();self.email.set_placeholder_text("you@example.com")
        form.append(self.email)
        form.append(self.label("Password"))
        self.password=Gtk.PasswordEntry();self.password.set_show_peek_icon(True)
        form.append(self.password)
        self.message=self.label("")
        form.append(self.message)
        button=Gtk.Button(label="Sign in");button.add_css_class("suggested-action")
        button.connect("clicked",self.login)
        form.append(button)
        self.window.set_child(form)

    def request(self,method,path,body=None,token=None):
        headers={"Accept":"application/json"}
        if token:headers["Authorization"]="Bearer "+token
        if body is not None:headers["Content-Type"]="application/json"
        url=self.api_url+"/api/v1"+path
        req=urllib.request.Request(url,method=method,headers=headers,
          data=json.dumps(body).encode() if body is not None else None)
        with _NO_REDIRECTS.open(req,timeout=12) as response:
            return json.load(response)

    def run_async(self,task,done):
        def worker():
            try:
                result=task()
                GLib.idle_add(done,result)
            except Exception as error:
                GLib.idle_add(self.error,str(error))
        threading.Thread(target=worker,daemon=True).start()

    def error(self,message):
        self.message.set_text("Unable to complete request: "+message[:140])
        return False

    def login(self,_button):
        try:self.api_url=origin(self.server_entry.get_text())
        except ValueError as error:
            self.error(str(error));return
        email=self.email.get_text()
        password=self.password.get_text()
        self.message.set_text("Connecting…")
        def done(data):
            self.token=data["token"]
            self.password.set_text("")
            self.show_calendar()
            self.load_day()
            return False
        self.run_async(lambda:self.request("POST","/login",{"email":email,"password":password}),done)

    def show_calendar(self):
        outer=self.box()
        outer.set_margin_top(20);outer.set_margin_bottom(20)
        outer.set_margin_start(20);outer.set_margin_end(20)
        top=self.box(False)
        top.append(self.label("GoreeCloud Calendar","title"))
        spacer=self.label("");spacer.set_hexpand(True);top.append(spacer)
        add=Gtk.Button(label="＋ New event");add.add_css_class("suggested-action")
        add.connect("clicked",lambda *_:self.create_event())
        top.append(add)
        logout=Gtk.Button(label="Sign out")
        logout.connect("clicked",self.logout)
        top.append(logout)
        outer.append(top)
        main=self.box(False)
        self.date_picker=Gtk.Calendar()
        self.date_picker.connect("day-selected",lambda *_:self.load_day())
        main.append(self.date_picker)
        right=self.box()
        right.set_hexpand(True)
        self.day_title=self.label("Your schedule","title");right.append(self.day_title)
        self.message=self.label("");right.append(self.message)
        scroll=Gtk.ScrolledWindow();scroll.set_vexpand(True)
        self.event_list=Gtk.ListBox()
        scroll.set_child(self.event_list)
        right.append(scroll);main.append(right);outer.append(main)
        self.window.set_child(outer)

    def selected_date(self):
        d=self.date_picker.get_date()
        return dt.date(d.get_year(),d.get_month(),d.get_day_of_month())

    def load_day(self):
        d=self.selected_date()
        self.day_title.set_text(d.strftime("%A, %B %d"))
        self.message.set_text("Loading events…")
        start=dt.datetime.combine(d,dt.time.min).astimezone(dt.timezone.utc)
        end=(dt.datetime.combine(d+dt.timedelta(days=1),dt.time.min)).astimezone(dt.timezone.utc)
        def work():
            qs=urllib.parse.urlencode({"start":start.isoformat(),"end":end.isoformat()})
            return (self.request("GET","/calendars",token=self.token)["calendars"],
                    self.request("GET","/events?"+qs,token=self.token)["events"])
        def done(data):
            self.calendars,events=data
            child=self.event_list.get_first_child()
            while child:
                next_child=child.get_next_sibling()
                self.event_list.remove(child);child=next_child
            self.message.set_text("")
            if not events:self.event_list.append(self.label("Nothing scheduled. Enjoy the space.","hint"))
            for event in events:
                when=dt.datetime.fromisoformat(event["start_at"].replace("Z","+00:00")).astimezone()
                row=self.label(when.strftime("%I:%M %p")+"  •  "+event["title"])
                row.set_margin_top(12);row.set_margin_bottom(12)
                self.event_list.append(row)
            return False
        self.run_async(work,done)

    def create_event(self):
        if not self.calendars:
            self.error("No calendars available");return
        d=self.selected_date()
        dialog=Gtk.Window(transient_for=self.window,modal=True,title="Add event")
        dialog.set_default_size(430,270)
        area=self.box()
        area.set_margin_top(22);area.set_margin_bottom(22)
        area.set_margin_start(22);area.set_margin_end(22)
        area.append(self.label(d.strftime("New event • %B %d"),"title"))
        name=Gtk.Entry();name.set_placeholder_text("Event title");area.append(name)
        area.append(self.label("Preview: 9 AM to 10 AM, local time.","hint"))
        info=self.label("");area.append(info)
        save=Gtk.Button(label="Save event");save.add_css_class("suggested-action")
        def submit(_):
            if not name.get_text().strip():
                info.set_text("Enter a title.");return
            start=dt.datetime.combine(d,dt.time(9)).astimezone(dt.timezone.utc)
            end=dt.datetime.combine(d,dt.time(10)).astimezone(dt.timezone.utc)
            data={"calendar_id":self.calendars[0]["id"],"title":name.get_text(),
                  "start_at":start.isoformat(),"end_at":end.isoformat()}
            def complete(_result):
                dialog.close();self.load_day();return False
            info.set_text("Saving…")
            self.run_async(lambda:self.request("POST","/events",data,token=self.token),complete)
        save.connect("clicked",submit);area.append(save)
        dialog.set_child(area);dialog.present()

    def logout(self,_button):
        old=self.token
        self.token=None
        self.show_login()
        if old:
            self.run_async(lambda:self.request("POST","/logout",token=old),lambda _:False)

if __name__=="__main__":
    raise SystemExit(CalendarClient().run())
