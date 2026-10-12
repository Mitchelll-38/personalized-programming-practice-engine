"""Original synthetic exercises; no real student data."""

import pytest

from practice_engine.data.holdouts import family_holdout
from practice_engine.data.schema import Interaction


def row(problem, index, *, student="s1", correct=True, attempt=1):
    return Interaction(student_id=student, problem_id=problem, sequence_index=index,
                       problem_text=f"Synthetic statement for {problem}", concept_ids=("loops",),
                       correct=correct, attempt_number=attempt, submitted_code=f"code-{problem}")


def fixture():
    families = {f"p{i}": f"family-{i // 2}" for i in range(12)}
    return [row(problem, index) for index, problem in enumerate(families)], families


def test_family_groups_are_disjoint_nonempty_and_reproducible():
    rows, families = fixture()
    result = family_holdout(rows, families)
    groups = [set(ids) for ids in result.metadata["family_ids"].values()]
    assert all(groups)
    assert len(set.union(*groups)) == 6
    assert all(not a & b for i, a in enumerate(groups) for b in groups[i + 1:])
    for partition, examples in result.examples.items():
        assert examples
        assert {families[e.candidate.problem_id] for e in examples} == set(
            result.metadata["family_ids"][partition])
    assert result == family_holdout(list(reversed(rows)), families)
    assert result.metadata["version"] == "family-holdout-v1"
    assert result.metadata["seed"] == 38


def test_partition_assignment_does_not_depend_on_labels_or_submitted_code():
    rows, families = fixture()
    changed = [r.model_copy(update={"correct": False, "submitted_code": "changed"}) for r in rows]
    before, after = family_holdout(rows, families), family_holdout(changed, families)
    assert before.metadata == after.metadata
    for group in before.examples:
        assert [e.candidate for e in before.examples[group]] == [e.candidate for e in after.examples[group]]


def test_held_out_responses_never_enter_any_partition_history():
    rows, families = fixture()
    initial = family_holdout(rows, families)
    train = initial.metadata["problem_ids"]["train"]
    held_out = initial.metadata["problem_ids"]["validation"] + initial.metadata["problem_ids"]["test"]
    # Put held-out exercises first so they precede even the training targets.
    ordered = [row(p, i) for i, p in enumerate(held_out + train)]
    ordered.append(row(train[0], len(ordered), attempt=2))
    result = family_holdout(ordered, families)
    changed = [r.model_copy(update={"correct": False, "submitted_code": "HELD-OUT SECRET"})
               if r.problem_id in held_out else r for r in ordered]
    after = family_holdout(changed, families)
    assert len(result.examples["train"]) == len(train)
    for partition, examples in result.examples.items():
        assert [e.history for e in examples] == [e.history for e in after.examples[partition]]
        for example in examples:
            assert all(h.problem_id in train and h.attempt_number == 1 for h in example.history)
            assert all(h.sequence_index < example.target_sequence_index for h in example.history)
            assert example.candidate.problem_id not in {h.problem_id for h in example.history}


def test_histories_are_student_specific_and_first_attempt_chronological():
    rows, families = fixture()
    result = family_holdout(rows + [r.model_copy(update={"student_id": "s2"}) for r in rows], families)
    for examples in result.examples.values():
        for example in examples:
            assert all(h.student_id == example.student_id for h in example.history)
            assert [h.sequence_index for h in example.history] == sorted(h.sequence_index for h in example.history)


def test_missing_empty_and_insufficient_observed_families_fail():
    rows, families = fixture()
    with pytest.raises(ValueError, match="Missing family"):
        family_holdout(rows, {})
    with pytest.raises(ValueError, match="nonempty string"):
        family_holdout(rows, {**families, "p0": " "})
    with pytest.raises(ValueError, match="three observed families"):
        family_holdout(rows[:2], {**families, "unused": "another-family"})
    with pytest.raises(ValueError, match="Seed"):
        family_holdout(rows, families, seed=True)


def test_invalid_chronology_and_retry_numbers_fail():
    rows, families = fixture()
    with pytest.raises(ValueError, match="sequence index"):
        family_holdout(rows + [row("p1", 0)], families)
    with pytest.raises(ValueError, match="Attempt numbers"):
        family_holdout([row("p0", 0, attempt=2)], families)
