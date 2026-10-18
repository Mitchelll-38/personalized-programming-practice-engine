"""Explicit synthetic recommendation choices, separate from attempts/outcomes."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.recommendation_records import get_snapshot
from api.storage import connect

router = APIRouter(tags=["synthetic recommendation events"])


class ChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    snapshot_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    problem_id: str = Field(min_length=1, max_length=256, pattern=r"\S")


class StoredChoice(ChoiceRequest):
    choice_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    created_at: AwareDatetime


def record_choice(request: ChoiceRequest) -> StoredChoice:
    if not isinstance(request, ChoiceRequest):
        raise ValueError("A ChoiceRequest is required")
    request = ChoiceRequest.model_validate(request.model_dump())
    snapshot = get_snapshot(request.snapshot_id)
    if snapshot is None:
        raise LookupError("recommendation_snapshot_not_found")
    if request.problem_id not in {row.problem_id for row in snapshot.snapshot.candidates}:
        raise ValueError("problem_not_in_recommendation_snapshot")
    stored = StoredChoice(**request.model_dump(), choice_id=uuid4().hex, created_at=datetime.now(UTC))
    with connect() as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("CREATE TABLE IF NOT EXISTS recommendation_choices ("
                   "choice_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, "
                   "snapshot_id TEXT NOT NULL REFERENCES recommendation_snapshots(snapshot_id), "
                   "problem_id TEXT NOT NULL)")
        db.execute("INSERT INTO recommendation_choices VALUES (?, ?, ?, ?)",
                   (stored.choice_id, stored.created_at.isoformat(), stored.snapshot_id, stored.problem_id))
    return stored


@router.post("/recommendation-choices", status_code=201, response_model=StoredChoice)
def choices(request: ChoiceRequest):
    try:
        return record_choice(request)
    except LookupError:
        raise HTTPException(status_code=404, detail="recommendation_snapshot_not_found") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_recommendation_choice") from None
