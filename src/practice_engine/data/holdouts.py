"""Exercise-family holdouts with training-only observed response histories."""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import random

from .pipeline import first_attempts
from .schema import Candidate, Interaction, PredictionExample


@dataclass(frozen=True)
class FamilyHoldout:
    metadata: dict
    examples: dict[str, list[PredictionExample]]


def family_holdout(
    rows: list[Interaction], problem_families: Mapping[str, str], seed: int = 38,
) -> FamilyHoldout:
    """Partition observed families independently of responses and student IDs.

    The caller supplies an audited family map; no family inference, vocabulary
    fitting or outcome-dependent grouping happens here. Only training exercise
    responses enter histories, including for validation/test scored examples.
    """
    primary = first_attempts(rows)
    problems = sorted({row.problem_id for row in primary})
    missing = sorted(set(problems) - problem_families.keys())
    if missing:
        raise ValueError(f"Missing family mapping for problems: {missing}")
    if any(not isinstance(problem_families[p], str) or not problem_families[p].strip()
           for p in problems):
        raise ValueError("Observed problems require nonempty string family IDs")
    families = sorted({problem_families[p] for p in problems})
    if len(families) < 3:
        raise ValueError("Need at least three observed families for nonempty partitions")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed must be an integer")
    random.Random(seed).shuffle(families)
    n_validation = max(1, int(len(families) * 0.15))
    n_test = max(1, int(len(families) * 0.15))
    family_groups = {
        "train": sorted(families[:-(n_validation + n_test)]),
        "validation": sorted(families[-(n_validation + n_test):-n_test]),
        "test": sorted(families[-n_test:]),
    }
    partition_by_family = {family: partition for partition, group in family_groups.items()
                           for family in group}
    problem_groups = {
        partition: [p for p in problems if partition_by_family[problem_families[p]] == partition]
        for partition in family_groups
    }
    examples: dict[str, list[PredictionExample]] = {group: [] for group in family_groups}
    histories: dict[str, list[Interaction]] = defaultdict(list)
    for target in primary:
        partition = partition_by_family[problem_families[target.problem_id]]
        examples[partition].append(PredictionExample(
            student_id=target.student_id,
            target_sequence_index=target.sequence_index,
            history=tuple(histories[target.student_id]),
            candidate=Candidate(problem_id=target.problem_id, problem_text=target.problem_text,
                                concept_ids=target.concept_ids),
            label=target.correct,
        ))
        if partition == "train":
            histories[target.student_id].append(target)
    return FamilyHoldout(metadata={
        "protocol": "held-out-exercise-families", "version": "family-holdout-v1",
        "seed": seed, "ratios_requested": [0.70, 0.15, 0.15],
        "family_ids": family_groups, "problem_ids": problem_groups,
        "problem_families": {p: problem_families[p] for p in problems},
        "history_policy": "prior-first-attempt-training-exercises-only",
    }, examples=examples)
