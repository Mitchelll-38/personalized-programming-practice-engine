from hashlib import sha256
import json
import subprocess
import sys

import pytest

from practice_engine.data.manifest import ARTIFACT_NAMES, verify_manifest
from practice_engine.data.pipeline import prediction_examples, student_split
from practice_engine.data.schema import Interaction


@pytest.fixture
def inputs(tmp_path):
    rows = [Interaction(student_id=f"s{s}", problem_id=f"p{p}", sequence_index=p,
                        problem_text=f"Original synthetic exercise {p}", concept_ids=("loops",),
                        correct=p % 2 == 0, attempt_number=1, submitted_code=f"synthetic-{p}")
            for s in range(3) for p in range(6)]
    source, mapping = tmp_path / "source.jsonl", tmp_path / "families.json"
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8")
    mapping.write_text(json.dumps({f"p{p}": f"family-{p // 2}" for p in range(6)}), encoding="utf-8")
    return source, mapping, rows


def run_cli(source, output, *flags):
    return subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source),
                           "--output", str(output), "--synthetic", *flags], capture_output=True, text=True)


def test_family_cli_provenance_partition_boundaries_and_label_independence(inputs, tmp_path):
    source, mapping, rows = inputs
    output = tmp_path / "output"
    flags = ("--split-protocol", "family", "--family-map", str(mapping))
    result = run_cli(source, output, *flags)
    assert result.returncode == 0, result.stderr
    manifest = verify_manifest(output / "manifest.json")
    assert manifest.split_version == "family-holdout-v1" and manifest.source_kind == "synthetic"
    assert set(manifest.artifact_sha256) == set(ARTIFACT_NAMES)
    split = json.loads((output / "split.json").read_text())
    audit = json.loads((output / "audit.json").read_text())
    assert split["family_map_sha256"] == audit["family_map_sha256"] == sha256(mapping.read_bytes()).hexdigest()
    assert split["source_sha256"] == sha256(source.read_bytes()).hexdigest() and split["seed"] == 38
    groups = [set(group) for group in split["family_ids"].values()]
    assert all(groups) and all(not a & b for i, a in enumerate(groups) for b in groups[i + 1:])
    for group in split["problem_ids"]:
        examples = [json.loads(line) for line in (output / f"{group}.jsonl").read_text().splitlines()]
        assert examples and {e["candidate"]["problem_id"] for e in examples} == set(split["problem_ids"][group])
        for example in examples:
            assert all(h["problem_id"] in split["problem_ids"]["train"] and h["sequence_index"] < example["target_sequence_index"]
                       for h in example["history"])
    first_bytes = {name: (output / name).read_bytes() for name in (*ARTIFACT_NAMES, "manifest.json")}
    assert run_cli(source, output, *flags).returncode != 0
    assert first_bytes == {name: (output / name).read_bytes() for name in first_bytes}
    source.write_text("".join(row.model_copy(update={"correct": not row.correct}).model_dump_json() + "\n" for row in rows))
    changed = tmp_path / "changed"
    assert run_cli(source, changed, *flags).returncode == 0
    changed_split = json.loads((changed / "split.json").read_text())
    assert changed_split["family_ids"] == split["family_ids"]
    assert changed_split["problem_ids"] == split["problem_ids"]


@pytest.mark.parametrize("content", ["[]", '{"p0":"a","p0":"b"}', '{}', '{"p0":1}',
                                      json.dumps({f"p{i}": "same-family" for i in range(6)})])
def test_invalid_family_map_writes_nothing(inputs, tmp_path, content):
    source, mapping, _ = inputs
    mapping.write_text(content)
    output = tmp_path / "invalid"
    assert run_cli(source, output, "--split-protocol", "family", "--family-map", str(mapping)).returncode != 0
    assert not output.exists()


def test_family_argument_pairs_fail_before_input_read(inputs, tmp_path):
    _, mapping, _ = inputs
    for flags in [("--split-protocol", "family"), ("--family-map", str(mapping))]:
        output = tmp_path / "invalid"
        result = run_cli(tmp_path / "missing.jsonl", output, *flags)
        assert result.returncode != 0 and "--family-map" in result.stderr
        assert not output.exists()


def test_student_default_matches_existing_partition_bytes(inputs, tmp_path):
    source, _, rows = inputs
    output = tmp_path / "student"
    assert run_cli(source, output).returncode == 0
    split = student_split(rows)
    examples = prediction_examples(rows)
    for group, ids in split["student_ids"].items():
        expected = "".join(e.model_dump_json() + "\n" for e in examples if e.student_id in ids)
        assert (output / f"{group}.jsonl").read_text() == expected
    assert verify_manifest(output / "manifest.json").split_version == "student-split-v1"
