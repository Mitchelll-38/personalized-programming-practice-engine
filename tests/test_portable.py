import json

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.artifacts import ArtifactProvenance, save_rate_artifact
from practice_engine.models.bkt import BKTBaseline
from practice_engine.models.logistic import LogisticBaseline
from practice_engine.models.portable import load_baseline_artifact, save_baseline_artifact
from practice_engine.models.rates import RateBaseline


@pytest.mark.parametrize("model_class", [LogisticBaseline, BKTBaseline])
def test_portable_baseline_reload_and_mutation_rejection(tmp_path, model_class):
    rows = [PredictionExample(student_id="s", target_sequence_index=i, history=(), label=bool(i),
        candidate=Candidate(problem_id=f"p{i}", problem_text="Synthetic", concept_ids=("loops",))) for i in range(2)]
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    model = model_class.fit(rows)
    path = tmp_path / "model.json"
    save_baseline_artifact(path, model, provenance)
    loaded = load_baseline_artifact(path)
    assert loaded.predict(rows) == model.predict(rows)
    data = json.loads(path.read_text())
    data["feature_version"] = "future"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_baseline_artifact(path)
    if model_class is LogisticBaseline:
        loaded.model_payload["intercept"] += 1
    else:
        loaded.model_payload["parameters"]["initial"] = 0.9
    with pytest.raises(ValueError, match="hash mismatch"):
        loaded.predict(rows)


@pytest.mark.parametrize("payload", [[], {"artifact_version": "future"}])
def test_unknown_or_non_object_artifact_rejected(tmp_path, payload):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_baseline_artifact(path)


def test_generic_loader_keeps_rate_artifact_compatibility(tmp_path):
    row = PredictionExample(student_id="s", target_sequence_index=0, history=(), label=True,
        candidate=Candidate(problem_id="p", problem_text="Synthetic", concept_ids=("loops",)))
    provenance = ArtifactProvenance(dataset_version="synthetic-v1", source_kind="synthetic",
        source_sha256="a" * 64, split_version="student-split-v1", split_sha256="b" * 64)
    path = tmp_path / "model.json"
    saved = save_rate_artifact(path, RateBaseline.fit([row]), provenance)
    assert load_baseline_artifact(path).predict([row]) == saved.predict([row])
