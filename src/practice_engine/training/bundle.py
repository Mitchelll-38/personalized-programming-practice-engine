"""Verified synthetic train/validation inputs; test bytes are hashed, never parsed."""

from bisect import bisect_left
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from practice_engine.data.manifest import ProcessingManifest, verify_manifest
from practice_engine.data.pipeline import validate_problem_metadata
from practice_engine.data.schema import PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance
from practice_engine.models.features import historical_features

PARTITIONS = ("train", "validation", "test")


@dataclass(frozen=True)
class TrainingBundle:
    train: list[PredictionExample]
    validation: list[PredictionExample]
    manifest: ProcessingManifest
    split: dict
    provenance: ArtifactProvenance


def _groups(value) -> dict[str, set[str]]:
    if not isinstance(value, dict) or set(value) != set(PARTITIONS):
        raise ValueError("Split must declare exactly train/validation/test groups")
    groups = {}
    for name, ids in value.items():
        if (not isinstance(ids, list) or not ids or
                any(not isinstance(identifier, str) or not identifier.strip() for identifier in ids) or
                len(ids) != len(set(ids))):
            raise ValueError("Split groups require unique nonempty string IDs")
        groups[name] = set(ids)
    if any(groups[a] & groups[b] for i, a in enumerate(PARTITIONS) for b in PARTITIONS[i + 1:]):
        raise ValueError("Split partitions overlap")
    return groups


def _check_scored_history_consistency(examples: dict[str, list[PredictionExample]], *, family: bool) -> None:
    """Match complete permitted prefixes to scored first attempts outside test."""
    scored = [row for partition in ("train", "validation") for row in examples[partition]]
    by_position = {(row.student_id, row.target_sequence_index): row for row in scored}
    by_problem = {(row.student_id, row.candidate.problem_id): row for row in scored}
    permitted: dict[str, list[int]] = {}
    for partition in (("train",) if family else ("train", "validation")):
        for row in examples[partition]:
            permitted.setdefault(row.student_id, []).append(row.target_sequence_index)
    for positions in permitted.values():
        positions.sort()
    for example in scored:
        for observed in example.history:
            position = by_position.get((observed.student_id, observed.sequence_index))
            problem = by_problem.get((observed.student_id, observed.problem_id))
            if position is not None and (
                    position.candidate.problem_id != observed.problem_id
                    or position.candidate.problem_text != observed.problem_text
                    or position.candidate.concept_ids != observed.concept_ids
                    or position.label != observed.correct):
                raise ValueError("History contradicts a scored target at its sequence position")
            if problem is not None and problem.target_sequence_index != observed.sequence_index:
                raise ValueError("History contradicts a scored target's problem position")
        positions = permitted.get(example.student_id, [])
        expected = positions[:bisect_left(positions, example.target_sequence_index)]
        if [row.sequence_index for row in example.history] != expected:
            raise ValueError("History must contain the complete permitted first-attempt prefix")
    validate_problem_metadata(
        (row.problem_id, row.problem_text, row.concept_ids)
        for example in scored
        for row in (example.candidate, *example.history)
    )


def _verified_artifact_bytes(directory: Path, name: str, manifest: ProcessingManifest) -> bytes:
    """Bind the exact bytes consumed after initial bundle verification."""
    serialized = (directory / name).read_bytes()
    if sha256(serialized).hexdigest() != manifest.artifact_sha256[name]:
        raise ValueError(f"Processing artifact hash mismatch: {name}")
    return serialized


def load_training_bundle(directory: Path) -> TrainingBundle:
    manifest = verify_manifest(directory / "manifest.json")
    if manifest.source_kind != "synthetic":
        raise ValueError("This smoke workflow requires declared synthetic data; real-data provenance gate remains unmet")
    serialized = _verified_artifact_bytes(directory, "split.json", manifest)
    split = json.loads(serialized)
    protocols = {"student-split-v1": "held-out-students", "family-holdout-v1": "held-out-exercise-families"}
    if (not isinstance(split, dict) or split.get("version") != manifest.split_version or
            split.get("protocol") != protocols[manifest.split_version]):
        raise ValueError("Unsupported or mismatched split protocol")
    if (split.get("source_sha256") != manifest.source_sha256 or
            type(split.get("seed")) is not int or split["seed"] != manifest.seed):
        raise ValueError("Split source/seed differs from processing manifest")
    family = manifest.split_version == "family-holdout-v1"
    groups = _groups(split.get("problem_ids" if family else "student_ids"))
    if family:
        families = _groups(split.get("family_ids"))
        mapping = split.get("problem_families")
        if (not isinstance(mapping, dict) or set(mapping) != set.union(*groups.values()) or
                any(not isinstance(value, str) or not value.strip() for value in mapping.values()) or
                any({mapping[p] for p in groups[name]} != families[name] for name in PARTITIONS)):
            raise ValueError("Family/problem groups disagree with the family mapping")
        if split.get("history_policy") != "prior-first-attempt-training-exercises-only":
            raise ValueError("Unsupported family history policy")
        audit = json.loads(_verified_artifact_bytes(directory, "audit.json", manifest))
        digest = split.get("family_map_sha256")
        if (not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                or not isinstance(audit, dict) or audit.get("family_map_sha256") != digest):
            raise ValueError("Family map provenance differs from processing audit")
    examples = {}
    seen_positions = set()
    for name in ("train", "validation"):
        rows = [PredictionExample.model_validate_json(line) for line in
                _verified_artifact_bytes(directory, f"{name}.jsonl", manifest).splitlines() if line.strip()]
        if not rows or any((row.candidate.problem_id if family else row.student_id) not in groups[name] for row in rows):
            raise ValueError(f"Invalid or empty {name} {'family' if family else 'student'} partition")
        positions = [(row.student_id, row.target_sequence_index) for row in rows]
        targets = [(row.student_id, row.candidate.problem_id) for row in rows]
        if (len(set(positions)) != len(positions) or seen_positions.intersection(positions)
                or len(set(targets)) != len(targets)
                or any(row.target_sequence_index < 0 for row in rows)):
            raise ValueError("Duplicate or invalid target sequence positions")
        seen_positions.update(positions)
        historical_features(rows)
        if family and any(h.problem_id not in groups["train"] for row in rows for h in row.history):
            raise ValueError("Family histories must contain only training exercises")
        examples[name] = rows
    _check_scored_history_consistency(examples, family=family)
    provenance = ArtifactProvenance(dataset_version=manifest.dataset_version,
        source_kind=manifest.source_kind, source_sha256=manifest.source_sha256,
        split_version=manifest.split_version, split_sha256=sha256(serialized).hexdigest())
    return TrainingBundle(examples["train"], examples["validation"], manifest, split, provenance)
