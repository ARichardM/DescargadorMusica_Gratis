"""Historial local de archivos terminados. Una conexión SQLite por operación."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


DEFAULT_PATH = Path(__file__).resolve().parent / "datos" / "historial.sqlite3"
PAGE_SIZE = 100


class DownloadHistory:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)

    def record(self, entry):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        filename = str(Path(entry["filename"]).resolve())
        title = entry.get("title") or Path(filename).stem
        artist = entry.get("artist") or ""
        with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                filename TEXT NOT NULL,
                format TEXT NOT NULL,
                quality TEXT NOT NULL,
                source_url TEXT NOT NULL,
                state TEXT NOT NULL,
                search_text TEXT NOT NULL
            )""")
            cursor = connection.execute("""INSERT INTO downloads
                (created_at, title, artist, filename, format, quality, source_url, state, search_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                    datetime.now(timezone.utc).isoformat(), title, artist, filename,
                    entry.get("format") or Path(filename).suffix.lstrip(".").upper(),
                    entry.get("quality", ""), entry.get("source_url", ""),
                    entry.get("state", "downloaded"),
                    " ".join((title, artist, filename)).casefold()))
            return cursor.lastrowid

    def page(self, search="", offset=0, limit=PAGE_SIZE):
        if not self.path.is_file():
            return [], 0
        offset, limit = max(0, int(offset)), min(PAGE_SIZE, max(1, int(limit)))
        where = "WHERE instr(search_text, ?) > 0" if search.strip() else ""
        values = (search.strip().casefold(),) if where else ()
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            total = connection.execute(f"SELECT COUNT(*) FROM downloads {where}", values).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM downloads {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                (*values, limit, offset)).fetchall()
        return [dict(row) for row in rows], total
