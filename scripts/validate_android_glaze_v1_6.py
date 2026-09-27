#!/usr/bin/env python3
"""Fail-closed validation for GoreeCloud Calendar Android GLAZE UI V1.6 adoption."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "clients/android/app/src/main/java/com/goreecloud/calendar/GlazeCalendarTheme.kt"
MAIN = ROOT / "clients/android/app/src/main/java/com/goreecloud/calendar/MainActivity.kt"
READ_CONTRACT = ROOT / "clients/android/app/src/main/java/com/goreecloud/calendar/CalendarReadContract.kt"
RESPONSE_CONTRACT = ROOT / "clients/android/app/src/main/java/com/goreecloud/calendar/CalendarResponseContract.kt"
MANIFEST = ROOT / "clients/android/app/src/main/AndroidManifest.xml"
DOC = ROOT / "docs/glaze-ui-v1.6-android-adoption.md"
ANDROID_README = ROOT / "clients/android/README.md"
VERSION = "1.6.0"
REVISION = "a7180679ea851389e0f3004515f9a25f420e716d"
ROLLBACK_VERSION = "1.5.1"


def require(text: str, fragment: str, label: str) -> None:
    if fragment not in text:
        raise SystemExit(f"{label}: required fragment missing: {fragment!r}")


def forbid(text: str, fragment: str, label: str) -> None:
    if fragment in text:
        raise SystemExit(f"{label}: forbidden fragment present: {fragment!r}")


def main() -> None:
    theme = THEME.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    read_contract = READ_CONTRACT.read_text(encoding="utf-8")
    response_contract = RESPONSE_CONTRACT.read_text(encoding="utf-8")
    manifest = MANIFEST.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    android_readme = ANDROID_README.read_text(encoding="utf-8")

    require(theme, f'VERSION = "{VERSION}"', "theme")
    require(theme, f'REFERENCE_REVISION = "{REVISION}"', "theme")
    require(theme, f'ROLLBACK_VERSION = "{ROLLBACK_VERSION}"', "theme")
    require(theme, 'ADOPTION_STATE = "ADOPTION_IN_PROGRESS"', "theme")
    for flag in (
        "OPTICAL_ENGINE_ACCEPTED",
        "REDUCED_TRANSPARENCY_ACCEPTED",
        "INCREASED_CONTRAST_ACCEPTED",
        "PHYSICAL_DEVICE_ACCEPTED",
        "HUMAN_VISUAL_ACCEPTED",
    ):
        require(theme, f"{flag} = false", "theme")
    require(main_source, "GlazeCalendarTheme", "MainActivity")
    require(doc, "Radicale/CalDAV remains the sole authoritative calendar service", "documentation")
    require(doc, REVISION, "documentation")
    require(doc, "Shared V1.6 qualification does not establish Calendar-local acceptance", "documentation")

    require(read_contract, 'responseAcceptance = CalendarReadContractState.SOURCE_READY', "read contract")
    require(read_contract, 'nativeIdentitySession = CalendarReadContractState.IDENTITY_BLOCKED', "read contract")
    require(read_contract, 'networkTransport = CalendarReadContractState.TRANSPORT_BLOCKED', "read contract")

    for fragment in (
        'EVENTS_SCHEMA = "goreecloud.calendar.events.v1"',
        'BUSY_SCHEMA = "goreecloud.calendar.busy.v1"',
        "EVENTS_TOP_LEVEL_FIELDS",
        "BUSY_INTERVAL_FIELDS",
        "returned does not match events size",
        "busy range does not match request",
        "intervals are overlapping or not strictly ordered",
        "unexpectedFields",
    ):
        require(response_contract, fragment, "response contract")
    for forbidden in (
        "HttpURLConnection",
        "OkHttp",
        "android.net.",
        "java.net.http",
    ):
        forbid(response_contract, forbidden, "response contract")

    forbid(manifest, "android.permission.INTERNET", "manifest")
    forbid(manifest, "android.permission.READ_CALENDAR", "manifest")
    forbid(manifest, "android.permission.WRITE_CALENDAR", "manifest")
    require(manifest, 'android:allowBackup="false"', "manifest")

    require(android_readme, "Calendar response acceptance", "Android README")
    require(android_readme, "no network authority", "Android README")
    require(android_readme, "GLAZE UI V1.6", "Android README")

    print(
        "Calendar Android GLAZE UI V1.6 adoption validated: "
        f"version={VERSION} revision={REVISION} rollback={ROLLBACK_VERSION} "
        "responseAcceptance=source-ready network=false providerAuthority=false "
        "consumerAcceptance=false production=false"
    )


if __name__ == "__main__":
    main()
