# GoreeCloud Calendar native Android development client

This is an initial Android Activity written in Java with only Android SDK
runtime APIs, and no third-party Android UI libraries. It implements:

- Native login screen, HTTPS server validation, in-memory bearer session.
- Native agenda view with a date picker and upcoming daily events.
- Create one-hour events at 9 AM local time.
- Native task list, task completion toggles and task creation.
- Logout and automatic refresh through the self-hosted API.

A real Android debug APK build and device-level validation are required before
describing the client as installable/released. The target is Android API 26+.

Open the android directory in a compatible Android Studio, or use Gradle 8.13,
Android Gradle plugin 8.13 and Android SDK platform 35. Build debug using:

    gradle -p android assembleDebug

Remote server must provide HTTPS and a valid certificate. HTTP cleartext is
disabled, including for LAN hosts. Credentials and session token are not saved
to Android storage. Android does not yet implement offline edits, reminders,
home widgets, E2EE or full event editing.

Do not use a debug APK for confidential or production calendar data. When
delivering an APK, upload the standalone APK to the approved GoreeCloud
Artifacts location and verify its checksum, identity and signing metadata.
