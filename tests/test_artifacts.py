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
