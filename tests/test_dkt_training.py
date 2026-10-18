import json
from pathlib import Path
import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.manifest import artifact_hashes
from practice_engine.models.dkt_artifacts import load_dkt_checkpoint
from practice_engine.training.bundle import load_training_bundle
from practice_engine.training.dkt import DKTTrainingConfig, train_dkt

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


@pytest.fixture
def bundle(tmp_path):
    directory = tmp_path / "bundle"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(FIXTURE),
                    "--synthetic", "--output", str(directory)], capture_output=True, check=True)
    return directory


def refresh(bundle):
    path = bundle / "manifest.json"
    value = json.loads(path.read_text())
    value["artifact_sha256"] = artifact_hashes(bundle)
    path.write_text(json.dumps(value))


def small_config(**kwargs):
    return DKTTrainingConfig(max_epochs=4, patience=2, embedding_size=4, hidden_size=5,
                             batch_size=3, **kwargs)


def test_repeated_runs_selected_checkpoint_parity_and_restored_torch_state(bundle, tmp_path):
    torch.manual_seed(711)
    before = torch.get_rng_state().clone()
    first = train_dkt(bundle, tmp_path / "first", config=small_config())
    assert torch.equal(before, torch.get_rng_state())
    second = train_dkt(bundle, tmp_path / "second", config=small_config())
    assert first == second
    assert first["test_evaluated"] is False and first["research_results"] is False
    assert first["best_epoch"] == min(first["epochs"], key=lambda row: row["validation_log_loss"])["epoch"]
    verified = load_training_bundle(bundle)
    one = load_dkt_checkpoint(tmp_path / "first/model")
    two = load_dkt_checkpoint(tmp_path / "second/model")
    assert one.predict(verified.validation) == two.predict(verified.validation)
    assert one.metadata.training_total == 8 and one.metadata.training_correct == sum(row.label for row in verified.train)
    for row in verified.validation:
        if row.candidate.problem_id not in one.metadata.vocabulary["problem_ids"]:
            assert one.predict([row]) == [one.metadata.unknown_probability]
    assert (tmp_path / "first/validation.json").read_bytes() == (tmp_path / "second/validation.json").read_bytes()


def test_plateau_stops_after_patience_and_restores_first_best_state(bundle, tmp_path, monkeypatch):
    # Fixed validation predictions simulate no improvement while optimizer keeps changing weights.
    monkeypatch.setattr("practice_engine.training.dkt._probabilities", lambda *args: [.5, .5])
    monkeypatch.setattr("practice_engine.training.dkt.load_dkt_checkpoint",
                        lambda path: type("ConstantCheckpoint", (), {"predict": lambda self, rows: [.5, .5]})())
    run = train_dkt(bundle, tmp_path / "run", config=small_config())
    assert run["best_epoch"] == 1 and run["epochs_completed"] == 3 and run["stopped_early"] is True
    config = DKTTrainingConfig(max_epochs=1, embedding_size=4, hidden_size=5, batch_size=3)
    first_epoch = train_dkt(bundle, tmp_path / "first-epoch", config=config)
    assert run["checkpoint_weights_sha256"] == first_epoch["checkpoint_weights_sha256"]


def test_poisoned_test_examples_never_parsed_and_validation_labels_not_training_inputs(bundle, tmp_path):
    first = train_dkt(bundle, tmp_path / "first", config=small_config())
    (bundle / "test.jsonl").write_text("INVALID JSON: never read as examples\n")
    refresh(bundle)
    second = train_dkt(bundle, tmp_path / "second", config=small_config())
    assert first["epochs"] == second["epochs"]
    assert first["checkpoint_weights_sha256"] == second["checkpoint_weights_sha256"]
    validation_path = bundle / "validation.jsonl"
    rows = [json.loads(line) for line in validation_path.read_text().splitlines()]
    for row in rows:
        row["label"] = not row["label"]
    validation_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    refresh(bundle)
    # Exactly one epoch isolates fitting from validation-based selection.
    config = DKTTrainingConfig(max_epochs=1, embedding_size=4, hidden_size=5, batch_size=3)
    changed = train_dkt(bundle, tmp_path / "changed", config=config)
    for row in rows:
        row["label"] = not row["label"]
    validation_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    refresh(bundle)
    original = train_dkt(bundle, tmp_path / "original", config=config)
    assert changed["checkpoint_weights_sha256"] == original["checkpoint_weights_sha256"]


