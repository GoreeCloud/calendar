#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 -c 'import gi;gi.require_version("Gtk","4.0");from gi.repository import Gtk' || {
  echo 'Install python3-gi and gir1.2-gtk-4.0 first.' >&2
  exit 1
}
app_dir="$HOME/.local/share/goreecloud-calendar"
desktop_dir="$HOME/.local/share/applications"
mkdir -p "$app_dir" "$desktop_dir"
install -m 0644 "$dir/calendar_gtk.py" "$app_dir/calendar_gtk.py"
cat > "$desktop_dir/com.goreecloud.Calendar.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=GoreeCloud Calendar
Comment=Self-hosted personal calendar
Exec=/usr/bin/python3 $app_dir/calendar_gtk.py
Terminal=false
Categories=Office;Calendar;
EOF
echo "Installed GoreeCloud Calendar in your user applications directory."
