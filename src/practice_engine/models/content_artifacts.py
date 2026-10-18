"""Bounded CPU content-model checkpoints; integrity checks are not authentication."""

import ctypes
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator
import torch

from .artifacts import ArtifactProvenance, payload_hash
from .content_inputs import ConceptVocabulary, ContentInputs
from .content_lstm import ContentLSTM
from .embedding_cache import EncoderConfig


class _Architecture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    concept_vocabulary_size: StrictInt = Field(ge=3, le=10000)
    input_size: StrictInt = Field(ge=1, le=4096)
    projection_size: StrictInt = Field(ge=1, le=256)
    concept_size: StrictInt = Field(ge=1, le=128)
    correctness_size: StrictInt = Field(ge=1, le=32)
    hidden_size: StrictInt = Field(ge=1, le=256)


class ContentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    artifact_version: Literal["content-checkpoint-v1"] = "content-checkpoint-v1"
    model_version: Literal["content-lstm-v1"] = "content-lstm-v1"
    feature_version: Literal["content-inputs-forward-v1"] = "content-inputs-forward-v1"
    calibrated: StrictBool = False
    provenance: ArtifactProvenance
    config: _Architecture
    vocabulary: dict
    encoder: EncoderConfig
    weights_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    metadata_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_contents(self):
        if self.calibrated:
            raise ValueError("Content checkpoints are uncalibrated")
        if ConceptVocabulary.from_dict(self.vocabulary).size != self.config.concept_vocabulary_size:
            raise ValueError("Concept vocabulary differs from architecture")
        if self.encoder.dimension != self.config.input_size:
            raise ValueError("Encoder dimension differs from model input size")
        if payload_hash(self.model_dump(exclude={"metadata_sha256"})) != self.metadata_sha256:
            raise ValueError("Metadata checksum mismatch")
        return self


def _configuration(model):
    if type(model) is not ContentLSTM:
        raise ValueError("Canonical ContentLSTM required")
    if (type(model.problem) is not torch.nn.Linear or type(model.code) is not torch.nn.Linear
            or type(model.head) is not torch.nn.Linear or type(model.concepts) is not torch.nn.Embedding
            or type(model.correctness) is not torch.nn.Embedding or type(model.lstm) is not torch.nn.LSTM
            or model.concepts.padding_idx != 0 or model.correctness.padding_idx is not None
            or any(embedding.max_norm is not None or embedding.scale_grad_by_freq or embedding.sparse
                   for embedding in (model.concepts, model.correctness))
            or model.correctness.num_embeddings != 2
            or model.code.in_features != model.problem.in_features
            or model.code.out_features != model.problem.out_features
            or model.head.out_features != 1
            or model.head.in_features != model.lstm.hidden_size + model.problem.out_features + model.concepts.embedding_dim
            or any(layer.bias is None for layer in (model.problem, model.code, model.head))
            or model.lstm.input_size != 2 * model.problem.out_features + model.concepts.embedding_dim + model.correctness.embedding_dim + 1
            or model.lstm.num_layers != 1 or not model.lstm.batch_first or model.lstm.bidirectional
            or model.lstm.dropout != 0 or not model.lstm.bias or model.lstm.proj_size != 0):
        raise ValueError("Unsupported content architecture semantics")
    return _Architecture(concept_vocabulary_size=model.concepts.num_embeddings,
        input_size=model.problem.in_features, projection_size=model.problem.out_features,
        concept_size=model.concepts.embedding_dim, correctness_size=model.correctness.embedding_dim,
        hidden_size=model.lstm.hidden_size)


def _fingerprint(model):
    digest = sha256(payload_hash(_configuration(model).model_dump()).encode())
    for name, tensor in sorted(model.state_dict().items()):
        if tensor.device.type != "cpu" or tensor.dtype != torch.float32 or tensor.layout != torch.strided:
            raise ValueError("Content checkpoint state must be CPU float32 strided tensors")
        tensor = tensor.detach().contiguous()
        digest.update(f"{name}|{tensor.dtype}|{tuple(tensor.shape)}".encode())
        buffer = (ctypes.c_ubyte * (tensor.numel() * tensor.element_size())).from_address(tensor.data_ptr())
        digest.update(memoryview(buffer))
    return digest.hexdigest()


