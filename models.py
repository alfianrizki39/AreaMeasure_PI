"""
Database models & helpers — SQLite via sqlite3.

Tabel `measurements`:
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    timestamp       TEXT    (ISO-8601, default localtime)
    total_area_cm2  REAL
    object_count    INTEGER
    areas_detail    TEXT    (JSON array of per-object areas)
    output_image    TEXT    (filename of output image in static/outputs/)
    status          TEXT    ('success' | 'failed')
"""

import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "measurements.db")


def get_db() -> sqlite3.Connection:
    """Return a connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the measurements table if it doesn't exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS measurements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            total_area_cm2  REAL,
            object_count    INTEGER DEFAULT 0,
            areas_detail    TEXT    DEFAULT '[]',
            output_image    TEXT,
            status          TEXT    NOT NULL CHECK (status IN ('success', 'failed'))
        )
        """
    )
    conn.commit()
    conn.close()


def insert_measurement(
    total_area_cm2: float | None,
    objects: list[dict] | None,
    output_image: str | None,
    status: str,
) -> int:
    """Insert a measurement row and return its id."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO measurements
           (total_area_cm2, object_count, areas_detail, output_image, status)
           VALUES (?, ?, ?, ?, ?)""",
        (
            total_area_cm2,
            len(objects) if objects else 0,
            json.dumps(objects) if objects else "[]",
            output_image,
            status,
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_all_measurements() -> list[dict]:
    """Return all measurements ordered by newest first."""
    conn = get_db()
    rows = conn.execute(
        """SELECT id, timestamp, total_area_cm2, object_count,
                  areas_detail, output_image, status
           FROM measurements ORDER BY id DESC"""
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        # Parse JSON string back to list
        try:
            d["areas_detail"] = json.loads(d["areas_detail"]) if d["areas_detail"] else []
        except (json.JSONDecodeError, TypeError):
            d["areas_detail"] = []
        results.append(d)
    return results
