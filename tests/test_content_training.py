import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.embedding_cache import EncoderConfig, make_entry
from practice_engine.training.content import ContentTrainingConfig, fit_content


@pytest.fixture
def prepared():
    encoder = EncoderConfig(repository="synthetic/encoder", revision="a" * 40,
        tokenizer="synthetic/tokenizer", tokenizer_revision="b" * 40, pooling="mean",
        max_tokens=16, truncation="right", dimension=3)
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Prior", concept_ids=("loops",), correct=False, attempt_number=1,
        submitted_code="return 1;")
    first = PredictionExample(student_id="synthetic", target_sequence_index=1, history=(prior,), label=True,
        candidate=Candidate(problem_id="known", problem_text="Positive", concept_ids=("loops",)))
    negative = first.model_copy(update={"label": False, "candidate": Candidate(
        problem_id="negative", problem_text="Negative", concept_ids=("loops",))})
    heldout = first.model_copy(update={"candidate": Candidate(problem_id="held-out",
        problem_text="Held out", concept_ids=("validation-only",))})
    entries = {}
    for text, role, vector in [("Prior", "problem-text", [1., 2., 3.]),
        ("Positive", "problem-text", [3., 2., 1.]), ("Negative", "problem-text", [-3., -2., -1.]),
        ("Held out", "problem-text", [2., 1., 3.]), ("return 1;", "historical-code", [.2, .3, .4])]:
        entry = make_entry(text, role, encoder, vector)
        entries[entry.key_sha256] = entry
    return [first, negative, first], [heldout, negative], entries, encoder


def small(**changes):
    return ContentTrainingConfig(**{"max_epochs": 4, "patience": 2, "batch_size": 2,
        "projection_size": 4, "concept_size": 3, "correctness_size": 2, "hidden_size": 5, **changes})


def state_equal(one, two):
    return all(torch.equal(value, two.model.state_dict()[key]) for key, value in one.model.state_dict().items())


def test_deterministic_seed_train_only_vocabulary_and_heldout_content(prepared):
    train, validation, entries, encoder = prepared
    before = {key: entry.to_dict() for key, entry in entries.items()}
    first = fit_content(*prepared, config=small())
    second = fit_content(*prepared, config=small())
    different = fit_content(*prepared, config=small(seed=39))
    assert first.epochs == second.epochs and first.validation_probabilities == second.validation_probabilities
    assert state_equal(first, second) and not state_equal(first, different)
    assert first.vocabulary.concepts == ("loops",) and first.vocabulary.encode("validation-only") == 1
    assert first.best_epoch == min(first.epochs, key=lambda epoch: epoch.validation_log_loss).epoch
    changed = validation[0].model_copy(update={"candidate": validation[0].candidate.model_copy(
        update={"problem_text": "Negative"})})
    from practice_engine.training.content import _validation_probabilities
    alternative = _validation_probabilities(first.model, [changed], first.vocabulary, entries, encoder, 1)
    assert alternative[0] != first.validation_probabilities[0]
    assert before == {key: entry.to_dict() for key, entry in entries.items()}
    assert not first.model.training and all(p.device.type == "cpu" for p in first.model.parameters())


def test_training_learns_from_train_labels_not_validation_labels(prepared):
    train, validation, entries, encoder = prepared
    result = fit_content(train, validation, entries, encoder, config=small(max_epochs=12, learning_rate=.05))
    assert result.epochs[-1].training_bce < result.epochs[0].training_bce
    original = fit_content(*prepared, config=small(max_epochs=1))
    flipped = [row.model_copy(update={"label": not row.label}) for row in validation]
    changed = fit_content(train, flipped, entries, encoder, config=small(max_epochs=1))
    assert state_equal(original, changed)
    assert original.validation_probabilities == changed.validation_probabilities
    assert original.epochs[0].validation_log_loss != changed.epochs[0].validation_log_loss
    flipped_train = [row.model_copy(update={"label": not row.label}) for row in train]
    assert not state_equal(original, fit_content(flipped_train, validation, entries, encoder, config=small(max_epochs=1)))


def test_plateau_first_best_patience_and_exact_weight_restore(prepared, monkeypatch):
    monkeypatch.setattr("practice_engine.training.content._validation_probabilities", lambda *args: [.5, .5])
    result = fit_content(*prepared, config=small(max_epochs=8))
    first = fit_content(*prepared, config=small(max_epochs=1))
    assert result.best_epoch == 1 and len(result.epochs) == 3
    assert state_equal(result, first)  # Optimizer kept moving after the retained first best epoch.


def test_minibatch_gradient_clipping_and_state_restoration_even_on_failure(prepared, monkeypatch):
    original = torch.nn.utils.clip_grad_norm_
    clips = []
    def tracked(parameters, maximum, **kwargs):
        clips.append((maximum, kwargs))
        return original(parameters, maximum, **kwargs)
    monkeypatch.setattr(torch.nn.utils, "clip_grad_norm_", tracked)
    threads, enabled, warn = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(False, warn_only=True)
        rng = torch.get_rng_state().clone()
        with torch.device("meta"):
            fit_content(*prepared, config=small(max_epochs=1))
            assert torch.empty(0).device.type == "meta"
        assert clips == [(5., {"error_if_nonfinite": True})] * 2
        assert torch.equal(rng, torch.get_rng_state()) and torch.get_num_threads() == 2
        assert not torch.are_deterministic_algorithms_enabled() and torch.is_deterministic_algorithms_warn_only_enabled()
        train, validation, _, encoder = prepared
        with pytest.raises(ValueError, match="embedding is missing"):
            fit_content(train, validation, {}, encoder, config=small())
        assert torch.equal(rng, torch.get_rng_state()) and torch.get_num_threads() == 2
        assert not torch.are_deterministic_algorithms_enabled() and torch.is_deterministic_algorithms_warn_only_enabled()
    finally:
        torch.use_deterministic_algorithms(enabled, warn_only=warn)
        torch.set_num_threads(threads)


@pytest.mark.parametrize("changes", [{"seed": True}, {"max_epochs": 0}, {"max_epochs": 501},
    {"batch_size": 257}, {"patience": 0}, {"projection_size": 257}, {"concept_size": 129},
    {"correctness_size": 33}, {"hidden_size": 257}, {"learning_rate": float("nan")},
    {"learning_rate": 10**1000}, {"learning_rate": True}])
def test_bounded_configuration_rejected(changes):
    with pytest.raises(ValueError):
        small(**changes)


def test_invalid_partitions_config_and_encoder_fail(prepared):
    train, validation, entries, encoder = prepared
    for bad_train, bad_validation in (([], validation), (train, []), (iter(train), validation)):
        with pytest.raises(ValueError):
            fit_content(bad_train, bad_validation, entries, encoder, config=small())
    with pytest.raises(ValueError):
        fit_content(*prepared, config={})
    with pytest.raises(ValueError, match="bounds"):
        fit_content(train, validation, entries, encoder.model_copy(update={"dimension": 4097}), config=small())
