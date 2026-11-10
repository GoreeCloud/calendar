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


def verify_backup(path: str) -> bool:
    """Validate SQLite file structure without modifying or creating a database."""
    from urllib.parse import quote

    source = Path(path).expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError("Backup must exist as a regular file")
    source = source.resolve()
    uri = "file:" + quote(str(source), safe="/") + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=20) as connection:
            check = connection.execute("PRAGMA integrity_check").fetchone()
            if check is None or check[0] != "ok":
                raise ValueError("Backup integrity check failed")
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"users","sessions","calendars","events","tasks"}
            if not required <= tables:
                raise ValueError("Backup is not a GoreeCloud Calendar database")
            return True
    except sqlite3.DatabaseError:
        raise ValueError("Backup cannot be read as a valid SQLite database") from None


def restore_database(snapshot: str, destination: str) -> None:
    """Copy an independently verified snapshot to a NEW database pathname.

    The destination must not exist. Source is never modified; the temporary
    copy is verified before a same-filesystem, atomic no-clobber publication.
    This is a restore-to-new-path workflow, never a live in-place replacement.
    """
    import shutil

    source=Path(snapshot).expanduser()
    dest=Path(destination).expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError("Snapshot must exist as a regular file")
    if not dest.parent.is_dir():
        raise ValueError("Restore destination parent directory does not exist")
    if dest.is_symlink() or dest.exists() or source.resolve()==dest.resolve():
        raise FileExistsError("Refusing to overwrite destination")
    verify_backup(str(source))
    handle,temporary=tempfile.mkstemp(prefix=".goreecloud-calendar-restore-",
                                       suffix=".tmp",dir=dest.parent)
    try:
        os.fchmod(handle,0o600)
        # Copy the snapshot, not a live SQLite database; the copied content is
        # verified after closing and flushing the file.
        with source.open("rb") as inp, os.fdopen(handle,"wb") as out:
            handle=-1
            shutil.copyfileobj(inp,out,length=1024*1024)
            out.flush()
            os.fsync(out.fileno())
        verify_backup(temporary)
        os.link(temporary,dest)
        directory_fd=os.open(str(dest.parent),os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if handle>=0:
            os.close(handle)
        if os.path.exists(temporary):
            os.unlink(temporary)
