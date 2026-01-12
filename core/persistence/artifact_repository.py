"""Artifact repository implementation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional
import uuid

from core.types import ArtifactV3
from .database import Database


class ArtifactRepository:
    """SQLite implementation of artifact persistence."""

    def __init__(self, database: Database):
        self._db = database

    def save_for_session(self, session_id: str, artifact: ArtifactV3) -> None:
        payload = artifact.model_dump(by_alias=True, mode="json")
        artifact_json = json.dumps(payload)
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, artifact_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                artifact_json = excluded.artifact_json,
                updated_at = excluded.updated_at
            """,
            (
                str(uuid.uuid4()),
                session_id,
                artifact_json,
                now,
            ),
        )
        conn.commit()

    def get_for_session(self, session_id: str) -> Optional[ArtifactV3]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT artifact_json
            FROM artifacts
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        data = json.loads(row["artifact_json"])
        return ArtifactV3.model_validate(data)

    def delete_by_session(self, session_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
        conn.commit()
