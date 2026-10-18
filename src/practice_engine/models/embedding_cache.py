"""Exact-content, declared-encoder cache for finite caller-provided vectors."""

from hashlib import sha256
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator

from .artifacts import payload_hash

Role = Literal["problem-text", "historical-code"]
VERSION = "frozen-embedding-cache-v1"
SHA = r"^[a-f0-9]{64}$"


class EncoderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(min_length=1, pattern=r"\S")
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    tokenizer: str = Field(min_length=1, pattern=r"\S")
    tokenizer_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    pooling: Literal["mean", "cls"]
    max_tokens: StrictInt = Field(ge=1)
    truncation: Literal["left", "right"]
    dimension: StrictInt = Field(ge=1)


def cache_key(content: str, role: Role, config: EncoderConfig) -> str:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Cache input requires nonempty text")
    if role not in ("problem-text", "historical-code") or not isinstance(config, EncoderConfig):
        raise ValueError("Unsupported embedding role or encoder configuration")
    config = EncoderConfig.model_validate(config.model_dump())
    return _key(sha256(content.encode("utf-8")).hexdigest(), role, config)


def _key(content_sha256, role, config):
    return payload_hash({"cache_version": VERSION, "content_sha256": content_sha256,
                         "role": role, "encoder": config.model_dump()})


class EmbeddingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cache_version: Literal["frozen-embedding-cache-v1"] = VERSION
    vector_origin: Literal["caller-provided"] = "caller-provided"
    encoder: EncoderConfig
    role: Role
    content_sha256: str = Field(pattern=SHA)
    key_sha256: str = Field(pattern=SHA)
    vector: tuple[StrictFloat, ...]
    entry_sha256: str = Field(pattern=SHA)

    @model_validator(mode="after")
    def valid_contents(self):
        if len(self.vector) != self.encoder.dimension or any(not math.isfinite(v) for v in self.vector):
            raise ValueError("Vector must be finite and match the declared dimension")
        if self.key_sha256 != _key(self.content_sha256, self.role, self.encoder):
            raise ValueError("Embedding cache key mismatch")
        if self.entry_sha256 != payload_hash(self.to_dict(exclude_hash=True)):
            raise ValueError("Embedding entry checksum mismatch")
        return self

    def to_dict(self, *, exclude_hash=False) -> dict:
        return self.model_dump(mode="json", exclude={"entry_sha256"} if exclude_hash else set())


def make_entry(content: str, role: Role, config: EncoderConfig, vector) -> EmbeddingEntry:
    key = cache_key(content, role, config)
    if (not isinstance(vector, (list, tuple)) or len(vector) != config.dimension
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not -float("inf") < v < float("inf") for v in vector)):
        raise ValueError("Vector requires finite numbers matching the encoder dimension")
    try:
        values = [float(v) for v in vector]
    except OverflowError:
        raise ValueError("Vector entries must fit finite float values") from None
    payload = {"cache_version": VERSION, "vector_origin": "caller-provided", "encoder": config.model_dump(),
               "role": role, "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
               "key_sha256": key, "vector": values}
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Vector entries must fit finite float values")
    return EmbeddingEntry.model_validate({**payload, "entry_sha256": payload_hash(payload)})


def save_embedding(path: Path, content: str, role: Role, config: EncoderConfig, vector) -> EmbeddingEntry:
    """Publish a complete new file with a same-filesystem no-replace hard link."""
    entry = make_entry(content, role, config, vector)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{path.name}.",
                                dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(entry.to_dict(), indent=2, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return entry


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def load_embedding(path: Path, content: str, role: Role, config: EncoderConfig) -> EmbeddingEntry:
    payload = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    entry = EmbeddingEntry.model_validate(payload)
    if entry.key_sha256 != cache_key(content, role, config):
        raise ValueError("Cache entry does not match requested content, role and encoder configuration")
    return entry
