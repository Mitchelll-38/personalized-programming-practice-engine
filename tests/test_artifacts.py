import json

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, load_rate_artifact, save_rate_artifact
from practice_engine.models.rates import RateBaseline


def examples():
    return [PredictionExample(student_id="s", target_sequence_index=i, history=(),
                              candidate=Candidate(problem_id=f"p{i}", problem_text="Synthetic", concept_ids=("loops",)),
                              label=bool(i)) for i in range(2)]


def provenance():
    return ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
                              source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)


@pytest.mark.parametrize("variant", ["global", "problem"])
def test_rate_artifact_roundtrip_parity(tmp_path, variant):
    rows = examples()
    model = RateBaseline.fit(rows)
    path = tmp_path / "nested/model.json"
    saved = save_rate_artifact(path, model, provenance(), variant)
    loaded = load_rate_artifact(path)
    assert loaded == saved
    assert loaded.predict(rows) == model.predict(rows, per_problem=variant == "problem")
    assert loaded.provenance.source_kind == "synthetic" and loaded.calibrated is False
    assert loaded.provenance.fit_partition == "train"


@pytest.mark.parametrize("change", [
    lambda data: data.update(artifact_version="future"),
    lambda data: data.update(extra="untrusted"),
    lambda data: data.update(calibrated=True),
    lambda data: data.update(calibrated=0),
    lambda data: data.update(model_sha256="0" * 64),
    lambda data: data["provenance"].update(fit_partition="test"),
    lambda data: data["provenance"].update(source_kind="verified"),
    lambda data: data["model_payload"].update(alpha=2.0),
])
def test_corrupt_or_misdeclared_artifact_rejected(tmp_path, change):
    path = tmp_path / "model.json"
    save_rate_artifact(path, RateBaseline.fit(examples()), provenance())
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_rate_artifact(path)


def test_live_payload_mutation_cannot_change_predictions_under_old_hash(tmp_path):
    path = tmp_path / "model.json"
    loaded = save_rate_artifact(path, RateBaseline.fit(examples()), provenance())
    loaded.model_payload["alpha"] = 2.0
    with pytest.raises(ValueError, match="hash mismatch"):
        loaded.predict(examples())


@pytest.mark.parametrize("old,new", [
    ('"variant": "problem"', '"variant": "global", "variant": "problem"'),
    ('"source_kind": "synthetic"', '"source_kind": "unverified", "source_kind": "synthetic"'),
])
def test_duplicate_artifact_fields_rejected_even_when_effective_values_match(tmp_path, old, new):
    path = tmp_path / "model.json"
    save_rate_artifact(path, RateBaseline.fit(examples()), provenance())
    serialized = path.read_text()
    assert old in serialized
    path.write_text(serialized.replace(old, new, 1))
    with pytest.raises(ValueError, match="Duplicate artifact JSON field"):
        load_rate_artifact(path)


def test_failed_atomic_replace_preserves_previous_artifact_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "model.json"
    save_rate_artifact(path, RateBaseline.fit(examples()), provenance())
    before = path.read_bytes()
    def fail_replace(*_):
        raise OSError("simulated replace failure")
    monkeypatch.setattr("practice_engine.models.artifacts.os.replace", fail_replace)
    with pytest.raises(OSError, match="replace failure"):
        save_rate_artifact(path, RateBaseline.fit(examples(), alpha=2.0), provenance())
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
