"""CPU DKT checkpoints with strict metadata, tensor-only loads and UNK fallback."""

import ctypes
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator
import torch

from .artifacts import ArtifactProvenance, payload_hash
from .dkt import DKT, UNK, ExerciseVocabulary, make_batch


class _Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    vocabulary_size: StrictInt = Field(ge=3)
    embedding_size: StrictInt = Field(ge=1)
    hidden_size: StrictInt = Field(ge=1)


class DKTMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    artifact_version: Literal["dkt-checkpoint-v1"] = "dkt-checkpoint-v1"
    model_version: Literal["id-lstm-dkt-v1"] = "id-lstm-dkt-v1"
    calibrated: StrictBool = False
    provenance: ArtifactProvenance
    config: _Config
    vocabulary: dict
    training_total: StrictInt = Field(gt=0)
    training_correct: StrictInt = Field(ge=0)
    weights_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_contents(self):
        if self.calibrated:
            raise ValueError("DKT checkpoints must be uncalibrated")
        if self.training_correct > self.training_total:
            raise ValueError("training correct count cannot exceed total")
        if ExerciseVocabulary.from_dict(self.vocabulary).size != self.config.vocabulary_size:
            raise ValueError("vocabulary size does not match model configuration")
        if payload_hash(self.model_dump(exclude={"metadata_sha256"})) != self.metadata_sha256:
            raise ValueError("Metadata hash mismatch")
        return self

    @property
    def unknown_probability(self) -> float:
        return (self.training_correct + 1) / (self.training_total + 2)


def _restore(metadata: DKTMetadata, state: dict) -> DKT:
    model = DKT(**metadata.config.model_dump()).float().cpu()
    expected = model.state_dict()
    if not isinstance(state, dict) or set(state) != set(expected):
        raise ValueError("Checkpoint state keys do not match DKT")
    for key, reference in expected.items():
        tensor = state[key]
        if (not isinstance(tensor, torch.Tensor) or tensor.layout != torch.strided
                or tensor.shape != reference.shape or tensor.dtype != reference.dtype
                or not torch.isfinite(tensor).all()):
            raise ValueError(f"Invalid checkpoint tensor: {key}")
    model.load_state_dict(state, strict=True)
    return model.eval()


def _state_fingerprint(model: DKT) -> str:
    digest = sha256()
    for name, tensor in sorted(model.state_dict().items()):
        tensor = tensor.detach().cpu().contiguous()
        digest.update(f"{name}|{tensor.dtype}|{tuple(tensor.shape)}".encode())
        # A transient byte view avoids NumPy and a second serialized checkpoint.
        buffer = (ctypes.c_ubyte * (tensor.numel() * tensor.element_size())).from_address(tensor.data_ptr())
        digest.update(memoryview(buffer))
    return digest.hexdigest()


@dataclass(frozen=True)
class DKTCheckpoint:
    metadata: DKTMetadata
    _model: DKT
    _state_sha256: str

    def predict(self, examples) -> list[float]:
        self.metadata.valid_contents()  # Frozen envelopes do not deep-freeze maps.
        if _state_fingerprint(self._model) != self._state_sha256:
            raise ValueError("Loaded checkpoint weights changed")
        if not examples:
            return []
        batch = make_batch(examples, ExerciseVocabulary.from_dict(self.metadata.vocabulary))
        with torch.inference_mode():
            logits = self._model(batch.inputs)
            if not torch.isfinite(logits).all():
                raise ValueError("Nonfinite checkpoint prediction")
            probabilities = torch.sigmoid(logits).tolist()
        return [self.metadata.unknown_probability if candidate == UNK else probability
                for candidate, probability in zip(batch.inputs.candidate_ids.tolist(), probabilities)]


def save_dkt_checkpoint(directory: Path, model: DKT, vocabulary: ExerciseVocabulary,
                        provenance: ArtifactProvenance, *, training_total: int,
                        training_correct: int) -> DKTMetadata:
    """Publish a new directory only; supplied fallback counts must be train-only."""
    directory = Path(directory)
    if directory.exists() or directory.is_symlink():
        raise FileExistsError(f"Checkpoint destination exists: {directory}")
    state = {key: tensor.detach().cpu().clone() for key, tensor in model.state_dict().items()}
    directory.parent.mkdir(parents=True, exist_ok=True)
    lock = directory.with_name(f".{directory.name}.publish-lock")
    lock.mkdir()  # Serialize cooperating publishers; never replace their lock.
    try:
        with TemporaryDirectory(prefix=f".{directory.name}.", dir=directory.parent) as temporary:
            staging = Path(temporary)
            torch.save(state, staging / "weights.pt")
            payload = {"artifact_version": "dkt-checkpoint-v1", "model_version": "id-lstm-dkt-v1",
                       "calibrated": False, "provenance": provenance.model_dump(),
                       "config": {"vocabulary_size": model.head.out_features,
                                  "embedding_size": model.embedding.embedding_dim,
                                  "hidden_size": model.lstm.hidden_size},
                       "vocabulary": vocabulary.to_dict(), "training_total": training_total,
                       "training_correct": training_correct,
                       "weights_sha256": sha256((staging / "weights.pt").read_bytes()).hexdigest()}
            metadata = DKTMetadata.model_validate({**payload, "metadata_sha256": payload_hash(payload)})
            _restore(metadata, state)
            (staging / "metadata.json").write_text(metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")
            if directory.exists() or directory.is_symlink():
                raise FileExistsError(f"Checkpoint destination exists: {directory}")
            os.rename(staging, directory)
        return metadata
    finally:
        lock.rmdir()


def load_dkt_checkpoint(directory: Path) -> DKTCheckpoint:
    directory = Path(directory)
    metadata = DKTMetadata.model_validate_json((directory / "metadata.json").read_bytes())
    serialized = (directory / "weights.pt").read_bytes()
    if sha256(serialized).hexdigest() != metadata.weights_sha256:
        raise ValueError("Weights hash mismatch")
    state = torch.load(BytesIO(serialized), map_location="cpu", weights_only=True)
    model = _restore(metadata, state)
    return DKTCheckpoint(metadata, model, _state_fingerprint(model))
