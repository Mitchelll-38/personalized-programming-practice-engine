import csv
from hashlib import sha256

import pytest

from practice_engine.data.organizer_catalog import CONCEPTS, HEADERS, map_organizer_catalog
from practice_engine.models.artifacts import payload_hash


def row(assignment="7", problem="1", prompt="Original synthetic prompt", tags=("If/Else",)):
    return [assignment, problem, prompt, *("1" if tag in tags else "" for tag in CONCEPTS)]


def write(tmp_path, rows, headers=HEADERS, *, bom=False):
    path = tmp_path / "catalog.csv"
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def test_preserves_exact_release_ids_prompts_concepts_and_detached_identity(tmp_path):
    prompt = '  Original synthetic "prompt"\r\nwith Unicode α  '
    path = write(tmp_path, [row(prompt=prompt, tags=("If/Else", "Math%")),
                            row(problem="2", tags=("DefFunction",))], bom=True)
    inventory = ["7.00:2", "7.00:1"]
    result = map_organizer_catalog(path, inventory)
    assert [candidate.problem_id for candidate in result.candidates] == ["7.00:1", "7.00:2"]
    assert result.candidates[0].problem_text == prompt
    assert result.candidates[0].concept_ids == ("If/Else", "Math%")
    assert result.candidates[1].concept_ids == ("DefFunction",)
    receipt = result.receipt
    assert receipt["catalog_sha256"] == sha256(path.read_bytes()).hexdigest()
    assert receipt["release_inventory_sha256"] == payload_hash({"problem_ids": sorted(inventory)})
    assert receipt["crosswalk"] == {"7": "7.00"}
    assert receipt["crosswalk_sha256"] == payload_hash({"assignment_crosswalk": receipt["crosswalk"]})
    assert receipt["column_policy_sha256"] == payload_hash(receipt["column_policy"])
    assert receipt["candidate_sha256"] == payload_hash({"candidates": [item.model_dump(mode="json") for item in result.candidates]})
    receipt["column_policy"]["headers"].clear()
    receipt["crosswalk"]["7"] = "changed"
    inventory.clear()
    assert result.receipt["column_policy"]["headers"] == list(HEADERS)
    assert result.receipt["crosswalk"] == {"7": "7.00"}


def test_integer_identity_reverse_crosswalk_and_input_order_invariance(tmp_path):
    path = write(tmp_path, [row("7.0", "2"), row("7.0", "1")])
    one = map_organizer_catalog(path, ["7:2", "7:1"])
    two = map_organizer_catalog(path, ["7:1", "7:2"])
    assert one == two and one.receipt["crosswalk"] == {"7.0": "7"}
    assert map_organizer_catalog(write(tmp_path, [row("0", "0")]), ["0:0"]).candidates[0].problem_id == "0:0"


@pytest.mark.parametrize("bad", ["+7", "-7", "07", "7.1", "7e0", "7.", " 7", "7 ", "７", "", "7:1"])
def test_assignment_spelling_rejected_on_either_side(tmp_path, bad):
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [row(bad)]), ["7.0:1"])
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [row()]), [bad + ":1"])


@pytest.mark.parametrize("bad", ["01", "1.0", "1e0", "+1", "-1", " 1", "１", ""])
def test_problem_spelling_never_normalized(tmp_path, bad):
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [row(problem=bad)]), ["7.0:1"])
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [row()]), ["7.0:" + bad])


@pytest.mark.parametrize("headers", [HEADERS[::-1], HEADERS[:-1], (*HEADERS, "extra"),
                                    (*HEADERS[:3], "if_else", *HEADERS[4:]), ("ProblemID", *HEADERS[1:])])
def test_exact_headers_required(tmp_path, headers):
    with pytest.raises(ValueError, match="headers"):
        map_organizer_catalog(write(tmp_path, [row()], headers), ["7.0:1"])


@pytest.mark.parametrize("cell", ["0", "1.0", "true", "2", " 1", "1 ", " "])
def test_only_exact_one_or_empty_concept_cells(tmp_path, cell):
    record = row()
    record[3] = cell
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [record]), ["7.0:1"])


@pytest.mark.parametrize("records,inventory", [
    ([row(), row()], ["7.0:1"]), ([row(), row("7.0", "2")], ["7.0:1", "7.0:2"]),
    ([row(problem="1"), row(problem="2")], ["7:1", "7.0:2"]),
    ([row()], ["7.0:1", "7.0:2"]), ([row(), row(problem="2")], ["7.0:1"]),
    ([row("8")], ["7.0:1"]), ([row(prompt=" \n")], ["7.0:1"]),
    ([row(tags=())], ["7.0:1"]), ([row()[:-1]], ["7.0:1"]), ([], ["7.0:1"]),
])
def test_collisions_coverage_and_incomplete_rows_fail(tmp_path, records, inventory):
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, records), inventory)


@pytest.mark.parametrize("inventory", [[], ["7.0:1", "7.0:1"], [1], ["missing-colon"], ["7:1:2"], {"7:1"}])
def test_explicit_unique_inventory_required(tmp_path, inventory):
    with pytest.raises(ValueError):
        map_organizer_catalog(write(tmp_path, [row()]), inventory)


def test_malformed_csv_fails_and_prompt_mutation_changes_identity(tmp_path):
    path = write(tmp_path, [row()])
    before = map_organizer_catalog(path, ["7.0:1"])
    after = map_organizer_catalog(write(tmp_path, [row(prompt="Changed original synthetic prompt")]), ["7.0:1"])
    assert before.receipt["catalog_sha256"] != after.receipt["catalog_sha256"]
    assert before.receipt["candidate_sha256"] != after.receipt["candidate_sha256"]
    path.write_text(','.join(HEADERS) + '\n"unclosed')
    with pytest.raises(ValueError, match="Malformed"):
        map_organizer_catalog(path, ["7.0:1"])
