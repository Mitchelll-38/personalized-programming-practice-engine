"""Strict calibration envelopes binding an embedded baseline and validation record."""

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, model_validator

from .artifacts import ArtifactProvenance, RateArtifact, _write_json_atomically, payload_hash
from .calibration import TemperatureScaler
from .portable import PortableBaselineArtifact

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
PositiveFloat = Annotated[StrictFloat, Field(gt=0, allow_inf_nan=False)]


class ValidationCalibrationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fit_partition: Literal["validation"] = "validation"
    provenance: ArtifactProvenance
    validation_sha256: Digest
    probabilities_sha256: Digest
    n_examples: StrictInt = Field(gt=0)
    temperature_grid: tuple[PositiveFloat, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_grid(self):
        if len(set(self.temperature_grid)) != len(self.temperature_grid):
            raise ValueError("Temperature grid must contain unique values")
        return self


def _baseline(payload: dict) -> RateArtifact | PortableBaselineArtifact:
    serialized = json.dumps(payload, allow_nan=False)
    version = payload.get("artifact_version")
    if version == "rate-artifact-v1":
        return RateArtifact.model_validate_json(serialized)
    if version == "portable-baseline-artifact-v1":
        return PortableBaselineArtifact.model_validate_json(serialized)
    raise ValueError("Unsupported calibration base artifact")


class CalibratedBaselineArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_version: Literal["temperature-baseline-artifact-v1"] = "temperature-baseline-artifact-v1"
    calibrated: StrictBool = True
    base_artifact: dict[str, Any]
    base_artifact_sha256: Digest
    calibrator_payload: dict[str, Any]
    validation_record: ValidationCalibrationRecord
    artifact_sha256: Digest

    @model_validator(mode="after")
    def valid_contents(self):
        if not self.calibrated:
            raise ValueError("Calibrated envelope must apply temperature scaling")
        base = _baseline(self.base_artifact)
        scaler = TemperatureScaler.from_dict(self.calibrator_payload)
        if base.provenance != self.validation_record.provenance:
            raise ValueError("Calibration provenance differs from base model")
        if scaler.temperature not in self.validation_record.temperature_grid:
            raise ValueError("Selected temperature must belong to the fitting grid")
        if payload_hash(self.base_artifact) != self.base_artifact_sha256:
            raise ValueError("Base artifact hash mismatch")
        if payload_hash(self.model_dump(exclude={"artifact_sha256"})) != self.artifact_sha256:
            raise ValueError("Calibration envelope hash mismatch")
        return self

    def predict(self, examples) -> list[float]:
        self.valid_contents()  # Nested dictionaries remain mutable in frozen envelopes.
        probabilities = _baseline(self.base_artifact).predict(examples)
        return TemperatureScaler.from_dict(self.calibrator_payload).predict(probabilities)

    def baseline(self) -> RateArtifact | PortableBaselineArtifact:
        """Return a detached validated base, preserving live envelope checks."""
        self.valid_contents()
        return _baseline(self.base_artifact)


def save_calibrated_artifact(path: Path, base: RateArtifact | PortableBaselineArtifact,
                             scaler: TemperatureScaler,
                             record: ValidationCalibrationRecord) -> CalibratedBaselineArtifact:
    """Publish declared validation-fitted parameters; no fitting or dataset reads."""
    if not isinstance(base, (RateArtifact, PortableBaselineArtifact)):
        raise ValueError("Only portable baseline artifacts support this calibration envelope")
    # Serialize/parse once to detach every nested dictionary from caller objects.
    base_payload = json.loads(base.model_dump_json())
    payload = {"artifact_version": "temperature-baseline-artifact-v1", "calibrated": True,
               "base_artifact": base_payload, "base_artifact_sha256": payload_hash(base_payload),
               "calibrator_payload": scaler.to_dict(), "validation_record": record.model_dump()}
    artifact = CalibratedBaselineArtifact.model_validate({**payload, "artifact_sha256": payload_hash(payload)})
    _write_json_atomically(path, artifact.model_dump_json(indent=2) + "\n")
    return artifact


def load_calibrated_artifact(path: Path) -> CalibratedBaselineArtifact:
    return CalibratedBaselineArtifact.model_validate_json(path.read_bytes())
