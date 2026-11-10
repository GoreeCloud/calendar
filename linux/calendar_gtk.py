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
        right.append(scroll);main.append(right)
        tabs=Gtk.Notebook()
        tabs.append_page(main,Gtk.Label(label="Calendar"))
        tasks_page=self.box()
        tasks_page.set_margin_top(16)
        tasks_header=self.box(False)
        tasks_header.append(self.label("Tasks","title"))
        task_spacer=self.label("");task_spacer.set_hexpand(True);tasks_header.append(task_spacer)
        add_task=Gtk.Button(label="＋ New task")
        add_task.connect("clicked",lambda *_:self.create_task())
        tasks_header.append(add_task)
        tasks_page.append(tasks_header)
        self.task_message=self.label("")
        tasks_page.append(self.task_message)
        task_scroll=Gtk.ScrolledWindow();task_scroll.set_vexpand(True)
        self.task_list=Gtk.ListBox()
        task_scroll.set_child(self.task_list)
        tasks_page.append(task_scroll)
        tabs.append_page(tasks_page,Gtk.Label(label="Tasks"))
        tabs.connect("switch-page",lambda _tabs,_page,index:
                     self.load_tasks() if index==1 else None)
        outer.append(tabs)
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

    def load_tasks(self):
        token=self.token
        if not token:
            return
        self.task_message.set_text("Loading tasks…")
        def work():
            calendars=self.request("GET","/calendars",token=token)["calendars"]
            tasks=self.request("GET","/tasks",token=token)["tasks"]
            return calendars,tasks
        def done(data):
            if self.token!=token:
                return False
            calendars,tasks=data
            self.calendars=calendars
            editable={c["id"] for c in calendars if c.get("role") in ("owner","edit")}
            child=self.task_list.get_first_child()
            while child:
                next_child=child.get_next_sibling()
                self.task_list.remove(child)
                child=next_child
            self.task_message.set_text("")
            if not tasks:
                self.task_list.append(self.label("No tasks yet.","hint"))
            for task in sorted(tasks,key=lambda t:(int(t["done"]),int(t.get("priority",3)),
                                                 t.get("due_at") or "9999")):
                row=self.box(False)
                checkbox=Gtk.CheckButton()
                checkbox.set_active(bool(task["done"]))
                checkbox.set_sensitive(task["calendar_id"] in editable)
                checkbox.set_tooltip_text("Read-only calendar" if task["calendar_id"] not in editable
                                          else "Mark task complete")
                heading=task["title"]+"  ·  P"+str(task.get("priority",3))
                if task.get("due_at"):
                    due=dt.datetime.fromisoformat(task["due_at"].replace("Z","+00:00")).astimezone()
                    heading+="  ·  Due "+due.strftime("%b %d %I:%M %p")
                label=self.label(heading)
                label.set_wrap(True)
                label.set_hexpand(True)
                row.append(checkbox)
                row.append(label)
                def toggle(control,tid=task["id"]):
                    target=control.get_active()
                    self.run_async(
                        lambda:self.request("PATCH","/tasks/"+tid,{"done":target},token=token),
                        lambda _:self.load_tasks() or False)
                checkbox.connect("toggled",toggle)
                row.set_margin_top(8);row.set_margin_bottom(8)
                self.task_list.append(row)
            return False
        self.run_async(work,done)

    def create_task(self):
        editable=[c for c in self.calendars if c.get("role") in ("owner","edit")]
        if not editable:
            self.task_message.set_text("No editable calendar is available.")
            return
        dialog=Gtk.Window(transient_for=self.window,modal=True,title="New task")
        dialog.set_default_size(380,300)
        content=self.box()
        content.set_margin_top(20);content.set_margin_bottom(20)
        content.set_margin_start(20);content.set_margin_end(20)
        content.append(self.label("New task","title"))
        name=Gtk.Entry();name.set_placeholder_text("What needs doing?")
        content.append(name)
        content.append(self.label("Priority"))
        priority=Gtk.ComboBoxText()
        for caption in ("P1 · Urgent","P2 · High","P3 · Normal","P4 · Low"):
            priority.append_text(caption)
        priority.set_active(2)
        content.append(priority)
        message=self.label("")
        content.append(message)
        save=Gtk.Button(label="Create task")
        save.add_css_class("suggested-action")
        def submit(_):
            title=name.get_text().strip()
            if not title:
                message.set_text("Enter a task name.")
                return
            payload={"calendar_id":editable[0]["id"],"title":title,
                     "priority":priority.get_active()+1}
            message.set_text("Saving…")
            def done(_result):
                dialog.close()
                self.load_tasks()
                return False
            self.run_async(lambda:self.request("POST","/tasks",payload,token=self.token),done)
        save.connect("clicked",submit)
        content.append(save)
        dialog.set_child(content)
        dialog.present()

    def create_event(self):
        editable=[c for c in self.calendars if c.get("role","owner") in ("owner","edit")]
        if not editable:
            self.error("No editable calendar available")
            return
        date=self.selected_date()
        dialog=Gtk.Window(transient_for=self.window,modal=True,title="New event")
        dialog.set_default_size(430,430)
        area=self.box()
        area.set_margin_top(22);area.set_margin_bottom(22)
        area.set_margin_start(22);area.set_margin_end(22)
        area.append(self.label(date.strftime("New event • %B %d"),"title"))
        area.append(self.label("Event title"))
        name=Gtk.Entry()
        name.set_placeholder_text("What's scheduled?")
        area.append(name)
        time_row=self.box(False)
        start_hour=Gtk.SpinButton.new_with_range(0,23,1)
        start_hour.set_value(9)
        start_minute=Gtk.SpinButton.new_with_range(0,59,5)
        start_minute.set_value(0)
        time_row.append(self.label("Start hour (24h)"))
        time_row.append(start_hour)
        time_row.append(self.label("Minute"))
        time_row.append(start_minute)
        area.append(time_row)
        duration_row=self.box(False)
        duration=Gtk.SpinButton.new_with_range(15,480,15)
        duration.set_value(60)
        duration_row.append(self.label("Duration (minutes)"))
        duration_row.append(duration)
        area.append(duration_row)
        remind=Gtk.CheckButton(label="Remind me 15 minutes before")
        area.append(remind)
        info=self.label("")
        area.append(info)
        save=Gtk.Button(label="Create event")
        save.add_css_class("suggested-action")
        def submit(_):
            title=name.get_text().strip()
            if not title:
                info.set_text("Enter an event title.")
                return
            hour=int(start_hour.get_value())
            minute=int(start_minute.get_value())
            duration_minutes=int(duration.get_value())
            if not 0<=hour<24 or not 0<=minute<60 or duration_minutes<15:
                info.set_text("Invalid start time or event duration.")
                return
            local_start=dt.datetime.combine(date,dt.time(hour,minute)).astimezone()
            # Absolute duration prevents an unintended hour difference at DST.
            begins=local_start.astimezone(dt.timezone.utc)
            ends=begins+dt.timedelta(minutes=duration_minutes)
            payload={"calendar_id":editable[0]["id"],"title":title,
                     "start_at":begins.isoformat(),"end_at":ends.isoformat()}
            if remind.get_active():
                payload["reminder_minutes"]=15
            info.set_text("Saving event…")
            def done(_result):
                dialog.close()
                self.load_day()
                return False
            self.run_async(lambda:self.request("POST","/events",payload,token=self.token),done)
        save.connect("clicked",submit)
        area.append(save)
        dialog.set_child(area)
        dialog.present()

    def logout(self,_button):
        old=self.token
        self.token=None
        self.show_login()
        if old:
            self.run_async(lambda:self.request("POST","/logout",token=old),lambda _:False)

if __name__=="__main__":
    raise SystemExit(CalendarClient().run())
