import json
import subprocess
import sys

import pytest

from practice_engine.data.holdouts import family_holdout
from practice_engine.data.manifest import artifact_hashes
from practice_engine.data.schema import Interaction
from practice_engine.models.artifacts import load_rate_artifact
from practice_engine.training.bundle import load_training_bundle
from practice_engine.training.rates import train_rates


def mutate(bundle, filename, transform):
    path = bundle / filename
    value = json.loads(path.read_text()) if filename.endswith(".json") else [json.loads(line) for line in path.read_text().splitlines()]
    transform(value)
    path.write_text(json.dumps(value) if filename.endswith(".json") else "".join(json.dumps(row) + "\n" for row in value))
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    (bundle / "manifest.json").write_text(json.dumps(manifest))


@pytest.fixture(params=["student", "family"])
def bundle(request, tmp_path):
    mapping = {f"p{i}": f"f{i // 2}" for i in range(6)}
    def interaction(problem, index, student="s0"):
        return Interaction(student_id=student, problem_id=problem, sequence_index=index,
                           problem_text="Synthetic exercise", concept_ids=("loops",), correct=index % 2 == 0, attempt_number=1)
    initial = family_holdout([interaction(p, i) for i, p in enumerate(mapping)], mapping)
    order = initial.metadata["problem_ids"]["test"] + initial.metadata["problem_ids"]["validation"] + initial.metadata["problem_ids"]["train"]
    rows = [interaction(p, i, f"s{s}") for s in range(3) for i, p in enumerate(order)]
    source, families = tmp_path / "source.jsonl", tmp_path / "families.json"
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    families.write_text(json.dumps(mapping))
    directory = tmp_path / "bundle"
    flags = ["--split-protocol", request.param]
    if request.param == "family":
        flags += ["--family-map", str(families)]
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source), "--output", str(directory),
                    "--synthetic", *flags], capture_output=True, check=True)
    return directory


def test_both_protocols_run_without_parsing_test_examples(bundle, tmp_path):
    loaded = load_training_bundle(bundle)
    before = train_rates(bundle, tmp_path / "before")
    (bundle / "test.jsonl").write_text("POISON: not JSON, never parse\n")
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    after = train_rates(bundle, tmp_path / "after")
    assert before["test_evaluated"] is after["test_evaluated"] is False
    assert loaded.provenance.fit_partition == "train"
    assert loaded.manifest.split_version == loaded.provenance.split_version
    assert load_rate_artifact(tmp_path / "before/model.json") == load_rate_artifact(tmp_path / "after/model.json")
    assert (tmp_path / "before/validation.json").read_bytes() == (tmp_path / "after/validation.json").read_bytes()


@pytest.mark.parametrize("change", [
    lambda split: split.update(seed=99), lambda split: split.update(version="future"),
    lambda split: split.update(source_sha256="0" * 64),
    lambda split: split.update(**{("student_ids" if "student_ids" in split else "problem_ids"): []}),
    lambda split: split["student_ids" if "student_ids" in split else "problem_ids"].update(test=[]),
    lambda split: split["student_ids" if "student_ids" in split else "problem_ids"]["validation"].extend(
        split["student_ids" if "student_ids" in split else "problem_ids"]["train"]),
])
def test_malformed_split_rejected_before_output(bundle, tmp_path, change):
    mutate(bundle, "split.json", change)
    with pytest.raises(ValueError):
        train_rates(bundle, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_future_history_fails(bundle):
    def future(rows):
        example = next(row for row in rows if row["history"])
        example["history"][0]["sequence_index"] = example["target_sequence_index"]
    mutate(bundle, "train.jsonl", future)
    with pytest.raises(ValueError, match="before target"):
        load_training_bundle(bundle)


def test_duplicate_targets_fail(bundle):
    mutate(bundle, "train.jsonl", lambda rows: rows.append(rows[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_training_bundle(bundle)


def test_target_partition_membership_fails(bundle):
    def wrong(rows):
        split = json.loads((bundle / "split.json").read_text())
        if "problem_ids" in split:
            rows[0]["candidate"]["problem_id"] = split["problem_ids"]["validation"][0]
        else:
            rows[0]["student_id"] = split["student_ids"]["validation"][0]
    mutate(bundle, "train.jsonl", wrong)
    with pytest.raises(ValueError, match="partition"):
        load_training_bundle(bundle)


def test_family_held_out_history_and_metadata_mismatch_fail(bundle):
    split = json.loads((bundle / "split.json").read_text())
    if "problem_ids" not in split:
        pytest.skip("family-only boundary")
    held_out = split["problem_ids"]["test"][0]
    def leak(rows):
        rows[0]["history"] = [Interaction(student_id=rows[0]["student_id"], problem_id=held_out,
            sequence_index=0, problem_text="Held-out synthetic", concept_ids=("loops",),
            correct=True, attempt_number=1).model_dump()]
    mutate(bundle, "train.jsonl", leak)
    with pytest.raises(ValueError, match="only training exercises"):
        load_training_bundle(bundle)


def test_family_map_consistency_fail_closed(bundle):
    split = json.loads((bundle / "split.json").read_text())
    if "problem_ids" not in split:
        pytest.skip("family-only boundary")
    mutate(bundle, "split.json", lambda split: split["problem_families"].update(
        {split["problem_ids"]["train"][0]: "not-declared"}))
    with pytest.raises(ValueError, match="family mapping"):
        load_training_bundle(bundle)


def test_family_cross_partition_position_collision_fails(bundle):
    split = json.loads((bundle / "split.json").read_text())
    if "problem_ids" not in split:
        pytest.skip("family-only boundary")
    validation = json.loads((bundle / "validation.jsonl").read_text().splitlines()[0])
    def collide(rows):
        # Both rows individually have valid empty causal prefixes; the position
        # still cannot represent two distinct exercises for one learner.
        rows[0]["target_sequence_index"] = validation["target_sequence_index"]
        rows[0]["history"] = []
    mutate(bundle, "train.jsonl", collide)
    with pytest.raises(ValueError, match="Duplicate"):
        load_training_bundle(bundle)