def _restore(metadata, state):
    # Loading a checkpoint must not advance the caller's initialization RNG.
    with torch.device("cpu"), torch.random.fork_rng(devices=[]):
        model = ContentLSTM(**metadata.config.model_dump()).float().cpu()
    expected = model.state_dict()
    if not isinstance(state, dict) or set(state) != set(expected):
        raise ValueError("Content checkpoint state keys differ")
    for name, reference in expected.items():
        tensor = state[name]
        if (not isinstance(tensor, torch.Tensor) or tensor.device.type != "cpu"
                or tensor.layout != torch.strided or tensor.shape != reference.shape
                or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all()):
            raise ValueError(f"Invalid content checkpoint tensor: {name}")
    model.load_state_dict(state, strict=True)
    return model.eval()


@dataclass(frozen=True)
class ContentCheckpoint:
    metadata: ContentMetadata
    _model: ContentLSTM
    _state_sha256: str

    def validate_integrity(self) -> None:
        # Pydantic frozen envelopes do not deep-freeze vocabulary dictionaries.
        ContentMetadata.model_validate(self.metadata.model_dump())
        if _fingerprint(self._model) != self._state_sha256:
            raise ValueError("Loaded content checkpoint changed")

    def logits(self, inputs: ContentInputs) -> torch.Tensor:
        self.validate_integrity()
        with torch.inference_mode():
            return self._model(inputs)


def save_content_checkpoint(directory: Path, model: ContentLSTM, vocabulary: ConceptVocabulary,
                            encoder: EncoderConfig, provenance: ArtifactProvenance) -> ContentMetadata:
    """Publish a new directory; vocabulary/provenance must describe training only."""
    directory = Path(directory)
    if directory.exists() or directory.is_symlink():
        raise FileExistsError("Content checkpoint destination exists")
    if not isinstance(vocabulary, ConceptVocabulary) or not isinstance(encoder, EncoderConfig) or not isinstance(provenance, ArtifactProvenance):
        raise ValueError("Typed vocabulary, encoder and provenance required")
    config = _configuration(model)
    _fingerprint(model)  # Reject actual non-CPU/non-float32 state before cloning.
    state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    directory.parent.mkdir(parents=True, exist_ok=True)
    lock = directory.with_name(f".{directory.name}.publish-lock")
    lock.mkdir()
    try:
        with TemporaryDirectory(prefix=f".{directory.name}.", dir=directory.parent) as temporary:
            staging = Path(temporary)
            torch.save(state, staging / "weights.pt")
            payload = {"artifact_version": "content-checkpoint-v1", "model_version": "content-lstm-v1",
                "feature_version": "content-inputs-forward-v1", "calibrated": False,
                "provenance": provenance.model_dump(), "config": config.model_dump(),
                "vocabulary": vocabulary.to_dict(), "encoder": encoder.model_dump(),
                "weights_sha256": sha256((staging / "weights.pt").read_bytes()).hexdigest()}
            metadata = ContentMetadata.model_validate({**payload, "metadata_sha256": payload_hash(payload)})
            _restore(metadata, state)
            (staging / "metadata.json").write_text(metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")
            if directory.exists() or directory.is_symlink():
                raise FileExistsError("Content checkpoint destination exists")
            os.rename(staging, directory)
        return metadata
    finally:
        lock.rmdir()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate checkpoint JSON field")
        result[key] = value
    return result


def load_content_checkpoint(directory: Path) -> ContentCheckpoint:
    directory = Path(directory)
    payload = json.loads((directory / "metadata.json").read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    metadata = ContentMetadata.model_validate(payload)
    serialized = (directory / "weights.pt").read_bytes()
    if sha256(serialized).hexdigest() != metadata.weights_sha256:
        raise ValueError("Content weights checksum mismatch")
    state = torch.load(BytesIO(serialized), map_location="cpu", weights_only=True)
    model = _restore(metadata, state)
    return ContentCheckpoint(metadata, model, _fingerprint(model))
