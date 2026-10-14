"""Day 1 local replay service. Manual outcomes are simulations, not grading."""

from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from api.catalog import BY_ID, EXERCISES
from api.heuristics import concept_profile, estimate, first_attempts, recommend
from api import storage
from api.research import router as research_router

app = FastAPI(title="Programming Practice Engine — synthetic demo", description="Local synthetic replay with an optional stateless synthetic research baseline. No Java execution or calibrated probabilities.")
app.include_router(research_router)


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HistoryItem(StrictRequest):
    problem_id: str
    sequence_index: Annotated[int, Field(strict=True, ge=0)]
    correct: StrictBool
    attempt_number: Annotated[int, Field(strict=True, ge=1)]


class PredictionRequest(StrictRequest):
    history: Annotated[list[HistoryItem], Field(max_length=10000)]
    candidate_ids: Annotated[list[str], Field(min_length=1, max_length=1000)]

    @model_validator(mode="after")
    def validate_order(self):
        indices = [row.sequence_index for row in self.history]
        if len(indices) != len(set(indices)):
            raise ValueError("History sequence indices must be unique")
        attempts = {}
        for row in sorted(self.history, key=lambda item: item.sequence_index):
            previous = attempts.get(row.problem_id, 0)
            if row.attempt_number <= previous:
                raise ValueError("Attempt numbers must increase for each problem")
            attempts[row.problem_id] = row.attempt_number
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("Candidate IDs must be unique")
        return self


class AttemptRequest(StrictRequest):
    student_id: Literal["demo"]
    problem_id: str
    correct: StrictBool


def ensure_known(problem_ids: list[str]) -> None:
    unknown = sorted(set(problem_ids) - set(BY_ID))
    if unknown:
        raise HTTPException(status_code=404, detail={"message": "Unknown exercise IDs", "problem_ids": unknown})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models/current")
def current_model():
    return {"model_id": "demo-history-v1", "dataset_version": "synthetic-v1", "is_demo": True, "calibrated": False}


@app.get("/exercises")
def exercises():
    return EXERCISES


@app.get("/students/demo/history")
def history():
    return storage.history()


@app.get("/students/demo/profile")
def profile():
    observed = storage.history()
    return {
        "student_id": "demo", "is_demo": True,
        "total_interactions": len(observed),
        "first_attempts": len(first_attempts(observed)),
        "retries": sum(row["attempt_number"] > 1 for row in observed),
        "concepts": concept_profile(observed),
    }


@app.get("/students/demo/recommendations")
def recommendations():
    return {"student_id": "demo", "is_demo": True, "policy_version": "demo-ranking-v1", "recommendations": recommend(storage.history())}


@app.post("/predict")
def predict(request: PredictionRequest):
    ensure_known(request.candidate_ids + [row.problem_id for row in request.history])
    return {"is_demo": True, "predictions": estimate([row.model_dump() for row in request.history], request.candidate_ids)}


@app.post("/attempts", status_code=201)
def attempts(request: AttemptRequest):
    ensure_known([request.problem_id])
    return storage.record(request.problem_id, request.correct)
