"""Opt-in stateless serving for declared synthetic portable baseline artifacts."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from practice_engine.models.artifacts import RateArtifact
from practice_engine.models.calibrated_artifacts import CalibratedBaselineArtifact, parse_research_artifact
from practice_engine.models.serving import PredictionInput, predict_inputs

router = APIRouter(prefix="/research", tags=["synthetic research"])


class ResearchPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: list[PredictionInput] = Field(min_length=1, max_length=1000)

    @field_validator("inputs", mode="before")
    @classmethod
    def bounded_histories(cls, value):
        # Bound individual histories before constructing canonical interactions.
        if isinstance(value, list):
            for row in value:
                if isinstance(row, dict) and isinstance(row.get("history"), list) and len(row["history"]) > 10000:
                    raise ValueError("Each history is limited to 10000 interactions")
        return value


def _unavailable():
    return HTTPException(status_code=503, detail="research_model_unavailable")


def _artifact():
    configured = os.environ.get("PRACTICE_RESEARCH_MODEL")
    if not configured:
        raise HTTPException(status_code=503, detail="research_model_not_configured")
    try:
        serialized = Path(configured).read_bytes()
        artifact = parse_research_artifact(serialized)
        base = artifact.baseline() if isinstance(artifact, CalibratedBaselineArtifact) else artifact
        if base.provenance.source_kind != "synthetic":
            raise ValueError("Real-data provenance gate remains unmet")
        return artifact
    except (OSError, ValueError, TypeError, RecursionError):
        # Never expose file paths, artifact contents or loader errors to clients.
        raise _unavailable() from None


def _metadata(artifact):
    if isinstance(artifact, CalibratedBaselineArtifact):
        base = artifact.baseline()
        metadata = _metadata(base)
        metadata.update(artifact_version=artifact.artifact_version, calibrated=True,
                        base_artifact_version=base.artifact_version,
                        base_artifact_sha256=artifact.base_artifact_sha256,
                        artifact_sha256=artifact.artifact_sha256,
                        calibration={"method": "temperature-scaling-v1",
                                     "temperature": artifact.calibrator_payload["temperature"],
                                     "validation_record": artifact.validation_record.model_dump(mode="json")})
        return metadata
    return {"model_kind": "rate" if isinstance(artifact, RateArtifact) else artifact.model_kind,
            "variant": artifact.variant if isinstance(artifact, RateArtifact) else None,
            "artifact_version": artifact.artifact_version, "model_version": artifact.model_version,
            "feature_version": artifact.feature_version, "model_sha256": artifact.model_sha256,
            "source_kind": artifact.provenance.source_kind, "dataset_version": artifact.provenance.dataset_version,
            "provenance": artifact.provenance.model_dump(), "calibrated": False,
            "is_synthetic": True, "research_results": False}


@router.get("/model")
def research_model():
    return _metadata(_artifact())


@router.post("/predict")
def research_predict(request: ResearchPredictionRequest):
    artifact = _artifact()
    try:
        scores = predict_inputs(artifact, request.inputs)
    except (ValueError, TypeError, OverflowError):
        raise _unavailable() from None
    return {"model": _metadata(artifact), "predictions": [score.model_dump() for score in scores]}
