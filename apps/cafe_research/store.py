"""Persistent, source-aware storage for cafe research."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def database_path() -> Path:
    configured = os.environ.get("CAFE_RESEARCH_DB_PATH", "data/cafe-research.sqlite3")
    path = Path(configured).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize() -> None:
    with closing(_connect()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cafe_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                osm_type TEXT,
                osm_id INTEGER,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                region TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                latitude REAL,
                longitude REAL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                website_url TEXT NOT NULL DEFAULT '',
                menu_url TEXT NOT NULL DEFAULT '',
                menu_summary TEXT NOT NULL DEFAULT '',
                logo_url TEXT NOT NULL DEFAULT '',
                cuisine TEXT NOT NULL DEFAULT '',
                opening_hours TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT NOT NULL DEFAULT '',
                field_sources TEXT NOT NULL DEFAULT '{}',
                demo_url TEXT NOT NULL,
                checked_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(osm_type, osm_id)
            );
            CREATE INDEX IF NOT EXISTS cafe_leads_name_idx ON cafe_leads(name);
            CREATE INDEX IF NOT EXISTS cafe_leads_city_idx ON cafe_leads(city);
            CREATE TABLE IF NOT EXISTS research_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS request_rate_limits (
                service TEXT PRIMARY KEY,
                last_request REAL NOT NULL
            );
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(cafe_leads)")
        }
        if "checked_at" not in columns:
            connection.execute(
                "ALTER TABLE cafe_leads ADD COLUMN checked_at TEXT NOT NULL DEFAULT ''"
            )
            connection.execute("UPDATE cafe_leads SET checked_at = updated_at WHERE checked_at = ''")
        if "menu_summary" not in columns:
            connection.execute(
                "ALTER TABLE cafe_leads ADD COLUMN menu_summary TEXT NOT NULL DEFAULT ''"
            )
        connection.commit()


def get_cached_json(cache_key: str) -> Any | None:
    initialize()
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT payload, expires_at FROM research_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if row is None or row["expires_at"] <= _now():
        return None
    return json.loads(row["payload"])


def set_cached_json(cache_key: str, payload: Any, ttl: timedelta) -> None:
    initialize()
    expiry = (datetime.now(UTC) + ttl).isoformat()
    with closing(_connect()) as connection:
        connection.execute(
            """
            INSERT INTO research_cache (cache_key, payload, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                payload = excluded.payload,
                expires_at = excluded.expires_at
            """,
            (cache_key, json.dumps(payload, ensure_ascii=False), expiry),
        )
        connection.commit()


def wait_for_nominatim_slot(min_interval: float = 1.1) -> None:
    initialize()
    while True:
        with closing(_connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT last_request FROM request_rate_limits WHERE service = ?",
                ("nominatim",),
            ).fetchone()
            now = time.time()
            delay = min_interval - (now - row["last_request"]) if row else 0
            if delay <= 0:
                connection.execute(
                    """
                    INSERT INTO request_rate_limits (service, last_request)
                    VALUES (?, ?)
                    ON CONFLICT(service) DO UPDATE SET last_request = excluded.last_request
                    """,
                    ("nominatim", now),
                )
                connection.commit()
                return
            connection.rollback()
        time.sleep(delay)


def save_lead(lead: dict[str, Any]) -> dict[str, Any]:
    initialize()
    now = _now()
    columns = (
        "osm_type",
        "osm_id",
        "name",
        "slug",
        "address",
        "city",
        "region",
        "country",
        "latitude",
        "longitude",
        "phone",
        "email",
        "website_url",
        "menu_url",
        "menu_summary",
        "logo_url",
        "cuisine",
        "opening_hours",
        "status",
        "notes",
        "field_sources",
        "demo_url",
        "checked_at",
    )
    values = [lead.get(column) for column in columns]
    values[20] = json.dumps(lead.get("field_sources", {}), ensure_ascii=False)
    values[-1] = now
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"osm_type", "osm_id"}
    )
    with closing(_connect()) as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO cafe_leads ({", ".join(columns)}, created_at, updated_at)
            VALUES ({placeholders}, ?, ?)
            ON CONFLICT(osm_type, osm_id) DO UPDATE SET
                {updates},
                updated_at = excluded.updated_at
            """,
            [*values, now, now],
        )
        connection.commit()
        if lead.get("osm_type") and lead.get("osm_id"):
            row = connection.execute(
                "SELECT * FROM cafe_leads WHERE osm_type = ? AND osm_id = ?",
                (lead["osm_type"], lead["osm_id"]),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM cafe_leads WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
    if row is None:
        raise RuntimeError("Saved cafe lead could not be read back from the database")
    return _row_to_dict(row)


def find_leads(query: str, limit: int) -> list[dict[str, Any]]:
    initialize()
    normalized = query.strip()
    sql = "SELECT * FROM cafe_leads"
    parameters: list[Any] = []
    if normalized:
        pattern = f"%{normalized}%"
        sql += """
            WHERE name LIKE ? OR address LIKE ? OR city LIKE ? OR region LIKE ?
               OR country LIKE ? OR cuisine LIKE ? OR notes LIKE ?
        """
        parameters.extend([pattern] * 7)
    sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    parameters.append(limit)
    with closing(_connect()) as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["field_sources"] = json.loads(result["field_sources"])
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat()
