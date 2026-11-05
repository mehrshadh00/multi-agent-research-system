from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SQLiteRunStore:
    """Small checkpoint store; each stage transition is committed atomically."""

    def __init__(self, path: str | Path = ".aether_data/aether.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, state: dict) -> None:
        now = utc_now()
        state["updated_at"] = now
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_runs
                    (run_id, topic, status, created_at, updated_at, state_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    topic=excluded.topic,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    state_json=excluded.state_json
                """,
                (
                    state["run_id"],
                    state["inputs"]["topic"],
                    state["status"],
                    state["created_at"],
                    now,
                    json.dumps(state, ensure_ascii=False),
                ),
            )

    def load(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM research_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return json.loads(row["state_json"]) if row else None

    def list_runs(self, limit: int = 20) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, topic, status, created_at, updated_at
                FROM research_runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [dict(row) for row in rows]
