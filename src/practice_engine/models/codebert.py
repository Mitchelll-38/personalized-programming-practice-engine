"""Frozen local CodeBERT extraction for causal, label-free query content."""

from dataclasses import dataclass
from hashlib import sha1, sha256
import os
from pathlib import Path
import sys

from .embedding_cache import EncoderConfig, cache_key, load_embedding, save_embedding
from .serving import PredictionInput

REPOSITORY = "microsoft/codebert-base"
REVISION = "3b0952feddeffad0063f274080e3c23d75e7eb39"
CACHE_NAMESPACE = "frozen-codebert-v1"
WEIGHTS_SHA256 = "28b61fd8fa069f6bc966f4cb9572a4026ab2a784fca8fb224020d91b744e32d6"
BLOBS = {"config.json": "cd6f88de92758ae36c1c6e18a03ad288ccb41172",
         "merges.txt": "226b0752cac7789c48f0cb3ec53eda48b7be36cc",
         "special_tokens_map.json": "6cd1d9021e10d47aed59399af6b0e30312b46ca4",
         "tokenizer_config.json": "34ddbd64a4cd3f2d9d8a9120d3662d0bf91baead",
         "vocab.json": "0a39732b2d8be8e493cab3da68b68cc3e28221de"}


@dataclass(frozen=True)
class ContentInput:
    role: str
    text: str


def query_contents(query: PredictionInput) -> tuple[ContentInput, ...]:
    if not isinstance(query, PredictionInput):
        raise ValueError("Extraction requires a label-free PredictionInput")
    query = PredictionInput.model_validate(query.model_dump())
    contents = []
    for row in query.history:
        contents.append(ContentInput("problem-text", row.problem_text))
        if row.submitted_code is not None and row.submitted_code.strip():
            contents.append(ContentInput("historical-code", row.submitted_code))
    contents.append(ContentInput("problem-text", query.candidate.problem_text))
    return tuple(contents)


def codebert_config(*, pooling="mean", max_tokens=512, truncation="right") -> EncoderConfig:
    return EncoderConfig(repository=REPOSITORY, revision=REVISION, tokenizer=REPOSITORY,
                         tokenizer_revision=REVISION, pooling=pooling, max_tokens=max_tokens,
                         truncation=truncation, dimension=768)


def _contained_environment(directory):
    expected = {"HF_HOME": directory / "huggingface", "HF_XET_CACHE": directory / "huggingface/xet"}
    for name, value in expected.items():
        if not os.environ.get(name) or Path(os.environ[name]).resolve() != value:
            raise ValueError(f"Set {name} to the declared private encoder directory before imports")
    constants = sys.modules.get("huggingface_hub.constants")
    if constants is not None and any(Path(getattr(constants, name)).resolve() != value for name, value in expected.items()):
        raise ValueError("Hub was imported with different cache paths; use a fresh configured process")


