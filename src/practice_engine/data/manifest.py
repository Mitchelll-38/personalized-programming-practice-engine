"""Version and verify artifacts; a hash is integrity evidence, not data permission."""

from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ARTIFACT_NAMES = ("audit.json", "split.json", "train.jsonl", "validation.jsonl", "test.jsonl")


class ProcessingManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: Literal["processing-v1"] = "processing-v1"
    dataset_version: str = Field(min_length=1, pattern=r"\S")
    source_kind: Literal["synthetic", "unverified"]
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: Literal["canonical-v1"] = "canonical-v1"
    feature_version: Literal["causal-first-attempt-v1"] = "causal-first-attempt-v1"
    split_version: Literal["student-split-v1", "family-holdout-v1"] = "student-split-v1"
    seed: int
    trained_model_version: None = None
    # These cannot be set true by arbitrary CLI arguments.
    release_verified: Literal[False] = False
    redistribution_terms_verified: Literal[False] = False
    artifact_sha256: dict[str, str] = Field(default_factory=dict)


def artifact_hashes(directory: Path) -> dict[str, str]:
    return {name: sha256((directory / name).read_bytes()).hexdigest() for name in ARTIFACT_NAMES}


def write_manifest(directory: Path, manifest: ProcessingManifest) -> ProcessingManifest:
    complete = manifest.model_copy(update={"artifact_sha256": artifact_hashes(directory)})
    (directory / "manifest.json").write_text(complete.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return complete


def verify_manifest(path: Path) -> ProcessingManifest:
    """Read only a fixed artifact set; reject corrupt or incomplete output bundles."""
    manifest = ProcessingManifest.model_validate_json(path.read_bytes())
    if set(manifest.artifact_sha256) != set(ARTIFACT_NAMES):
        raise ValueError("Manifest must cover exactly the five processing artifacts")
    if manifest.artifact_sha256 != artifact_hashes(path.parent):
        raise ValueError("Processing artifact hash mismatch")
    return manifest
