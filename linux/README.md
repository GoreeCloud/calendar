# GoreeCloud Calendar — Linux GTK4 development client

Native GTK4 desktop code lives here. Requires Linux desktop packages python3-gi
and gir1.2-gtk-4.0. Run via the distro Python interpreter:

    /usr/bin/python3 linux/calendar_gtk.py

Install a per-user desktop launcher:

    sh linux/install.sh

The client provides a native sign-in screen, date picker, read-only day list and
event creation with selectable start hour, minute, duration (15–480 minutes) and optional 15-minute reminder. A Tasks tab lists authorized tasks, permits completion toggles only for editable calendars and supports priority-based task creation. Bearer tokens are held in
memory and not written to disk. Server origins must use HTTPS, except HTTP to
loopback for local development. Do not expose the self-hosted HTTP server publicly.

Editing existing events and tasks, offline storage, OS notification delivery, accessibility review, distro
package creation and actual Linux runtime acceptance are still required.
