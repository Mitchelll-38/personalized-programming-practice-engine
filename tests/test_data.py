import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from practice_engine.data.pipeline import first_attempts, prediction_examples, student_split
from practice_engine.data.schema import Candidate, Interaction
from practice_engine.training.bundle import load_training_bundle


FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic.jsonl"


def row(student="s1", problem="p1", index=0, correct=True, attempt=1):
    return Interaction(student_id=student, problem_id=problem, sequence_index=index,
                       problem_text="Return the sum.", concept_ids=("loops",),
                       correct=correct, attempt_number=attempt, submitted_code="return 1;")


def test_candidate_cannot_contain_target_response():
    with pytest.raises(ValidationError):
        Candidate(problem_id="p1", problem_text="Sum", concept_ids=("loops",), correct=True)


def test_target_code_and_label_are_not_prediction_inputs():
    before = prediction_examples([row(), row(problem="p2", index=1)])
    changed = prediction_examples([row(), row(problem="p2", index=1, correct=False).model_copy(update={"submitted_code": "TARGET SECRET"})])
    assert before[1].history == changed[1].history
    assert before[1].candidate == changed[1].candidate
    assert "submitted_code" not in before[1].candidate.model_dump()


def test_future_attempt_cannot_change_earlier_example():
    prefix = [row(), row(problem="p2", index=1)]
    assert prediction_examples(prefix) == prediction_examples(prefix + [row(problem="p3", index=2, correct=False)])[:2]


def test_first_attempts_exclude_retries_and_sort_input():
    rows = [row(problem="p2", index=2), row(index=1, attempt=2), row()]
    examples = prediction_examples(rows)
    assert len(examples) == 2
    assert len(examples[1].history) == 1
    assert examples[0].history == ()


def test_ambiguous_order_and_missing_initial_attempt_fail():
    with pytest.raises(ValueError, match="sequence index"):
        first_attempts([row(), row(problem="p2")])
    with pytest.raises(ValueError, match="Attempt numbers"):
        first_attempts([row(attempt=2)])


def test_student_split_disjoint_reproducible_and_label_independent():
    rows = [row(student=f"s{i}") for i in range(12)]
    split = student_split(rows)
    groups = [set(ids) for ids in split["student_ids"].values()]
    assert all(groups)
    assert len(set.union(*groups)) == 12
    assert not groups[0] & groups[1] and not groups[0] & groups[2] and not groups[1] & groups[2]
    assert split == student_split(list(reversed(rows)))
    assert split == student_split([r.model_copy(update={"correct": False}) for r in rows])


def test_outcomes_and_sequence_numbers_are_strict():
    with pytest.raises(ValidationError):
        row(correct="false")
    with pytest.raises(ValidationError):
        row(index=True)


def test_blank_student_id_cannot_publish_processing_bundle(tmp_path):
    for student_id in ("", " \t\n"):
        with pytest.raises(ValidationError):
            row(student=student_id)
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]
    original = rows[0]["student_id"]
    for record in rows:
        if record["student_id"] == original:
            record["student_id"] = " \t"
    source = tmp_path / "blank-student.jsonl"
    source.write_text("".join(json.dumps(record) + "\n" for record in rows))
    command = [sys.executable, "-m", "practice_engine.data.cli", str(source),
               "--synthetic", "--output", str(tmp_path / "invalid")]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / "invalid").exists()
    command[3] = str(FIXTURE)
    command[-1] = str(tmp_path / "valid")
    subprocess.run(command, capture_output=True, check=True)
    assert load_training_bundle(tmp_path / "valid").train
