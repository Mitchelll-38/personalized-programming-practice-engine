"""Strict JSON rate artifacts; counts and declared provenance, never pickle."""

from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from .rates import RateBaseline


def payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(encoded).hexdigest()


class ArtifactProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset_version: str = Field(min_length=1, pattern=r"\S")
    source_kind: Literal["synthetic", "unverified"]
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    split_version: str = Field(min_length=1, pattern=r"\S")
    split_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fit_partition: Literal["train"] = "train"


class RateArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_version: Literal["rate-artifact-v1"] = "rate-artifact-v1"
    model_version: Literal["rate-baseline-v1"] = "rate-baseline-v1"
    feature_version: Literal["training-target-counts-v1"] = "training-target-counts-v1"
    variant: Literal["global", "problem"]
    calibrated: StrictBool = False
    provenance: ArtifactProvenance
    model_payload: dict[str, Any]
    model_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_model(self):
        if self.calibrated:
            raise ValueError("Rate artifacts are uncalibrated")
        RateBaseline.from_dict(self.model_payload)
        if payload_hash(self.model_payload) != self.model_sha256:
            raise ValueError("Model payload hash mismatch")
        return self

    def predict(self, examples):
        # Frozen Pydantic envelopes do not deep-freeze nested dictionaries.
        self.valid_model()
        return RateBaseline.from_dict(self.model_payload).predict(examples, per_problem=self.variant == "problem")


def save_rate_artifact(path: Path, model: RateBaseline, provenance: ArtifactProvenance,
                       variant: Literal["global", "problem"] = "problem") -> RateArtifact:
    payload = model.to_dict()
    artifact = RateArtifact(variant=variant, provenance=provenance, model_payload=payload,
                            model_sha256=payload_hash(payload))
    _write_json_atomically(path, artifact.model_dump_json(indent=2) + "\n")
    return artifact


def _write_json_atomically(path: Path, serialized: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_rate_artifact(path: Path) -> RateArtifact:
    return RateArtifact.model_validate_json(path.read_bytes())