@pytest.mark.parametrize("change", [{"seed": True}, {"max_epochs": 0}, {"max_epochs": 501},
                                   {"patience": 0}, {"batch_size": 0}, {"hidden_size": 513},
                                   {"learning_rate": True}, {"learning_rate": float("nan")}])
def test_invalid_bounded_configuration(change):
    with pytest.raises(ValueError):
        DKTTrainingConfig(**change)


def test_unverified_source_future_history_and_no_clobber_fail_before_publication(bundle, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    (output / "preserve").write_text("existing")
    with pytest.raises(ValueError, match="new directory"):
        train_dkt(bundle, output, config=small_config())
    assert (output / "preserve").read_text() == "existing"
    manifest_path = bundle / "manifest.json"
    value = json.loads(manifest_path.read_text())
    value["source_kind"] = "unverified"
    manifest_path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="synthetic"):
        train_dkt(bundle, tmp_path / "unverified", config=small_config())
    value["source_kind"] = "synthetic"
    manifest_path.write_text(json.dumps(value))
    path = bundle / "train.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = next(row for row in rows if row["history"])
    row["history"][0]["sequence_index"] = row["target_sequence_index"]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    refresh(bundle)
    with pytest.raises(ValueError, match="before target"):
        train_dkt(bundle, tmp_path / "future", config=small_config())
    assert not (tmp_path / "unverified").exists() and not (tmp_path / "future").exists()


def test_failed_publication_cleans_staging_and_preserves_other_writer_lock(bundle, tmp_path, monkeypatch):
    def interrupted(*args):
        raise OSError("interrupted")
    monkeypatch.setattr("practice_engine.training.dkt.os.rename", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        train_dkt(bundle, tmp_path / "failed", config=small_config())
    assert not (tmp_path / "failed").exists() and not list(tmp_path.glob(".failed*"))
    lock = tmp_path / ".locked.publish-lock"
    lock.mkdir()
    with pytest.raises(FileExistsError):
        train_dkt(bundle, tmp_path / "locked", config=small_config())
    assert lock.is_dir() and not (tmp_path / "locked").exists()


def test_family_holdout_predictions_use_population_fallback_and_cli_runs(tmp_path):
    from practice_engine.data.schema import Interaction
    rows = [Interaction(student_id=f"s{s}", problem_id=f"p{p}", sequence_index=p,
                        problem_text="Original synthetic", concept_ids=("loops",),
                        correct=p % 2 == 0, attempt_number=1) for s in range(3) for p in range(6)]
    source, mapping, bundle = tmp_path / "source.jsonl", tmp_path / "families.json", tmp_path / "bundle"
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    mapping.write_text(json.dumps({f"p{p}": f"f{p // 2}" for p in range(6)}))
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source), "--synthetic",
                    "--split-protocol", "family", "--family-map", str(mapping), "--output", str(bundle)],
                   capture_output=True, check=True)
    output = tmp_path / "run"
    result = subprocess.run([sys.executable, "-m", "practice_engine.training.dkt", str(bundle),
                             "--output", str(output), "--max-epochs", "2", "--patience", "1",
                             "--embedding-size", "4", "--hidden-size", "5"],
                            capture_output=True, check=True, text=True)
    run = json.loads(result.stdout)
    loaded = load_dkt_checkpoint(output / "model")
    validation = load_training_bundle(bundle).validation
    assert run["provenance"]["split_version"] == "family-holdout-v1"
    assert all(row.candidate.problem_id not in loaded.metadata.vocabulary["problem_ids"] for row in validation)
    assert loaded.predict(validation) == [loaded.metadata.unknown_probability] * len(validation)


