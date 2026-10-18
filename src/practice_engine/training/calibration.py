"""Fit scalar calibration to a fixed synthetic baseline on validation only."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from practice_engine.evaluation import evaluate
from practice_engine.evaluation.reliability import reliability_summary
from practice_engine.models.artifacts import payload_hash
from practice_engine.models.calibrated_artifacts import (
    ValidationCalibrationRecord, load_calibrated_artifact, save_calibrated_artifact,
)
from practice_engine.models.calibration import DEFAULT_TEMPERATURES, TemperatureScaler
from practice_engine.models.portable import load_baseline_artifact
from .bundle import load_training_bundle


def calibrate_baseline(bundle: Path, base_model: Path, output: Path,
                       *, temperatures=DEFAULT_TEMPERATURES) -> dict:
    bundle, base_model, output = Path(bundle), Path(base_model), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Calibration output must be a new directory")
    verified = load_training_bundle(bundle)
    base = load_baseline_artifact(base_model)
    if base.provenance != verified.provenance:
        raise ValueError("Base model provenance differs from the calibration bundle")
    grid = tuple(temperatures)
    before = base.predict(verified.validation)
    scaler = TemperatureScaler.fit_validation(verified.validation, before, temperatures=grid)
    after = scaler.predict(before)
    record = ValidationCalibrationRecord(provenance=verified.provenance,
        validation_sha256=sha256((bundle / "validation.jsonl").read_bytes()).hexdigest(),
        probabilities_sha256=payload_hash({"probabilities": before}),
        n_examples=len(verified.validation), temperature_grid=tuple(float(t) for t in grid))
    metrics = {"evaluation_role": "same-validation-observations-used-for-calibration",
               "before": evaluate(verified.validation, before),
               "after": evaluate(verified.validation, after)}
    reliability = {weighting: {phase: reliability_summary(verified.validation, scores, weighting=weighting)
                               for phase, scores in (("before", before), ("after", after))}
                   for weighting in ("interaction", "student")}
    run = {"run_version": "calibration-run-v1", "dataset_kind": "synthetic", "research_results": False,
           "base_model_version": base.model_version, "base_artifact_sha256": payload_hash(base.model_dump()),
           "temperature": scaler.temperature, "temperature_grid": list(record.temperature_grid),
           "seed": verified.manifest.seed, "calibration_fit_partition": "validation",
           "evaluated_partition": "validation", "evaluation_role": metrics["evaluation_role"],
           "test_evaluated": False, "validation_examples": len(verified.validation),
           "provenance": verified.provenance.model_dump(), "validation_record": record.model_dump(mode="json"),
           "processing_manifest_sha256": sha256((bundle / "manifest.json").read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="calibration-run-", dir=output.parent) as temporary:
        staging = Path(temporary)
        artifact = save_calibrated_artifact(staging / "model.json", base, scaler, record)
        if load_calibrated_artifact(staging / "model.json").predict(verified.validation) != after:
            raise ValueError("Reloaded calibrated predictions differ from in-memory predictions")
        run.update(artifact_sha256=artifact.artifact_sha256, reload_predictions_equal=True)
        for name, data in (("validation.json", metrics), ("reliability.json", reliability), ("run.json", run)):
            (staging / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(staging, output)
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temperatures", type=float, nargs="+", default=DEFAULT_TEMPERATURES)
    args = parser.parse_args()
    print(json.dumps(calibrate_baseline(args.bundle, args.base_model, args.output,
                                       temperatures=args.temperatures), indent=2))


if __name__ == "__main__":
    main()
