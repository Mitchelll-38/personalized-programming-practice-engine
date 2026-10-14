"""Train a rate baseline on a verified synthetic bundle; evaluate validation only."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from practice_engine.evaluation import evaluate
from practice_engine.models.artifacts import save_rate_artifact
from practice_engine.models.rates import RateBaseline
from .bundle import load_training_bundle


def train_rates(bundle: Path, output: Path, *, variant: str = "problem", alpha: float = 1.0) -> dict:
    verified = load_training_bundle(bundle)
    manifest = verified.manifest
    if output.exists():
        raise ValueError("Run output must be a new directory; existing runs are not overwritten")
    train, validation = verified.train, verified.validation
    model = RateBaseline.fit(train, alpha=alpha)
    if variant not in ("global", "problem"):
        raise ValueError("Unknown rate variant")
    probabilities = model.predict(validation, per_problem=variant == "problem")
    metrics = evaluate(validation, probabilities)
    run = {"run_version": "rate-run-v1", "dataset_kind": "synthetic", "research_results": False,
           "model": variant, "alpha": alpha, "seed": manifest.seed,
           "train_examples": len(train), "validation_examples": len(validation),
           "evaluated_partition": "validation", "test_evaluated": False,
           "processing_manifest_sha256": sha256((bundle / "manifest.json").read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="rate-run-", dir=output.parent) as temporary:
        directory = Path(temporary)
        save_rate_artifact(directory / "model.json", model, verified.provenance, variant)
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
