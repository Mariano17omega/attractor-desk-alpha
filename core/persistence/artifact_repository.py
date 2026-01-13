"""Artifact repository implementation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactV3,
)
from .database import Database


def _is_legacy_artifact_shape(data: dict) -> bool:
    """Check if JSON matches legacy ArtifactV3 shape (not collection)."""
    # Collection has 'version' key and 'artifacts' list; legacy has 'currentIndex'
    return "currentIndex" in data and "version" not in data


def _migrate_legacy_artifact(data: dict) -> ArtifactCollectionV1:
    """Wrap a legacy ArtifactV3 JSON into a collection with one artifact."""
    legacy = ArtifactV3.model_validate(data)
    artifact_id = str(uuid.uuid4())
    entry = ArtifactEntry(
        id=artifact_id,
        artifact=legacy,
        export_meta=ArtifactExportMeta(),
    )
    return ArtifactCollectionV1(
        version=1,
        artifacts=[entry],
        active_artifact_id=artifact_id,
    )


class ArtifactRepository:
    """SQLite implementation of artifact persistence with collection support."""

    def __init__(self, database: Database):
        self._db = database

    # ---- Collection-based API ----

    def save_collection(self, session_id: str, collection: ArtifactCollectionV1) -> None:
        """Save an artifact collection for a session."""
        payload = collection.model_dump(by_alias=True, mode="json")
        collection_json = json.dumps(payload)
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
                collection_json,
                now,
            ),
        )
        conn.commit()

    def get_collection(self, session_id: str) -> Optional[ArtifactCollectionV1]:
        """Get the artifact collection for a session with backward compatibility."""
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
        # Handle legacy single-artifact format
        if _is_legacy_artifact_shape(data):
            return _migrate_legacy_artifact(data)
        return ArtifactCollectionV1.model_validate(data)

    # ---- Legacy API (for backward compatibility with existing callers) ----

    def save_for_session(self, session_id: str, artifact: ArtifactV3) -> None:
        """Save a single artifact for a session (legacy API).

        This wraps the artifact in a collection or updates the active artifact
        in an existing collection.
        """
        existing = self.get_collection(session_id)
        if existing is None:
            # Create new collection with this artifact as the only one
            artifact_id = str(uuid.uuid4())
            entry = ArtifactEntry(
                id=artifact_id,
                artifact=artifact,
                export_meta=ArtifactExportMeta(),
            )
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=artifact_id,
            )
        else:
            # Update the active artifact in the existing collection
            collection = existing
            active_entry = collection.get_active_entry()
            if active_entry is not None:
                # Update the artifact in place
                for i, entry in enumerate(collection.artifacts):
                    if entry.id == active_entry.id:
                        collection.artifacts[i] = ArtifactEntry(
                            id=entry.id,
                            artifact=artifact,
                            export_meta=entry.export_meta,
                        )
                        break
            else:
                # No active artifact; add this one and make it active
                artifact_id = str(uuid.uuid4())
                entry = ArtifactEntry(
                    id=artifact_id,
                    artifact=artifact,
                    export_meta=ArtifactExportMeta(),
                )
                collection.artifacts.append(entry)
                collection.active_artifact_id = artifact_id
        self.save_collection(session_id, collection)

    def get_for_session(self, session_id: str) -> Optional[ArtifactV3]:
        """Get the active artifact for a session (legacy API)."""
        collection = self.get_collection(session_id)
        if collection is None:
            return None
        return collection.get_active_artifact()

    def delete_by_session(self, session_id: str) -> None:
        """Delete artifacts for a session."""
        conn = self._db.get_connection()
        conn.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
        conn.commit()