def test_validation_chunks_preserve_order_fallback_and_whole_batch_parity(bundle, monkeypatch):
    import practice_engine.training.dkt as trainer
    from practice_engine.models.dkt import DKT, UNK, ExerciseVocabulary, make_batch

    verified = load_training_bundle(bundle)
    vocabulary = ExerciseVocabulary.fit(verified.train)
    rows = verified.train[:4] + verified.validation[:1]
    rows[-1] = rows[-1].model_copy(update={
        "candidate": rows[-1].candidate.model_copy(update={"problem_id": "unseen-validation"})})
    model = DKT(vocabulary.size, embedding_size=4, hidden_size=5).eval()
    batch = make_batch(rows, vocabulary)
    with torch.inference_mode():
        expected = torch.sigmoid(model(batch.inputs)).tolist()
    expected = [.25 if candidate == UNK else value
                for candidate, value in zip(batch.inputs.candidate_ids.tolist(), expected)]
    sizes = []

    def bounded_batch(examples, vocabulary):
        sizes.append(len(examples))
        assert len(examples) <= 2
        return make_batch(examples, vocabulary)

    monkeypatch.setattr(trainer, "make_batch", bounded_batch)
    actual = trainer._probabilities(model, rows, vocabulary, .25, 2)
    assert sizes == [2, 2, 1]
    assert actual == pytest.approx(expected, abs=1e-7)
    assert actual[-1] == .25

    # Reject a nonfinite logit in the final partial chunk, even for an unknown ID.
    original_forward = model.forward
    def nonfinite_last(inputs):
        logits = original_forward(inputs)
        return logits * float("nan") if len(inputs.candidate_ids) == 1 else logits
    monkeypatch.setattr(model, "forward", nonfinite_last)
    with pytest.raises(ValueError, match="Nonfinite DKT validation"):
        trainer._probabilities(model, rows, vocabulary, .25, 2)


def test_training_validation_and_reload_are_bounded_and_metrics_weight_examples(tmp_path, monkeypatch):
    import math
    import practice_engine.models.dkt_artifacts as artifacts
    import practice_engine.training.dkt as trainer
    from practice_engine.data.schema import Interaction

    source, directory = tmp_path / "source.jsonl", tmp_path / "bundle"
    rows = [Interaction(student_id=f"s{s}", problem_id=f"p{p}", sequence_index=p,
                        problem_text="Original synthetic batching case", concept_ids=("loops",),
                        correct=p % 2 == 0, attempt_number=1) for s in range(10) for p in range(5)]
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source),
                    "--synthetic", "--output", str(directory)], capture_output=True, check=True)
    verified = load_training_bundle(directory)
    assert len(verified.validation) > 3 and len(verified.validation) % 3
    original_batch = trainer.make_batch
    validation_sizes, reload_sizes = [], []
    validation_students = {row.student_id for row in verified.validation}

    def bounded_batch(examples, vocabulary):
        assert len(examples) <= 3
        if examples[0].student_id in validation_students:
            validation_sizes.append(len(examples))
        return original_batch(examples, vocabulary)

    def bounded_reload(examples, vocabulary):
        reload_sizes.append(len(examples))
        assert len(examples) <= 3
        return original_batch(examples, vocabulary)

    monkeypatch.setattr(trainer, "make_batch", bounded_batch)
    monkeypatch.setattr(artifacts, "make_batch", bounded_reload)
    output = tmp_path / "run"
    config = DKTTrainingConfig(max_epochs=2, patience=2, embedding_size=4, hidden_size=5, batch_size=3)
    run = train_dkt(directory, output, config=config)
    chunks = [min(3, len(verified.validation) - start) for start in range(0, len(verified.validation), 3)]
    assert validation_sizes == chunks * (run["epochs_completed"] + 1)
    assert reload_sizes == chunks
    checkpoint = load_dkt_checkpoint(output / "model")
    probabilities = [value for start in range(0, len(verified.validation), 3)
                     for value in checkpoint.predict(verified.validation[start:start + 3])]
    loss = -sum(math.log(p if row.label else 1 - p)
                for row, p in zip(verified.validation, probabilities)) / len(probabilities)
    metrics = json.loads((output / "validation.json").read_text())
    assert metrics["aggregate"]["log_loss"] == pytest.approx(loss)
    assert run["epochs"][run["best_epoch"] - 1]["validation_log_loss"] == pytest.approx(loss)
    assert run["test_evaluated"] is False and run["research_results"] is False
