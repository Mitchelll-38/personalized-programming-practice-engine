"""Profile repeated offline synthetic baseline batches; never evaluate labels."""

import argparse
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import platform
from statistics import median
from time import perf_counter_ns

from pydantic import BaseModel, ConfigDict, Field, field_validator

from practice_engine.models.calibrated_artifacts import CalibratedBaselineArtifact
from practice_engine.models.portable import parse_baseline_artifact
from practice_engine.models.serving import PredictionInput, predict_inputs


class _Queries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[PredictionInput] = Field(min_length=1, max_length=1000)

    @field_validator("inputs", mode="before")
    @classmethod
    def bounded_history(cls, rows):
        if isinstance(rows, list) and any(isinstance(row, dict) and
                isinstance(row.get("history"), list) and len(row["history"]) > 10000 for row in rows):
            raise ValueError("Each query history is limited to 10000 interactions")
        return rows


def _timings(samples, batch_size):
    ordered = sorted(samples)
    total = sum(samples)
    return {"batch_ms": {"min": ordered[0] / 1e6, "median": median(samples) / 1e6,
                         "p95": ordered[ceil(.95 * len(samples)) - 1] / 1e6,
                         "max": ordered[-1] / 1e6},
            "queries_per_second": batch_size * len(samples) * 1e9 / total if total else None}


def profile_inference(model: Path, queries: Path, *, repeats: int = 20, warmups: int = 2) -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 1000:
        raise ValueError("repeats must be an integer in [1, 1000]")
    if type(warmups) is not int or not 0 <= warmups <= 100:
        raise ValueError("warmups must be an integer in [0, 100]")
    started = perf_counter_ns()
    serialized = Path(model).read_bytes()
    payload = json.loads(serialized)
    calibrated = isinstance(payload, dict) and payload.get("artifact_version") == "temperature-baseline-artifact-v1"
    artifact = (CalibratedBaselineArtifact.model_validate_json(serialized) if calibrated
                else parse_baseline_artifact(serialized))
    base = artifact.baseline() if calibrated else artifact
    if base.provenance.source_kind != "synthetic":
        raise ValueError("Profiling currently requires a declared synthetic artifact")
    load_ns = perf_counter_ns() - started
    query_bytes = Path(queries).read_bytes()
    inputs = _Queries.model_validate_json(query_bytes).inputs
    for _ in range(warmups):
        predict_inputs(artifact, inputs)
    samples = []
    for _ in range(repeats):
        started = perf_counter_ns()
        predict_inputs(artifact, inputs)
        samples.append(perf_counter_ns() - started)
    return {"profile_version": "offline-inference-profile-v1", "research_results": False,
            "source_kind": "synthetic", "calibrated": artifact.calibrated,
            "artifact_version": artifact.artifact_version, "model_version": base.model_version,
            "dataset_version": base.provenance.dataset_version,
            "artifact_sha256": sha256(serialized).hexdigest(),
            "queries_sha256": sha256(query_bytes).hexdigest(),
            "batch_size": len(inputs), "repeats": repeats, "warmups": warmups,
            "artifact_load_ms": load_ns / 1e6, "p95_method": "nearest-rank",
            "scope": "loaded-adapter-including-query-and-live-integrity-validation",
            "python_version": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), **_timings(samples, len(inputs))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("queries", type=Path)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(profile_inference(args.model, args.queries,
        repeats=args.repeats, warmups=args.warmups), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
