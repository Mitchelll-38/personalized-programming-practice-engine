"""Synthetic regressions for complete causal histories in training bundles."""

import json
import subprocess
import sys

import pytest

from practice_engine.data.holdouts import family_holdout
from practice_engine.data.manifest import artifact_hashes
from practice_engine.data.schema import Interaction
from practice_engine.training.bundle import load_training_bundle


def _row(student, problem, index, attempt_number=1):
    return Interaction(student_id=student, problem_id=problem, sequence_index=index,
                       problem_text=f"Synthetic prompt {problem}", concept_ids=("loops",),
                       correct=index % 2 == 0, attempt_number=attempt_number)


@pytest.fixture(params=("student", "family"))
def bundle(request, tmp_path):
    mapping = {f"p{i}": f"f{i}" for i in range(6)}
    preview = family_holdout([_row("preview", problem, i) for i, problem in enumerate(mapping)], mapping)
    groups = preview.metadata["problem_ids"]
    # A retry gap follows the first training exercise. A test-family first attempt
    # sits between two training targets and must stay absent from family histories.
    order = [groups["train"][0], groups["test"][0], groups["train"][1],
             groups["validation"][0], *groups["train"][2:]]
    rows = []
    for student in ("s0", "s1", "s2"):
        rows.append(_row(student, order[0], 0))
        rows.append(_row(student, order[0], 1, attempt_number=2))
        rows.extend(_row(student, problem, index) for index, problem in enumerate(order[1:], 2))
    source = tmp_path / "source.jsonl"
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    command = [sys.executable, "-m", "practice_engine.data.cli", str(source),
               "--output", str(tmp_path / "bundle"), "--synthetic", "--split-protocol", request.param]
    if request.param == "family":
        family_map = tmp_path / "family-map.json"
        family_map.write_text(json.dumps(mapping))
        command += ["--family-map", str(family_map)]
    subprocess.run(command, capture_output=True, check=True)
    return tmp_path / "bundle", request.param, order


def _rehash(bundle):
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    manifest_path.write_text(json.dumps(manifest))


def test_valid_prefix_preserves_retry_and_family_holdout_gaps(bundle):
    directory, protocol, _ = bundle
    loaded = load_training_bundle(directory)
    examples = loaded.train + loaded.validation
    student = "s0" if protocol == "family" else loaded.train[0].student_id
    later = next(row for row in examples if row.student_id == student and row.target_sequence_index == 3)
    positions = [row.sequence_index for row in later.history]
    assert 0 in positions and 1 not in positions  # Prior first attempt, not retry.
    if protocol == "family":
        assert positions == [0]  # Sequence 2 is held out, so it is not observed.
    else:
        assert positions == [0, 2]  # Student-split history includes that earlier first attempt.


@pytest.mark.parametrize("partition", ("train", "validation"))
def test_omitted_prior_scored_target_is_rejected(bundle, partition):
    directory, _, _ = bundle
    path = directory / f"{partition}.jsonl"
    examples = [json.loads(line) for line in path.read_text().splitlines()]
    later = next(row for row in examples if any(observed["sequence_index"] == 0 for observed in row["history"]))
    later["history"] = [row for row in later["history"] if row["sequence_index"] != 0]
    path.write_text("".join(json.dumps(row) + "\n" for row in examples))
    _rehash(directory)
    with pytest.raises(ValueError, match="complete permitted first-attempt prefix"):
        load_training_bundle(directory)
