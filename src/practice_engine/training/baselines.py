"""Reproducible synthetic logistic/BKT runs; validation only, no test parsing."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from practice_engine.evaluation import evaluate
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import load_baseline_artifact, save_baseline_artifact
from .bundle import load_training_bundle


def train_baseline(bundle: Path, output: Path, *, model_kind: str,
                   C: float | None = None, max_iter: int | None = None) -> dict:
    if model_kind not in ("logistic", "bkt"):
        raise ValueError("Model must be logistic or bkt")
    if model_kind == "bkt" and (C is not None or max_iter is not None):
        raise ValueError("C/max_iter are only valid for logistic runs")
    if output.exists():
        raise ValueError("Run output must be a new directory; existing runs are not overwritten")
    verified = load_training_bundle(bundle)
    manifest = verified.manifest
    if model_kind == "logistic":
        config = {"C": 1.0 if C is None else C, "max_iter": 1000 if max_iter is None else max_iter,
                  "seed": manifest.seed}
        model = LogisticBaseline.fit(verified.train, **config)
    else:
        config = {"selection": "train-conditional-log-likelihood", "tie_break": "lexicographic",
                  "parameter_grid": {"initial": [0.2, 0.5], "learn": [0.0, 0.1, 0.2],
                                     "guess": [0.1, 0.2], "slip": [0.1, 0.2]},
                  "configurations": 24}
        model = BKTBaseline.fit(verified.train)
    probabilities = model.predict(verified.validation)
    metrics = evaluate(verified.validation, probabilities)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="baseline-run-", dir=output.parent) as temporary:
        directory = Path(temporary)
        artifact = save_baseline_artifact(directory / "model.json", model, verified.provenance)
        reloaded = load_baseline_artifact(directory / "model.json")
        if reloaded.predict(verified.validation) != probabilities:
            raise ValueError("Saved baseline predictions differ from the fitted model")
        run = {"run_version": "baseline-run-v1", "dataset_kind": "synthetic", "research_results": False,
               "model": model_kind, "model_version": artifact.model_version,
               "feature_version": artifact.feature_version, "artifact_version": artifact.artifact_version,
               "calibrated": False, "config": config, "seed": manifest.seed,
               "train_examples": len(verified.train), "validation_examples": len(verified.validation),
               "evaluated_partition": "validation", "test_evaluated": False,
               "reload_predictions_equal": True, "provenance": verified.provenance.model_dump(),
               "model_sha256": artifact.model_sha256,
               "processing_manifest_sha256": sha256((bundle / "manifest.json").read_bytes()).hexdigest()}
        for name, data in (("validation.json", metrics), ("run.json", run)):
            (directory / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(directory, output)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=("logistic", "bkt"), required=True)
    parser.add_argument("--C", type=float, help="Positive finite logistic regularization strength (default 1)")
    parser.add_argument("--max-iter", type=int, help="Positive logistic iteration limit (default 1000)")
    args = parser.parse_args()
    if args.model == "bkt" and (args.C is not None or args.max_iter is not None):
        parser.error("--C/--max-iter are only valid with --model logistic")
    print(json.dumps(train_baseline(args.bundle, args.output, model_kind=args.model,
                                   C=args.C, max_iter=args.max_iter), indent=2))


if __name__ == "__main__":
    main()
