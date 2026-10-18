"""Prepare verified synthetic train/validation content; test examples stay unread."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from practice_engine.data.schema import PredictionExample
from practice_engine.models.codebert import CACHE_NAMESPACE, FrozenCodeBERT, codebert_config, query_contents
from practice_engine.models.embedding_cache import EncoderConfig, cache_key, load_embedding
from practice_engine.models.serving import PredictionInput
from .bundle import load_training_bundle


def _queries(examples):
    if not isinstance(examples, (list, tuple)) or any(not isinstance(row, PredictionExample) for row in examples):
        raise ValueError("Content examples must be PredictionExample objects")
    rows = [PredictionExample.model_validate(row.model_dump()) for row in examples]
    return [PredictionInput.model_validate(row.model_dump(exclude={"label"})) for row in rows]


def load_content_entries(examples, directory: Path, config: EncoderConfig) -> dict:
    """Read matching required entries without initializing an encoder/network."""
    if not isinstance(config, EncoderConfig):
        raise ValueError("An EncoderConfig is required")
    config = EncoderConfig.model_validate(config.model_dump())
    entries = {}
    for query in _queries(examples):
        for item in query_contents(query):
            key = cache_key(item.text, item.role, config)
            if key not in entries:
                entries[key] = load_embedding(Path(directory) / "embeddings" / CACHE_NAMESPACE / f"{key}.json",
                                              item.text, item.role, config)
    return entries


def prepare_content_cache(bundle: Path, directory: Path, *, config: EncoderConfig | None = None,
                          allow_download: bool = False) -> dict:
    bundle = Path(bundle)
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    verified = load_training_bundle(bundle)
    if (bundle / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Bundle manifest changed during verification")
    examples = [*verified.train, *verified.validation]
    queries = _queries(examples)
    config = codebert_config() if config is None else config
    encoder = FrozenCodeBERT(Path(directory), config=config, allow_download=allow_download)
    for query in queries:
        encoder.encode(query)
    entries = load_content_entries(examples, directory, encoder.config)
    if (bundle / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Bundle manifest changed during content preparation")
    return {"receipt_version": "synthetic-content-cache-v1", "source_kind": "synthetic",
            "research_results": False, "test_examples_read": False,
            "processing_manifest_sha256": sha256(manifest_bytes).hexdigest(),
            "provenance": verified.provenance.model_dump(), "encoder": encoder.config.model_dump(),
            "cache_namespace": CACHE_NAMESPACE, "train_examples": len(verified.train),
            "validation_examples": len(verified.validation),
            "entries": {key: entries[key].entry_sha256 for key in sorted(entries)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--encoder-directory", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--pooling", choices=("mean", "cls"), default="mean")
    parser.add_argument("--truncation", choices=("left", "right"), default="right")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    config = codebert_config(max_tokens=args.max_tokens, pooling=args.pooling, truncation=args.truncation)
    print(json.dumps(prepare_content_cache(args.bundle, args.encoder_directory,
        config=config, allow_download=args.allow_download), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
