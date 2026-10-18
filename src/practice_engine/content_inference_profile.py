"""Profile offline loaded synthetic content inference; no encoder or evaluation."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
from time import perf_counter_ns

from pydantic import BaseModel, ConfigDict, Field, field_validator
import torch

from practice_engine.inference_profile import _timings
from practice_engine.models.artifacts import payload_hash
from practice_engine.models.codebert import CACHE_NAMESPACE
from practice_engine.models.content_artifacts import _unique_object, load_content_checkpoint
from practice_engine.models.content_serving import predict_content_inputs
from practice_engine.models.serving import PredictionInput
from practice_engine.training.content_cache import load_content_entries


class _Queries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[PredictionInput] = Field(min_length=1, max_length=256)

    @field_validator("inputs", mode="before")
    @classmethod
    def bounded_history(cls, rows):
        if isinstance(rows, list) and any(isinstance(row, dict) and
                isinstance(row.get("history"), list) and len(row["history"]) > 256 for row in rows):
            raise ValueError("Content profile histories are limited to 256 interactions")
        return rows


def _profile(model, queries, directory, repeats, warmups, batch_size):
    started = perf_counter_ns()
    checkpoint = load_content_checkpoint(model)
    if checkpoint.metadata.provenance.source_kind != "synthetic":
        raise ValueError("Content profiling requires a declared synthetic checkpoint")
    load_ns = perf_counter_ns() - started
    started = perf_counter_ns()
    with Path(queries).open("rb") as stream:
        query_bytes = stream.read(8 * 1024 * 1024 + 1)
    if len(query_bytes) > 8 * 1024 * 1024:
        raise ValueError("Content query file exceeds 8 MiB")
    inputs = _Queries.model_validate(json.loads(query_bytes, object_pairs_hook=_unique_object)).inputs
    query_ns = perf_counter_ns() - started
    started = perf_counter_ns()
    encoder = checkpoint.metadata.encoder
    entries = load_content_entries([row._example() for row in inputs], directory, encoder)
    inventory = {"cache_namespace": CACHE_NAMESPACE, "encoder": encoder.model_dump(),
                 "entries": {key: entries[key].entry_sha256 for key in sorted(entries)}}
    cache_ns = perf_counter_ns() - started
    started = perf_counter_ns()
    for _ in range(warmups):
        predict_content_inputs(checkpoint, inputs, entries, batch_size=batch_size)
    warmup_ns = perf_counter_ns() - started
    samples = []
    for _ in range(repeats):
        started = perf_counter_ns()
        predict_content_inputs(checkpoint, inputs, entries, batch_size=batch_size)
        samples.append(perf_counter_ns() - started)
    metadata = checkpoint.metadata
    return {"profile_version": "offline-content-profile-v1", "research_results": False,
        "source_kind": "synthetic", "model_version": metadata.model_version,
        "artifact_version": metadata.artifact_version, "calibrated": False,
        "checkpoint_metadata_sha256": metadata.metadata_sha256,
        "checkpoint_weights_sha256": metadata.weights_sha256,
        "dataset_version": metadata.provenance.dataset_version,
        "queries_sha256": sha256(query_bytes).hexdigest(), "encoder": encoder.model_dump(),
        "encoder_sha256": payload_hash(encoder.model_dump()),
        "embedding_inventory_sha256": payload_hash(inventory), "embedding_entries": len(entries),
        "cache_namespace": CACHE_NAMESPACE, "config": metadata.config.model_dump(),
        "queries": len(inputs), "batch_size": batch_size, "repeats": repeats, "warmups": warmups,
        "checkpoint_load_ms": load_ns / 1e6, "query_parse_ms": query_ns / 1e6, "cache_load_ms": cache_ns / 1e6,
        "warmup_ms": warmup_ns / 1e6,
        "p95_method": "nearest-rank", "scope": "loaded-adapter-including-feature-building-and-live-integrity",
        "encoder_initialized": False, "network_used": False, "labels_evaluated": False,
        "cpu_threads": 1, "deterministic_algorithms": True, "torch_version": torch.__version__,
        "python_version": platform.python_version(), "system": platform.system(), "machine": platform.machine(),
        **_timings(samples, len(inputs))}


def profile_content_inference(model: Path, queries: Path, directory: Path, *,
                              repeats: int = 20, warmups: int = 2, batch_size: int = 32) -> dict:
    for name, value, lower, upper in (("repeats", repeats, 1, 100), ("warmups", warmups, 0, 10),
                                      ("batch_size", batch_size, 1, 256)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"{name} must be an integer in [{lower},{upper}]")
    threads, deterministic, warn_only = (torch.get_num_threads(),
        torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled())
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            return _profile(model, queries, directory, repeats, warmups, batch_size)
    finally:
        torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)
        torch.set_num_threads(threads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("queries", type=Path)
    parser.add_argument("--encoder-directory", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(profile_content_inference(args.model, args.queries, args.encoder_directory,
        repeats=args.repeats, warmups=args.warmups, batch_size=args.batch_size), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
