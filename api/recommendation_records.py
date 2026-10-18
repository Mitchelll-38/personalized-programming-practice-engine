"""Append-only synthetic recommendation snapshots, independent of later outcomes."""

from datetime import UTC, datetime
import re
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, model_validator

from api.storage import connect
from api.practice_policy import PracticePolicy
from practice_engine.models.artifacts import payload_hash


class ScoredCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    problem_id: str = Field(min_length=1, max_length=256, pattern=r"\S")
    predicted_correctness: StrictFloat = Field(ge=0, le=1, allow_inf_nan=False)
    score: StrictFloat = Field(allow_inf_nan=False)


class RecommendationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    student_id: Literal["demo"] = "demo"
    source_kind: Literal["synthetic"] = "synthetic"
    model_id: str = Field(min_length=1, max_length=256, pattern=r"\S")
    policy_version: str = Field(min_length=1, max_length=256, pattern=r"\S")
    dataset_version: str = Field(min_length=1, max_length=256, pattern=r"\S")
    calibrated: StrictBool = False
    policy_config: PracticePolicy | None = None
    policy_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    history_sequence_index: StrictInt = Field(ge=-1)
    candidates: tuple[ScoredCandidate, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_candidates(self):
        if (self.policy_config is None) != (self.policy_sha256 is None):
            raise ValueError("Policy configuration and hash must be recorded together")
        if self.policy_config is not None and (self.policy_config.policy_version != self.policy_version
                or payload_hash(self.policy_config.model_dump()) != self.policy_sha256):
            raise ValueError("Policy identity differs from snapshot metadata")
        ids = [row.problem_id for row in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("Snapshot candidates must be distinct")
        return self


class StoredSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    snapshot_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    created_at: AwareDatetime
    snapshot: RecommendationSnapshot


def _initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS recommendation_snapshots ("
               "snapshot_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload_json TEXT NOT NULL)")


def record_snapshot(snapshot: RecommendationSnapshot) -> StoredSnapshot:
    if not isinstance(snapshot, RecommendationSnapshot):
        raise ValueError("A RecommendationSnapshot is required")
    snapshot = RecommendationSnapshot.model_validate(snapshot.model_dump())
    stored = StoredSnapshot(snapshot_id=uuid4().hex, created_at=datetime.now(UTC), snapshot=snapshot)
    with connect() as db:
        _initialize(db)
        db.execute("INSERT INTO recommendation_snapshots VALUES (?, ?, ?)",
                   (stored.snapshot_id, stored.created_at.isoformat(), stored.model_dump_json()))
    return stored


def _reconstruct(row) -> StoredSnapshot:
    stored = StoredSnapshot.model_validate_json(row[2])
    if stored.snapshot_id != row[0] or stored.created_at.isoformat() != row[1]:
        raise ValueError("Snapshot payload identity does not match its database row")
    return stored


def get_snapshot(snapshot_id: str) -> StoredSnapshot | None:
    if not isinstance(snapshot_id, str) or not re.fullmatch(r"[a-f0-9]{32}", snapshot_id):
        raise ValueError("Invalid snapshot ID")
    with connect() as db:
        _initialize(db)
        row = db.execute("SELECT snapshot_id, created_at, payload_json FROM recommendation_snapshots WHERE snapshot_id = ?",
                         (snapshot_id,)).fetchone()
    return _reconstruct(row) if row else None


def list_snapshots(*, limit: int = 50) -> list[StoredSnapshot]:
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Snapshot limit must be an integer between 1 and 500")
    with connect() as db:
        _initialize(db)
        rows = db.execute("SELECT snapshot_id, created_at, payload_json FROM recommendation_snapshots "
                          "ORDER BY created_at DESC, snapshot_id DESC LIMIT ?", (limit,)).fetchall()
    return [_reconstruct(row) for row in rows]
