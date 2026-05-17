from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any


class Storage:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS readings(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT NOT NULL,
                  balance REAL NOT NULL,
                  display_text TEXT NOT NULL,
                  recorded_at TEXT NOT NULL,
                  source TEXT NOT NULL DEFAULT 'api'
                );
                CREATE TABLE IF NOT EXISTS query_events(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  status TEXT NOT NULL,
                  message TEXT NOT NULL,
                  recorded_at TEXT NOT NULL
                );
                """
            )

    def add_reading(self, room: str, balance: float, display_text: str, recorded_at: str, source: str = "api") -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO readings(room, balance, display_text, recorded_at, source) VALUES (?, ?, ?, ?, ?)",
                (room, balance, display_text, recorded_at, source),
            )

    def list_readings(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM readings ORDER BY recorded_at ASC, id ASC").fetchall()
        return [dict(row) for row in rows]

    def latest_reading(self) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM readings ORDER BY recorded_at DESC, id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def add_query_event(self, status: str, message: str, recorded_at: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO query_events(status, message, recorded_at) VALUES (?, ?, ?)",
                (status, message, recorded_at),
            )

    def last_query_event(self) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM query_events ORDER BY recorded_at DESC, id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
