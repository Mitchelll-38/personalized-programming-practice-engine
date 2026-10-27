"""Bounded, deterministic CPU DKT smoke runs with validation-only selection."""

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import torch
from torch import nn

from practice_engine.evaluation import evaluate
from practice_engine.models.dkt import DKT, UNK, ExerciseVocabulary, make_batch
from practice_engine.models.dkt_artifacts import load_dkt_checkpoint, save_dkt_checkpoint
from .bundle import load_training_bundle


@dataclass(frozen=True)
class DKTTrainingConfig:
    seed: int = 38
    max_epochs: int = 30
    patience: int = 5
    batch_size: int = 32
    embedding_size: int = 16
    hidden_size: int = 32
    learning_rate: float = .01

    def __post_init__(self):
        for name, upper in (("seed", 2**32 - 1), ("max_epochs", 500), ("patience", 500),
                            ("batch_size", 4096), ("embedding_size", 512), ("hidden_size", 512)):
            value = getattr(self, name)
            if type(value) is not int or not (0 if name == "seed" else 1) <= value <= upper:
                raise ValueError(f"Invalid bounded integer configuration: {name}")
        if (isinstance(self.learning_rate, bool) or not isinstance(self.learning_rate, (int, float))
                or not 0 < self.learning_rate <= 1 or not math.isfinite(self.learning_rate)):
            raise ValueError("learning_rate must be finite in (0, 1]")


def _probabilities(model, examples, vocabulary, unknown_probability, batch_size):
    model.eval()
    probabilities = []
    with torch.inference_mode():
        for start in range(0, len(examples), batch_size):
            batch = make_batch(examples[start:start + batch_size], vocabulary)
            logits = model(batch.inputs)
            if not torch.isfinite(logits).all():
                raise ValueError("Nonfinite DKT validation predictions")
            values = torch.sigmoid(logits).tolist()
            probabilities.extend(unknown_probability if candidate == UNK else value
                for candidate, value in zip(batch.inputs.candidate_ids.tolist(), values))
    return probabilities


def _fit(train, validation, config):
    vocabulary = ExerciseVocabulary.fit(train)
    model = DKT(vocabulary.size, config.embedding_size, config.hidden_size).cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.BCEWithLogitsLoss()
    correct = sum(row.label for row in train)
    unknown = (correct + 1) / (len(train) + 2)
    history, best_state, best_loss, best_epoch, stale = [], None, math.inf, 0, 0
    for epoch in range(1, config.max_epochs + 1):
        model.train()
        indices = torch.randperm(len(train)).tolist()
        loss_sum = 0.
        for start in range(0, len(indices), config.batch_size):
            rows = [train[index] for index in indices[start:start + config.batch_size]]
            batch = make_batch(rows, vocabulary)
            optimizer.zero_grad()
            loss = criterion(model(batch.inputs), batch.labels)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite DKT training loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5., error_if_nonfinite=True)
            optimizer.step()
            loss_sum += loss.item() * len(rows)
        probabilities = _probabilities(model, validation, vocabulary, unknown, config.batch_size)
        metrics = evaluate(validation, probabilities)
        validation_loss = metrics["aggregate"]["log_loss"]
        history.append({"epoch": epoch, "training_bce": loss_sum / len(train),
                        "validation_log_loss": validation_loss})
        if validation_loss < best_loss:
            best_loss, best_epoch, stale = validation_loss, epoch, 0
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        else:
            stale += 1
            if stale >= config.patience:
                break
    model.load_state_dict(best_state)
    probabilities = _probabilities(model, validation, vocabulary, unknown, config.batch_size)
    return model, vocabulary, correct, probabilities, history, best_epoch


def _run_training(bundle: Path, output: Path, config: DKTTrainingConfig) -> dict:
    bundle, output = Path(bundle), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Run output must be a new directory")
    verified = load_training_bundle(bundle)
    model, vocabulary, correct, probabilities, epochs, best_epoch = _fit(
        verified.train, verified.validation, config)
    metrics = evaluate(verified.validation, probabilities)
    run = {"run_version": "dkt-run-v1", "dataset_kind": "synthetic", "research_results": False,
           "model_version": "id-lstm-dkt-v1", "config": asdict(config), "cpu_threads": 1,
           "deterministic_algorithms": True, "torch_version": torch.__version__,
           "train_examples": len(verified.train), "validation_examples": len(verified.validation),
           "evaluated_partition": "validation", "test_evaluated": False, "calibrated": False,
           "best_epoch": best_epoch, "epochs": epochs, "epochs_completed": len(epochs),
           "stopped_early": len(epochs) < config.max_epochs,
           "provenance": verified.provenance.model_dump(),
           "processing_manifest_sha256": sha256((bundle / "manifest.json").read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.with_name(f".{output.name}.publish-lock")
    lock.mkdir()
    try:
        with TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temporary:
            staging = Path(temporary)
            metadata = save_dkt_checkpoint(staging / "model", model, vocabulary, verified.provenance,
                                           training_total=len(verified.train), training_correct=correct)
            checkpoint = load_dkt_checkpoint(staging / "model")
            reloaded = []
            for start in range(0, len(verified.validation), config.batch_size):
                reloaded.extend(checkpoint.predict(verified.validation[start:start + config.batch_size]))
            if reloaded != probabilities:
                raise ValueError("Selected checkpoint reload prediction mismatch")
            run.update(checkpoint_metadata_sha256=metadata.metadata_sha256,
                       checkpoint_weights_sha256=metadata.weights_sha256)
            for name, value in (("validation.json", metrics), ("run.json", run)):
                (staging / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            if output.exists() or output.is_symlink():
                raise ValueError("Run output must be a new directory")
            os.rename(staging, output)
    finally:
        lock.rmdir()
    return run


def train_dkt(bundle: Path, output: Path, *, config: DKTTrainingConfig | None = None) -> dict:
    """Test bytes are verified by the bundle loader; test examples are never read."""
    config = DKTTrainingConfig() if config is None else config
    if not isinstance(config, DKTTrainingConfig):
        raise ValueError("config must be DKTTrainingConfig")
    previous_threads = torch.get_num_threads()
    previous_determinism = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            torch.manual_seed(config.seed)
            return _run_training(bundle, output, config)
    finally:
        torch.use_deterministic_algorithms(previous_determinism, warn_only=previous_warn_only)
        torch.set_num_threads(previous_threads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    for name, default in asdict(DKTTrainingConfig()).items():
        parser.add_argument("--" + name.replace("_", "-"), type=type(default), default=default)
    arguments = vars(parser.parse_args())
    bundle, output = arguments.pop("bundle"), arguments.pop("output")
    print(json.dumps(train_dkt(bundle, output, config=DKTTrainingConfig(**arguments)), indent=2))


if __name__ == "__main__":
    main()
