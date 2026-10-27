import json
from pathlib import Path
import subprocess
import sys

import pytest

from practice_engine.data.holdouts import family_holdout
from practice_engine.data.manifest import artifact_hashes
from practice_engine.data.schema import Interaction
from practice_engine.models.artifacts import load_rate_artifact
from practice_engine.training import bundle as bundle_module
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


@pytest.mark.parametrize("artifact", ["split.json", "train.jsonl", "validation.jsonl", "audit.json"])
def test_changed_bytes_after_manifest_verification_never_enter_training(bundle, tmp_path,
                                                                         monkeypatch, artifact):
    if artifact == "audit.json" and "problem_ids" not in json.loads((bundle / "split.json").read_text()):
        pytest.skip("family audit is parsed only for family holdouts")
    original_verify = bundle_module.verify_manifest

    def verify_then_change(path):
        manifest = original_verify(path)
        target = bundle / artifact
        if artifact.endswith(".jsonl"):
            rows = [json.loads(line) for line in target.read_text().splitlines()]
            last = max(rows, key=lambda row: row["target_sequence_index"])
            last["label"] = not last["label"]
            target.write_text("".join(json.dumps(row) + "\n" for row in rows))
        else:
            target.write_text(target.read_text() + "\n")
        return manifest

    monkeypatch.setattr(bundle_module, "verify_manifest", verify_then_change)
    output = tmp_path / "invalid-run"
    with pytest.raises(ValueError, match=f"Processing artifact hash mismatch: {artifact}"):
        train_rates(bundle, output)
    assert not output.exists()


@pytest.mark.parametrize("field", ["label", "history_correct"])
def test_hash_valid_duplicate_json_fields_fail_before_training(bundle, field):
    path = bundle / "train.jsonl"
    lines = path.read_text().splitlines()
    index = next(i for i, line in enumerate(lines)
                 if field == "label" or json.loads(line)["history"])
    row = json.loads(lines[index])
    original = row["label"] if field == "label" else row["history"][0]["correct"]
    key = "label" if field == "label" else "correct"
    accepted = f'"{key}":{str(original).lower()}'
    contradictory = f'"{key}":{str(not original).lower()},' + accepted
    assert accepted in lines[index]
    lines[index] = lines[index].replace(accepted, contradictory, 1)
    path.write_text("\n".join(lines) + "\n")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Duplicate JSON field in research input"):
        load_training_bundle(bundle)


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


@pytest.mark.parametrize("change", [
    lambda observed: observed.update(correct=not observed["correct"]),
    lambda observed: observed.update(problem_text="Contradictory synthetic statement"),
    lambda observed: observed.update(concept_ids=["different-synthetic-concept"]),
])
def test_history_must_match_earlier_scored_target(bundle, change):
    def contradict(rows):
        targets = {(row["student_id"], row["target_sequence_index"]): row for row in rows}
        later = next(row for row in rows if any(
            (row["student_id"], observed["sequence_index"]) in targets
            for observed in row["history"]))
        observed = next(observed for observed in later["history"] if
                        (later["student_id"], observed["sequence_index"]) in targets)
        change(observed)
    mutate(bundle, "train.jsonl", contradict)
    with pytest.raises(ValueError, match="History contradicts a scored target"):
        load_training_bundle(bundle)


@pytest.mark.parametrize("field,value", [
    ("problem_text", "Different synthetic statement"),
    ("concept_ids", ["different-synthetic-concept"]),
])
def test_hash_valid_cross_student_problem_metadata_conflict_fails(bundle, field, value):
    def conflict(rows):
        selected = rows[0]
        student = selected["student_id"]
        problem = selected["candidate"]["problem_id"]
        for example in rows:
            if example["student_id"] != student:
                continue
            if example["candidate"]["problem_id"] == problem:
                example["candidate"][field] = value
            for observed in example["history"]:
                if observed["problem_id"] == problem:
                    observed[field] = value
    mutate(bundle, "validation.jsonl", conflict)
    with pytest.raises(ValueError, match="inconsistent statement or concepts"):
        load_training_bundle(bundle)


def test_duplicate_candidate_tags_cannot_hide_behind_set_equivalence(tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"
    source = tmp_path / "two-tag-exercises.jsonl"
    source.write_text("".join(line + "\n" for line in fixture.read_text().splitlines()
                              if json.loads(line)["problem_id"] == "sum"))
    directory = tmp_path / "bundle"
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source),
                    "--synthetic", "--output", str(directory)], capture_output=True, check=True)
    assert load_training_bundle(directory).validation

    def duplicate(rows):
        target = next(row for row in rows if row["candidate"]["problem_id"] == "sum")
        assert target["candidate"]["concept_ids"] == ["loops", "arrays"]
        target["candidate"]["concept_ids"] = ["loops", "loops", "arrays"]

    mutate(directory, "validation.jsonl", duplicate)
    with pytest.raises(ValueError, match="unique nonempty concept IDs"):
        load_training_bundle(directory)


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
