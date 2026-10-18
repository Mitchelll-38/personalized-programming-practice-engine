"""Versioned JSON envelopes for fitted historical logistic and BKT baselines."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from .artifacts import ArtifactProvenance, RateArtifact, _write_json_atomically, payload_hash
from .bkt import BKTBaseline
from .features import FEATURE_VERSION
from .logistic import LogisticBaseline

_REGISTRY = {
    "logistic": (LogisticBaseline, "logistic-baseline-v1", FEATURE_VERSION),
    "bkt": (BKTBaseline, "shared-bkt-v1", "concept-bkt-v1"),
}


class PortableBaselineArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_version: Literal["portable-baseline-artifact-v1"] = "portable-baseline-artifact-v1"
    model_kind: Literal["logistic", "bkt"]
    model_version: str
    feature_version: str
    calibrated: StrictBool = False
    provenance: ArtifactProvenance
    model_payload: dict[str, Any]
    model_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_model(self):
        model_class, model_version, feature_version = _REGISTRY[self.model_kind]
        if self.calibrated or self.model_version != model_version or self.feature_version != feature_version:
            raise ValueError("Unsupported baseline model/feature/calibration declaration")
        model_class.from_dict(self.model_payload)
        if payload_hash(self.model_payload) != self.model_sha256:
            raise ValueError("Model payload hash mismatch")
        return self

    def predict(self, examples):
        self.valid_model()
        return _REGISTRY[self.model_kind][0].from_dict(self.model_payload).predict(examples)


def save_baseline_artifact(path: Path, model: LogisticBaseline | BKTBaseline,
                           provenance: ArtifactProvenance) -> PortableBaselineArtifact:
    kind = next((key for key, entry in _REGISTRY.items() if isinstance(model, entry[0])), None)
    if kind is None:
        raise ValueError("Only logistic and BKT portable models are supported")
    _, model_version, feature_version = _REGISTRY[kind]
    payload = model.to_dict()
    artifact = PortableBaselineArtifact(model_kind=kind, model_version=model_version,
        feature_version=feature_version, provenance=provenance, model_payload=payload,
        model_sha256=payload_hash(payload))
    _write_json_atomically(path, artifact.model_dump_json(indent=2) + "\n")
    return artifact


def load_baseline_artifact(path: Path) -> RateArtifact | PortableBaselineArtifact:
    return parse_baseline_artifact(path.read_bytes())


def parse_baseline_artifact(serialized: str | bytes) -> RateArtifact | PortableBaselineArtifact:
    """Validate a known uncalibrated baseline from already-read JSON bytes."""
    import json
    payload = json.loads(serialized)
    if not isinstance(payload, dict):
        raise ValueError("Baseline artifact must be a JSON object")
    version = payload.get("artifact_version")
    if version == "rate-artifact-v1":
        return RateArtifact.model_validate_json(serialized)
    if version == "portable-baseline-artifact-v1":
        return PortableBaselineArtifact.model_validate_json(serialized)
    raise ValueError("Unsupported baseline artifact version")
