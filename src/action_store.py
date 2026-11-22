"""SQLite-backed corrective-action register with field-level audit history."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

FIELDS = [
    "Facility", "Month", "Programme", "Indicator", "Primary issue", "Issue count",
    "Status", "Assigned owner", "Root cause", "Corrective action / notes", "Due date",
]
DB_COLUMNS = {
    "Facility": "facility",
    "Month": "month",
    "Programme": "programme",
    "Indicator": "indicator",
    "Primary issue": "primary_issue",
    "Issue count": "issue_count",
    "Status": "status",
    "Assigned owner": "assigned_owner",
    "Root cause": "root_cause",
    "Corrective action / notes": "corrective_action",
    "Due date": "due_date",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _value(value: Any) -> str | int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else float(value)
    return str(value).strip()


class ActionRegisterStore:
    """Persist action assignments locally and record every field change."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    record_id TEXT PRIMARY KEY,
                    facility TEXT,
                    month TEXT,
                    programme TEXT,
                    indicator TEXT,
                    primary_issue TEXT,
                    issue_count INTEGER,
                    status TEXT NOT NULL DEFAULT 'Open',
                    assigned_owner TEXT,
                    root_cause TEXT,
                    corrective_action TEXT,
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS action_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    FOREIGN KEY(record_id) REFERENCES actions(record_id)
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_history_record "
                "ON action_history(record_id, changed_at)"
            )

    def get_actions(self, record_ids: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
        with self._connect() as connection:
            if record_ids is None:
                rows = connection.execute("SELECT * FROM actions").fetchall()
            else:
                ids = list(dict.fromkeys(str(value) for value in record_ids))
                if not ids:
                    return {}
                placeholders = ",".join("?" for _ in ids)
                rows = connection.execute(
                    f"SELECT * FROM actions WHERE record_id IN ({placeholders})", ids
                ).fetchall()
        result = {}
        reverse = {column: label for label, column in DB_COLUMNS.items()}
        for row in rows:
            item = {label: row[column] for column, label in reverse.items()}
            result[row["record_id"]] = item
        return result

    def upsert_actions(self, records: Iterable[dict[str, Any]]) -> dict[str, int]:
        inserted = updated = unchanged = 0
        timestamp = _now()
        with self._connect() as connection:
            for record in records:
                record_id = str(record.get("Record_ID", "")).strip()
                if not record_id:
                    continue
                values = {column: _value(record.get(label)) for label, column in DB_COLUMNS.items()}
                existing = connection.execute(
                    "SELECT * FROM actions WHERE record_id = ?", (record_id,)
                ).fetchone()
                if existing is None:
                    columns = ["record_id", *DB_COLUMNS.values(), "created_at", "updated_at"]
                    params = [record_id, *values.values(), timestamp, timestamp]
                    placeholders = ",".join("?" for _ in params)
                    connection.execute(
                        f"INSERT INTO actions ({','.join(columns)}) VALUES ({placeholders})",
                        params,
                    )
                    for label, column in DB_COLUMNS.items():
                        connection.execute(
                            "INSERT INTO action_history "
                            "(record_id, changed_at, field_name, old_value, new_value) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (record_id, timestamp, label, None,
                             None if values[column] is None else str(values[column])),
                        )
                    inserted += 1
                else:
                    changes = {
                        label: (existing[column], values[column])
                        for label, column in DB_COLUMNS.items()
                        if _value(existing[column]) != values[column]
                    }
                    if not changes:
                        unchanged += 1
                        continue
                    assignments = ", ".join(f"{column} = ?" for column in DB_COLUMNS.values())
                    connection.execute(
                        f"UPDATE actions SET {assignments}, updated_at = ? WHERE record_id = ?",
                        [*values.values(), timestamp, record_id],
                    )
                    for label, (old, new) in changes.items():
                        connection.execute(
                            "INSERT INTO action_history "
                            "(record_id, changed_at, field_name, old_value, new_value) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (record_id, timestamp, label,
                             None if old is None else str(old),
                             None if new is None else str(new)),
                        )
                    updated += 1
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

    def history(self, record_id: str) -> pd.DataFrame:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT changed_at, field_name, old_value, new_value "
                "FROM action_history WHERE record_id = ? ORDER BY history_id",
                (str(record_id),),
            ).fetchall()
        return pd.DataFrame([dict(row) for row in rows],
                            columns=["changed_at", "field_name", "old_value", "new_value"])
