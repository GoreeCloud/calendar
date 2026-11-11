#!/usr/bin/env python3
"""Owned-Xvfb native Calendar GTK4 UI smoke; no network or personal data.

Only synthetic labels and disposable XDG paths are used. An unexpected
HTTP invocation raises rather than connecting to a real calendar server.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

if not os.environ.get("DISPLAY"):
    raise RuntimeError("Calendar native GTK smoke requires an isolated display")

os.environ["GDK_BACKEND"] = "x11"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calendar_gtk import CalendarClient, origin
from gi.repository import Gtk


def blocked(*_args, **_kwargs):
    raise AssertionError("Native Calendar UI smoke must never make network requests")


def descendants(widget):
    yield widget
    child = widget.get_first_child()
    while child is not None:
        yield from descendants(child)
        child = child.get_next_sibling()


def main():
    with tempfile.TemporaryDirectory(prefix="goreecloud-calendar-ui-smoke-") as folder:
        os.environ["XDG_DATA_HOME"] = folder
        os.environ["XDG_CONFIG_HOME"] = folder
        app = CalendarClient()
        app.request = blocked
        app.run_async = blocked
        assert app.register(None), "GTK application must register"
        try:
            app.activate()
            window = app.window
            assert isinstance(window, Gtk.ApplicationWindow)
            assert window.get_title() == "GoreeCloud Calendar"
            assert isinstance(app.server_entry, Gtk.Entry)
            assert isinstance(app.password, Gtk.PasswordEntry)
            assert app.server_entry.get_text() == "http://127.0.0.1:8787"
            assert app.token is None

            assert origin("http://127.0.0.1:8787") == "http://127.0.0.1:8787"
            assert origin("https://calendar.example.invalid") == "https://calendar.example.invalid"
            for unsafe in (
                "http://not-loopback.example.invalid",
                "http://user:pass@127.0.0.1",
                "https://calendar.example.invalid/private",
                "https://calendar.example.invalid/?query=1",
            ):
                try:
                    origin(unsafe)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Unsafe Calendar origin accepted")

            app.server_entry.set_text("http://not-loopback.example.invalid")
            app.login(None)
            assert "HTTPS is required" in app.message.get_text()
            assert app.token is None, "Invalid origin must not log in"
            app.server_entry.set_text("http://127.0.0.1:8787")

            # Rendering the two native panes must not start a backend request.
            app.show_calendar()
            widgets = list(descendants(window))
            notebooks = [widget for widget in widgets if isinstance(widget, Gtk.Notebook)]
            assert len(notebooks) == 1 and notebooks[0].get_n_pages() == 2
            assert isinstance(app.date_picker, Gtk.Calendar)
            assert isinstance(app.event_list, Gtk.ListBox)
            assert isinstance(app.task_list, Gtk.ListBox)
            assert app.token is None

            app.show_login()
            assert isinstance(app.password, Gtk.PasswordEntry)
            assert app.token is None
            print("CALENDAR_GTK4_LOGIN_ORIGIN_AND_NATIVE_PANES_SMOKE_PASS")
        finally:
            if getattr(app, "window", None):
                app.window.close()
            app.quit()


if __name__ == "__main__":
    main()
