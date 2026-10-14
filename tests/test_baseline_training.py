import json
import subprocess
import sys

import pytest

from practice_engine.data.manifest import artifact_hashes
from practice_engine.data.schema import Interaction
from practice_engine.evaluation import evaluate
from practice_engine.models.portable import load_baseline_artifact
from practice_engine.training import baselines
from practice_engine.training.bundle import load_training_bundle


@pytest.fixture(params=["student", "family"])
def bundle(request, tmp_path):
    source = tmp_path / "source.jsonl"
    rows = [Interaction(student_id=f"s{s}", problem_id=f"p{p}", sequence_index=p,
                        problem_text="Synthetic exercise", concept_ids=("loops",),
                        correct=p % 2 == 0, attempt_number=1)
            for s in range(6) for p in range(6)]
    source.write_text("".join(row.model_dump_json() + "\n" for row in rows))
    mapping = tmp_path / "families.json"
    mapping.write_text(json.dumps({f"p{p}": f"f{p // 2}" for p in range(6)}))
    output = tmp_path / "bundle"
    flags = ["--split-protocol", request.param]
    if request.param == "family":
        flags += ["--family-map", str(mapping)]
    subprocess.run([sys.executable, "-m", "practice_engine.data.cli", str(source),
                    "--synthetic", "--dataset-version", "synthetic-baseline-v1", "--output", str(output),
                    *flags], check=True, capture_output=True)
    return output


def rehash(bundle):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifact_sha256"] = artifact_hashes(bundle)
    path.write_text(json.dumps(manifest))


@pytest.mark.parametrize("kind", ["logistic", "bkt"])
def test_runs_reload_reproduce_and_never_parse_test(bundle, tmp_path, kind):
    loaded = load_training_bundle(bundle)
    before = baselines.train_baseline(bundle, tmp_path / "before", model_kind=kind)
    (bundle / "test.jsonl").write_bytes(b"\xffPOISON non-JSON test labels")
    rehash(bundle)
    after = baselines.train_baseline(bundle, tmp_path / "after", model_kind=kind)
    first = load_baseline_artifact(tmp_path / "before/model.json")
    second = load_baseline_artifact(tmp_path / "after/model.json")
    assert first == second
    assert before["processing_manifest_sha256"] != after["processing_manifest_sha256"]
    assert before["test_evaluated"] is after["test_evaluated"] is False
    assert before["research_results"] is before["calibrated"] is False
    assert before["reload_predictions_equal"] is True
    assert before["provenance"] == loaded.provenance.model_dump()
    assert first.model_sha256 == before["model_sha256"]
    assert before["seed"] == loaded.manifest.seed
    metrics = json.loads((tmp_path / "before/validation.json").read_text())
    assert metrics == evaluate(loaded.validation, first.predict(loaded.validation))
    assert (tmp_path / "before/validation.json").read_bytes() == (tmp_path / "after/validation.json").read_bytes()
    with pytest.raises(ValueError, match="new directory"):
        baselines.train_baseline(bundle, tmp_path / "before", model_kind=kind)


@pytest.mark.parametrize("kind", ["logistic", "bkt"])
def test_atomic_cleanup_on_reload_failure(bundle, tmp_path, monkeypatch, kind):
    def fail(path):
        assert path.is_file()
        raise ValueError("reload failure")
    monkeypatch.setattr(baselines, "load_baseline_artifact", fail)
    with pytest.raises(ValueError, match="reload failure"):
        baselines.train_baseline(bundle, tmp_path / "runs/failed", model_kind=kind)
    assert list((tmp_path / "runs").iterdir()) == []


@pytest.mark.parametrize("config", [{"C": 0}, {"C": float("nan")}, {"max_iter": 0}, {"max_iter": True}])
def test_invalid_logistic_configuration_never_publishes(bundle, tmp_path, config):
    with pytest.raises(ValueError):
        baselines.train_baseline(bundle, tmp_path / "bad", model_kind="logistic", **config)
    assert not (tmp_path / "bad").exists()


def test_commands_and_model_specific_options(bundle, tmp_path):
    command = [sys.executable, "-m", "practice_engine.training.baselines", str(bundle),
               "--output", str(tmp_path / "cli"), "--model", "logistic", "--C", "0.5", "--max-iter", "2000"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["config"] == {"C": 0.5, "max_iter": 2000, "seed": 38}
    command[command.index("logistic")] = "bkt"
    failure = subprocess.run(command, capture_output=True, text=True)
    assert failure.returncode == 2 and "only valid" in failure.stderr
    with pytest.raises(ValueError, match="only valid"):
        baselines.train_baseline(bundle, tmp_path / "invalid", model_kind="bkt", C=1)


def test_shared_boundary_blocks_target_membership_and_unverified_input(bundle, tmp_path):
    path = bundle / "train.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    split = json.loads((bundle / "split.json").read_text())
    if "student_ids" in split:
        rows[0]["student_id"] = split["student_ids"]["validation"][0]
    else:
        rows[0]["candidate"]["problem_id"] = split["problem_ids"]["validation"][0]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    rehash(bundle)
    with pytest.raises(ValueError, match="partition"):
        baselines.train_baseline(bundle, tmp_path / "invalid", model_kind="bkt")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_kind"] = "unverified"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="synthetic"):
        baselines.train_baseline(bundle, tmp_path / "invalid", model_kind="logistic")
    assert not (tmp_path / "invalid").exists()
