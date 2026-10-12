import json

import pytest

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.features import historical_features
from practice_engine.models.logistic import LogisticBaseline


def examples():
    result = []
    for i in range(16):
        rows = tuple(Interaction(student_id=f"s{i}", problem_id=f"prior{j}", sequence_index=j,
                                 problem_text="Prior", concept_ids=("loops",), correct=i % 2 == 0,
                                 attempt_number=1) for j in range(i % 8))
        result.append(PredictionExample(
            student_id=f"s{i}", target_sequence_index=10, history=rows,
            candidate=Candidate(problem_id="target", problem_text="Synthetic", concept_ids=("loops",)),
            label=i % 2 == 0,
        ))
    return result


def test_train_scaling_prediction_labels_and_json_reload():
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    train = examples()
    model = LogisticBaseline.fit(train)
    payload = model.to_dict()
    scaler = StandardScaler().fit(historical_features(train))
    reference = LogisticRegression(C=1, max_iter=1000, random_state=38, tol=1e-8, solver="lbfgs")
    reference.fit(scaler.transform(historical_features(train)), [int(e.label) for e in train])
    assert payload["means"] == pytest.approx(scaler.mean_)
    assert payload["scales"] == pytest.approx(scaler.scale_)
    assert model.predict(train) == pytest.approx(reference.predict_proba(scaler.transform(historical_features(train)))[:, 1])
    before = model.to_dict()
    changed = [e.model_copy(update={"label": not e.label}) for e in train]
    assert model.predict(train) == model.predict(changed)
    assert model.to_dict() == before
    restored = LogisticBaseline.from_dict(json.loads(json.dumps(payload)))
    assert restored.predict(train) == model.predict(train)
    assert model.predict([]) == []
    payload["means"][0] = 999
    assert model.to_dict() == before
    assert LogisticBaseline.fit(train).to_dict() == before


@pytest.mark.parametrize("kwargs", [
    {"C": 0}, {"C": float("nan")}, {"C": float("inf")}, {"C": True},
    {"max_iter": 0}, {"max_iter": True}, {"seed": -1}, {"seed": 2**32}, {"seed": True},
])
def test_invalid_training_config_rejected(kwargs):
    with pytest.raises(ValueError):
        LogisticBaseline.fit(examples(), **kwargs)


def test_empty_one_class_and_nonconvergence_rejected():
    for train in ([], [e for e in examples() if e.label]):
        with pytest.raises(ValueError, match="both outcome classes"):
            LogisticBaseline.fit(train)
    with pytest.raises(ValueError, match="did not converge"):
        LogisticBaseline.fit(examples(), max_iter=1)


@pytest.mark.parametrize("change", [
    lambda p: p.update(extra="unknown"),
    lambda p: p.update(feature_version="future"),
    lambda p: p["feature_names"].reverse(),
    lambda p: p.update(coefficients=[0.0]),
    lambda p: p["means"].__setitem__(0, float("nan")),
    lambda p: p["scales"].__setitem__(0, 0.0),
    lambda p: p["coefficients"].__setitem__(0, float("inf")),
    lambda p: p.update(intercept=float("inf")),
    lambda p: p.update(C=True),
    lambda p: p.update(seed=True),
])
def test_invalid_saved_parameters_rejected(change):
    payload = LogisticBaseline.fit(examples()).to_dict()
    change(payload)
    with pytest.raises(ValueError):
        LogisticBaseline.from_dict(payload)


def test_extreme_finite_score_has_stable_sigmoid():
    payload = LogisticBaseline.fit(examples()).to_dict()
    payload.update(coefficients=[0.0] * 6, intercept=1000.0)
    assert LogisticBaseline.from_dict(payload).predict(examples()) == [1.0] * 16
    payload["intercept"] = -1000.0
    assert LogisticBaseline.from_dict(payload).predict(examples()) == [0.0] * 16
