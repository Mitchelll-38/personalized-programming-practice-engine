import json
import math

import pytest

from practice_engine.data.schema import Candidate, PredictionExample
from practice_engine.models.calibration import EPSILON, TemperatureScaler


def example(label):
    return PredictionExample(student_id="synthetic", target_sequence_index=0, history=(),
                             candidate=Candidate(problem_id="sum", problem_text="Sum",
                                                 concept_ids=("loops",)), label=label)


def test_overconfidence_softened_and_grid_order_independent():
    examples = [example(True), example(False)]
    model = TemperatureScaler.fit_validation(examples, [.9, .9], temperatures=(1, 2, 5))
    assert model.temperature == 5
    assert .5 < model.predict([.9])[0] < .9
    assert model == TemperatureScaler.fit_validation(examples, [.9, .9], temperatures=(5, 2, 1))
    assert model == TemperatureScaler.from_dict(json.loads(json.dumps(model.to_dict())))
    assert model.predict([.2, .8]) == pytest.approx([1 - model.predict([.8])[0], model.predict([.8])[0]])


def test_correct_confident_predictions_choose_sharpening_and_ties_choose_identity():
    examples = [example(True), example(False)]
    assert TemperatureScaler.fit_validation(examples, [.8, .2]).temperature == .5
    assert TemperatureScaler.fit_validation(examples, [.5, .5]).temperature == 1
    assert TemperatureScaler(1).predict([0, 1]) == pytest.approx([EPSILON, 1 - EPSILON])


def test_monotonic_portable_predictions_and_no_mutable_payload():
    model = TemperatureScaler(2)
    scores = model.predict([0, .01, .3, .5, .7, .99, 1])
    assert scores == sorted(scores) and scores[3] == .5
    assert all(math.isfinite(p) and 0 <= p <= 1 for p in scores)
    payload = model.to_dict()
    payload["temperature"] = 5
    assert model.temperature == 2
    assert model.predict([]) == []


@pytest.mark.parametrize("temperature", [True, 0, -1, 10**400, float("nan"), float("inf"), "1", None])
def test_invalid_temperature_rejected(temperature):
    with pytest.raises(ValueError):
        TemperatureScaler(temperature)


@pytest.mark.parametrize("probability", [True, -.1, 1.1, 10**400, float("nan"), float("inf"), "0.5"])
def test_invalid_probabilities_rejected(probability):
    with pytest.raises(ValueError):
        TemperatureScaler(1).predict([probability])


@pytest.mark.parametrize("grid", [(), (1, 1), (True, 1), (0, 1), (float("nan"), 1)])
def test_bad_grid_rejected(grid):
    with pytest.raises(ValueError):
        TemperatureScaler.fit_validation([example(True), example(False)], [.5, .5], temperatures=grid)


def test_invalid_validation_and_payload_rejected():
    for rows, scores in [([], []), ([example(True)], []), ([example(True)], [.5])]:
        with pytest.raises(ValueError):
            TemperatureScaler.fit_validation(rows, scores)
    for key, value in [("version", "future"), ("epsilon", True), ("fit_partition", "test"), ("extra", 1)]:
        payload = TemperatureScaler(1).to_dict()
        payload[key] = value
        with pytest.raises(ValueError):
            TemperatureScaler.from_dict(payload)


def test_subnormal_temperature_has_stable_limits_and_rejects_infinite_fit_loss():
    tiny = math.nextafter(0, 1)
    assert TemperatureScaler(tiny).predict([.1, .5, .9]) == [0, .5, 1]
    with pytest.raises(ValueError, match="finite fitting objective"):
        TemperatureScaler.fit_validation([example(True), example(False)], [.1, .9], temperatures=(tiny,))
