"""Train a rate baseline on a verified synthetic bundle; evaluate validation only."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from practice_engine.data.manifest import verify_manifest
from practice_engine.data.schema import PredictionExample
from practice_engine.evaluation import evaluate
from practice_engine.models.artifacts import ArtifactProvenance, save_rate_artifact
from practice_engine.models.features import historical_features
from practice_engine.models.rates import RateBaseline


def _partition(bundle: Path, partition: str, student_ids: set[str]) -> list[PredictionExample]:
    examples = [PredictionExample.model_validate_json(line)
                for line in (bundle / f"{partition}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if not examples or any(row.student_id not in student_ids for row in examples):
        raise ValueError(f"Invalid or empty {partition} student partition")
    historical_features(examples)  # Validate causal boundaries even for history-independent models.
    return examples


def train_rates(bundle: Path, output: Path, *, variant: str = "problem", alpha: float = 1.0) -> dict:
    manifest = verify_manifest(bundle / "manifest.json")
    if manifest.source_kind != "synthetic":
        raise ValueError("This smoke workflow requires declared synthetic data; real-data provenance gate remains unmet")
    if output.exists():
        raise ValueError("Run output must be a new directory; existing runs are not overwritten")
    split = json.loads((bundle / "split.json").read_bytes())
    if split.get("protocol") != "held-out-students" or split.get("version") != manifest.split_version:
        raise ValueError("Unsupported or mismatched split protocol")
    if split.get("source_sha256") != manifest.source_sha256 or split.get("seed") != manifest.seed:
        raise ValueError("Split source/seed differs from processing manifest")
    groups = split["student_ids"]
    train_ids, validation_ids, test_ids = (set(groups[name]) for name in ("train", "validation", "test"))
    if train_ids & validation_ids or train_ids & test_ids or validation_ids & test_ids:
        raise ValueError("Student partitions overlap")
    train = _partition(bundle, "train", train_ids)
    validation = _partition(bundle, "validation", validation_ids)
    model = RateBaseline.fit(train, alpha=alpha)
    if variant not in ("global", "problem"):
        raise ValueError("Unknown rate variant")
    probabilities = model.predict(validation, per_problem=variant == "problem")
    metrics = evaluate(validation, probabilities)
    provenance = ArtifactProvenance(dataset_version=manifest.dataset_version,
        source_kind=manifest.source_kind, source_sha256=manifest.source_sha256,
        split_version=manifest.split_version, split_sha256=sha256((bundle / "split.json").read_bytes()).hexdigest())
    run = {"run_version": "rate-run-v1", "dataset_kind": "synthetic", "research_results": False,
           "model": variant, "alpha": alpha, "seed": manifest.seed,
           "train_examples": len(train), "validation_examples": len(validation),
           "evaluated_partition": "validation", "test_evaluated": False,
           "processing_manifest_sha256": sha256((bundle / "manifest.json").read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="rate-run-", dir=output.parent) as temporary:
        directory = Path(temporary)
        save_rate_artifact(directory / "model.json", model, provenance, variant)
        for name, data in (("validation.json", metrics), ("run.json", run)):
            (directory / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(directory, output)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("global", "problem"), default="problem")
    parser.add_argument("--alpha", type=float, default=1.0)
    args = parser.parse_args()
    print(json.dumps(train_rates(args.bundle, args.output, variant=args.variant, alpha=args.alpha), indent=2))


if __name__ == "__main__":
    main()
