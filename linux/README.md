# GoreeCloud Calendar — Linux GTK4 development client

Native GTK4 desktop code lives here. Requires Linux desktop packages python3-gi
and gir1.2-gtk-4.0. Run via the distro Python interpreter:

    /usr/bin/python3 linux/calendar_gtk.py

Install a per-user desktop launcher:

    sh linux/install.sh

The client provides a native sign-in screen, date picker, read-only day list and
a simple event creation workflow (9–10 AM local time). Bearer tokens are held in
memory and not written to disk. Server origins must use HTTPS, except HTTP to
loopback for local development. Do not expose the self-hosted HTTP server publicly.

More event editing, offline storage, reminders, accessibility review, distro
package creation and actual Linux runtime acceptance are still required.
