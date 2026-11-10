"""Atomic, no-overwrite and validated SQLite snapshot for personal data recovery.

Backup exports plaintext. The caller must protect and encrypt destination storage
as needed; integrity_check verifies SQLite structure, not recoverability of every
future application feature or an external restore workflow.
"""
import os
import sqlite3
import tempfile
from pathlib import Path


def backup_database(source: str, destination: str) -> None:
    src = Path(source).expanduser()
    dest = Path(destination).expanduser()
    if src.is_symlink() or not src.is_file():
        raise ValueError("Source database must exist as a regular file")
    if not dest.parent.is_dir():
        raise ValueError("Destination parent directory does not exist")
    if dest.is_symlink() or dest.exists() or src.resolve() == dest.resolve():
        raise FileExistsError("Refusing to overwrite destination")
    handle, temporary = tempfile.mkstemp(prefix=".goreecloud-calendar-snapshot-", suffix=".tmp", dir=dest.parent)
    try:
        os.fchmod(handle, 0o600)
        os.close(handle)
        handle = -1
        with sqlite3.connect(str(src), timeout=30) as original, sqlite3.connect(temporary, timeout=30) as snapshot:
            original.backup(snapshot)
            check = snapshot.execute("PRAGMA integrity_check").fetchone()
            if check is None or check[0] != "ok":
                raise ValueError("Backup integrity check failed")
        verify = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(verify)
        finally:
            os.close(verify)
        # Hard link publishes atomically without clobbering a concurrently
        # created destination. Both paths are on the same filesystem.
        os.link(temporary, dest)
        directory_fd = os.open(str(dest.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if handle >= 0:
            os.close(handle)
        if os.path.exists(temporary):
            os.unlink(temporary)
