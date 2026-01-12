"""Settings repository implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.models import Setting
from .database import Database


class SettingsRepository:
    """Repository for settings persistence operations."""

    def __init__(self, database: Database):
        self._db = database

    def get(self, key: str) -> Optional[Setting]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Setting(
            key=row["key"],
            value=row["value"],
            category=row["category"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_all(self) -> list[Setting]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings ORDER BY category, key"
        )
        return [
            Setting(
                key=row["key"],
                value=row["value"],
                category=row["category"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in cursor.fetchall()
        ]

    def get_by_category(self, category: str) -> list[Setting]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings WHERE category = ? ORDER BY key",
            (category,),
        )
        return [
            Setting(
                key=row["key"],
                value=row["value"],
                category=row["category"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in cursor.fetchall()
        ]

    def set(self, key: str, value: str, category: str) -> Setting:
        conn = self._db.get_connection()
        now = datetime.now()
        conn.execute(
            """
            INSERT INTO settings (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (key, value, category, now.isoformat()),
        )
        conn.commit()
        return Setting(key=key, value=value, category=category, updated_at=now)

    def delete(self, key: str) -> bool:
        conn = self._db.get_connection()
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    def get_value(self, key: str, default: str = "") -> str:
        setting = self.get(key)
        return setting.value if setting else default

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get_value(key, str(default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get_value(key, str(default).lower())
        return value.strip().lower() in ("1", "true", "yes", "on")