def _assets(directory, allow_download):
    from huggingface_hub import hf_hub_download
    paths = {}
    for filename in (*BLOBS, "pytorch_model.bin"):
        path = Path(hf_hub_download(REPOSITORY, filename, revision=REVISION,
                    cache_dir=str(directory / "huggingface/hub"), local_files_only=not allow_download, token=False))
        digest = sha256() if filename == "pytorch_model.bin" else sha1()
        if filename in BLOBS:
            digest.update(f"blob {path.stat().st_size}\0".encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != (WEIGHTS_SHA256 if filename == "pytorch_model.bin" else BLOBS[filename]):
            raise ValueError(f"Official encoder asset checksum mismatch: {filename}")
        paths[filename] = path
    snapshot = paths["config.json"].parent
    if any(path.parent != snapshot for path in paths.values()):
        raise ValueError("Encoder assets must belong to one pinned snapshot")
    if {path.name for path in snapshot.iterdir()} != set(paths):
        raise ValueError("Unexpected encoder snapshot files could override verified tokenizer assets")
    return snapshot


class FrozenCodeBERT:
    def __init__(self, directory: Path, *, config: EncoderConfig | None = None,
                 allow_download: bool = False, batch_size: int = 8):
        config = codebert_config() if config is None else config
        if not isinstance(config, EncoderConfig):
            raise ValueError("Encoder configuration is required")
        config = EncoderConfig.model_validate(config.model_dump())
        if (config.repository != REPOSITORY or config.revision != REVISION or config.tokenizer != REPOSITORY
                or config.tokenizer_revision != REVISION or config.dimension != 768 or not 2 <= config.max_tokens <= 512):
            raise ValueError("Only the verified CodeBERT snapshot, dimension and token limit are supported")
        if type(allow_download) is not bool or type(batch_size) is not int or not 1 <= batch_size <= 64:
            raise ValueError("Download flag must be bool and batch_size an integer in [1, 64]")
        self.directory, self.config, self.batch_size = Path(directory).resolve(), config, batch_size
        _contained_environment(self.directory)
        # All optional imports occur after the explicit cache environment check.
        import torch
        from transformers import AutoTokenizer, RobertaModel
        snapshot = _assets(self.directory, allow_download)
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True,
                                                      trust_remote_code=False, use_fast=True)
        self._tokenizer.truncation_side = config.truncation
        self._tokenizer.padding_side = "right"
        self._model = RobertaModel.from_pretrained(str(snapshot), local_files_only=True,
            trust_remote_code=False, weights_only=True, use_safetensors=False, dtype=torch.float32).cpu().eval()
        self._model.requires_grad_(False)
        if self._model.config.hidden_size != 768 or self._model.config.max_position_embeddings != 514:
            raise ValueError("Loaded encoder dimensions differ from the verified snapshot")

    def _vectors(self, contents):
        torch = self._torch
        tokens = self._tokenizer([item.text for item in contents], padding=True, truncation=True,
            max_length=self.config.max_tokens, add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
        ids, mask = tokens["input_ids"].cpu(), tokens["attention_mask"].cpu()
        if (ids.dtype != torch.long or mask.dtype != torch.long or ids.ndim != 2
                or mask.shape != ids.shape or ids.shape[0] != len(contents)
                or not 1 <= ids.shape[1] <= self.config.max_tokens or torch.any((mask != 0) & (mask != 1))
                or torch.any(mask.sum(1) == 0) or torch.any(mask[:, 0] != 1)):
            raise ValueError("Tokenizer returned invalid attention masks or dimensions")
        self._model.eval()
        with torch.inference_mode():
            hidden = self._model(input_ids=ids, attention_mask=mask).last_hidden_state
            if hidden.shape != (*ids.shape, self.config.dimension):
                raise ValueError("Encoder returned invalid hidden dimensions")
            if self.config.pooling == "cls":
                vectors = hidden[:, 0]
            else:
                observed = hidden.masked_fill(~mask.bool().unsqueeze(-1), 0)
                vectors = observed.sum(1) / mask.sum(1).unsqueeze(-1)
            if not torch.isfinite(vectors).all():
                raise ValueError("Encoder returned nonfinite pooled vectors")
        return vectors.tolist()

    def encode(self, query: PredictionInput):
        contents = query_contents(query)
        unique = {cache_key(item.text, item.role, self.config): item for item in contents}
        entries, missing = {}, []
        for key, item in unique.items():
            path = self.directory / "embeddings" / CACHE_NAMESPACE / f"{key}.json"
            if path.exists():
                entries[key] = load_embedding(path, item.text, item.role, self.config)
            else:
                missing.append((key, item))
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start:start + self.batch_size]
            vectors = self._vectors([item for _, item in batch])
            for (key, item), vector in zip(batch, vectors):
                path = self.directory / "embeddings" / CACHE_NAMESPACE / f"{key}.json"
                try:
                    entries[key] = save_embedding(path, item.text, item.role, self.config, vector)
                except FileExistsError:
                    entries[key] = load_embedding(path, item.text, item.role, self.config)
        return tuple(entries[cache_key(item.text, item.role, self.config)] for item in contents)
