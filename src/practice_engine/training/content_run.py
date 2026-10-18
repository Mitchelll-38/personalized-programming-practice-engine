"""Publish verified synthetic content runs from offline cache; no test evaluation."""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import torch

from practice_engine.evaluation import evaluate
from practice_engine.models.artifacts import payload_hash
from practice_engine.models.codebert import CACHE_NAMESPACE, codebert_config
from practice_engine.models.content_artifacts import load_content_checkpoint, save_content_checkpoint
from practice_engine.models.content_inputs import make_content_batch
from practice_engine.models.embedding_cache import EncoderConfig
from .bundle import load_training_bundle
from .content import ContentTrainingConfig, fit_content
from .content_cache import load_content_entries


def _replay(checkpoint, rows, vocabulary, entries, encoder, batch_size):
    threads = torch.get_num_threads()
    deterministic = torch.are_deterministic_algorithms_enabled()
    warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        probabilities = []
        with torch.device("cpu"), torch.inference_mode():
            for start in range(0, len(rows), batch_size):
                batch = make_content_batch(rows[start:start + batch_size], vocabulary, entries, encoder)
                probabilities.extend(torch.sigmoid(checkpoint.logits(batch.inputs)).tolist())
        return tuple(probabilities)
    finally:
        torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)
        torch.set_num_threads(threads)


def train_content(bundle: Path, directory: Path, output: Path, *, encoder: EncoderConfig | None = None,
                  config: ContentTrainingConfig | None = None) -> dict:
    bundle, output = Path(bundle), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Content run output must be a new directory")
    encoder = codebert_config() if encoder is None else encoder
    config = ContentTrainingConfig() if config is None else config
    if not isinstance(encoder, EncoderConfig) or not isinstance(config, ContentTrainingConfig):
        raise ValueError("Typed encoder and training configuration required")
    encoder = EncoderConfig.model_validate(encoder.model_dump())
    config = ContentTrainingConfig(**asdict(config))
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    verified = load_training_bundle(bundle)
    if (bundle / "manifest.json").read_bytes() != manifest_bytes:
        raise ValueError("Bundle manifest changed during verification")
    entries = load_content_entries([*verified.train, *verified.validation], directory, encoder)
    inventory = {"cache_namespace": CACHE_NAMESPACE, "encoder": encoder.model_dump(),
                 "entries": {key: entries[key].entry_sha256 for key in sorted(entries)}}
    fit = fit_content(verified.train, verified.validation, entries, encoder, config=config)
    evaluation = evaluate(verified.validation, fit.validation_probabilities)
    metrics = {key: evaluation[key] for key in ("aggregate", "equal_student_macro", "metric_definitions")}
    run = {"run_version": "content-run-v1", "dataset_kind": "synthetic", "research_results": False,
        "model_version": "content-lstm-v1", "feature_version": "content-inputs-forward-v1",
        "config": asdict(config), "config_sha256": payload_hash(asdict(config)),
        "encoder": encoder.model_dump(), "encoder_sha256": payload_hash(encoder.model_dump()),
        "embedding_inventory_sha256": payload_hash(inventory), "embedding_entries": len(entries),
        "cache_namespace": CACHE_NAMESPACE, "cpu_threads": 1, "deterministic_algorithms": True,
        "torch_version": torch.__version__, "train_examples": len(verified.train),
        "validation_examples": len(verified.validation), "evaluated_partition": "validation",
        "test_evaluated": False, "test_examples_read": False, "calibrated": False,
        "best_epoch": fit.best_epoch, "epochs": [asdict(epoch) for epoch in fit.epochs],
        "epochs_completed": len(fit.epochs), "stopped_early": len(fit.epochs) < config.max_epochs,
        "provenance": verified.provenance.model_dump(),
        "processing_manifest_sha256": sha256(manifest_bytes).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.with_name(f".{output.name}.publish-lock")
    lock.mkdir()
    try:
        with TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temporary:
            staging = Path(temporary)
            metadata = save_content_checkpoint(staging / "model", fit.model, fit.vocabulary, encoder, verified.provenance)
            checkpoint = load_content_checkpoint(staging / "model")
            probabilities = _replay(checkpoint, verified.validation, fit.vocabulary, entries, encoder, config.batch_size)
            if probabilities != fit.validation_probabilities:
                raise ValueError("Content checkpoint reload prediction mismatch")
            run.update(reload_predictions_equal=True, checkpoint_metadata_sha256=metadata.metadata_sha256,
                       checkpoint_weights_sha256=metadata.weights_sha256)
            for name, data in (("validation.json", metrics), ("run.json", run)):
                (staging / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            if (bundle / "manifest.json").read_bytes() != manifest_bytes:
                raise ValueError("Bundle manifest changed during training")
            if output.exists() or output.is_symlink():
                raise FileExistsError("Content run output must be a new directory")
            os.rename(staging, output)
    finally:
        lock.rmdir()
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--encoder-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--pooling", choices=("mean", "cls"), default="mean")
    parser.add_argument("--truncation", choices=("left", "right"), default="right")
    for name, default in asdict(ContentTrainingConfig()).items():
        parser.add_argument("--" + name.replace("_", "-"), type=type(default), default=default)
    values = vars(parser.parse_args())
    bundle, directory, output = values.pop("bundle"), values.pop("encoder_directory"), values.pop("output")
    encoder = codebert_config(**{name: values.pop(name) for name in ("max_tokens", "pooling", "truncation")})
    print(json.dumps(train_content(bundle, directory, output, encoder=encoder,
        config=ContentTrainingConfig(**values)), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
