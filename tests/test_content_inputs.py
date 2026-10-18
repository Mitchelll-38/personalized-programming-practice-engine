from dataclasses import fields

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.content_inputs import ConceptVocabulary, ContentInputs, make_content_batch
from practice_engine.models.embedding_cache import EncoderConfig, make_entry


@pytest.fixture
def prepared():
    encoder = EncoderConfig(repository="original-synthetic/encoder", revision="a" * 40,
        tokenizer="original-synthetic/tokenizer", tokenizer_revision="b" * 40,
        pooling="mean", max_tokens=32, truncation="right", dimension=3)
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Synthetic prior", concept_ids=("loops",), correct=False,
        attempt_number=1, submitted_code="return 17;")
    row = PredictionExample(student_id="synthetic", target_sequence_index=1,
        history=(prior,), label=True, candidate=Candidate(problem_id="candidate",
            problem_text="Synthetic candidate", concept_ids=("arrays", "loops")))
    entries = {}
    for text, role, vector in [(prior.problem_text, "problem-text", [.1, .2, .3]),
        (prior.submitted_code, "historical-code", [1., 2., 3.]),
        (row.candidate.problem_text, "problem-text", [4., 5., 6.])]:
        entry = make_entry(text, role, encoder, vector)
        entries[entry.key_sha256] = entry
    return row, encoder, entries


def test_train_only_vocabulary_is_immutable_detached_and_unknown_explicit(prepared):
    row, _, _ = prepared
    vocabulary = ConceptVocabulary.fit([row])
    assert vocabulary.concepts == ("arrays", "loops") and vocabulary.size == 4
    assert vocabulary.encode("arrays") == 2 and vocabulary.encode("loops") == 3
    assert vocabulary.encode("validation-only") == 1
    payload = vocabulary.to_dict()
    assert ConceptVocabulary.from_dict(payload) == vocabulary
    payload["concepts"].append("future")
    assert vocabulary.encode("future") == 1
    assert vocabulary == ConceptVocabulary.fit([row.model_copy(update={"label": False})])
    with pytest.raises(AttributeError):
        vocabulary.concepts = ("changed",)


def test_batch_has_only_prior_outcomes_and_target_labels_are_separate(prepared):
    row, encoder, entries = prepared
    vocabulary = ConceptVocabulary.fit([row])
    batch = make_content_batch([row], vocabulary, entries, encoder)
    changed = make_content_batch([row.model_copy(update={"label": False})], vocabulary, entries, encoder)
    assert batch.labels.tolist() == [1.] and changed.labels.tolist() == [0.]
    assert batch.inputs.history_correct.tolist() == [[0]]
    assert torch.allclose(batch.inputs.history_problem[0, 0], torch.tensor([.1, .2, .3]))
    assert batch.inputs.history_code.tolist() == [[[1., 2., 3.]]]
    assert batch.inputs.candidate_problem.tolist() == [[4., 5., 6.]]
    assert batch.inputs.candidate_concepts.tolist() == [[2, 3]]
    assert not any("label" in field.name or "candidate_code" in field.name or "student_id" in field.name
                   for field in fields(ContentInputs))
    for field in fields(ContentInputs):
        left, right = getattr(batch.inputs, field.name), getattr(changed.inputs, field.name)
        assert torch.equal(left, right) and not left.requires_grad
    unseen_id = row.model_copy(update={"candidate": row.candidate.model_copy(update={"problem_id": "held-out-id"})})
    unseen = make_content_batch([unseen_id], vocabulary, entries, encoder)
    assert all(torch.equal(getattr(batch.inputs, field.name), getattr(unseen.inputs, field.name))
               for field in fields(ContentInputs))


def test_cold_start_missing_code_and_unknown_concepts_are_distinct_from_padding(prepared):
    row, encoder, entries = prepared
    vocabulary = ConceptVocabulary.fit([row])
    cold = row.model_copy(update={"history": (), "target_sequence_index": 0,
        "candidate": row.candidate.model_copy(update={"concept_ids": ("unseen",)})})
    absent = row.model_copy(update={"history": (row.history[0].model_copy(update={"submitted_code": " "}),)})
    batch = make_content_batch([cold, absent, row], vocabulary, entries, encoder)
    assert batch.inputs.lengths.tolist() == [0, 1, 1]
    assert batch.inputs.candidate_concepts[0].tolist() == [1, 0]
    assert batch.inputs.history_code_present.tolist() == [[False], [False], [True]]
    assert torch.count_nonzero(batch.inputs.history_problem[0]) == 0
    assert torch.count_nonzero(batch.inputs.history_concepts[0]) == 0
    assert torch.count_nonzero(batch.inputs.history_code[1]) == 0


def test_other_examples_future_interactions_cannot_change_existing_prefix(prepared):
    row, encoder, entries = prepared
    vocabulary = ConceptVocabulary.fit([row])
    initial = make_content_batch([row], vocabulary, entries, encoder)
    later = row.history[0].model_copy(update={"problem_id": "later", "sequence_index": 1, "correct": True})
    longer = row.model_copy(update={"history": (*row.history, later), "target_sequence_index": 2})
    extended = make_content_batch([row, longer], vocabulary, entries, encoder)
    assert extended.inputs.lengths.tolist() == [1, 2]
    assert torch.equal(initial.inputs.history_problem[0], extended.inputs.history_problem[0, :1])
    assert torch.equal(initial.inputs.history_correct[0], extended.inputs.history_correct[0, :1])
    assert torch.count_nonzero(extended.inputs.history_problem[0, 1]) == 0


@pytest.mark.parametrize("change", [{"sequence_index": 1}, {"student_id": "other"},
                                   {"attempt_number": 2}, {"problem_id": "candidate"}])
def test_future_retry_wrong_learner_and_candidate_history_rejected(prepared, change):
    row, encoder, entries = prepared
    invalid = row.model_copy(update={"history": (row.history[0].model_copy(update=change),)})
    with pytest.raises(ValueError):
        make_content_batch([invalid], ConceptVocabulary.fit([row]), entries, encoder)


def test_missing_wrong_identity_tampered_and_float32_overflow_cache_entries_fail(prepared):
    row, encoder, entries = prepared
    vocabulary = ConceptVocabulary.fit([row])
    with pytest.raises(ValueError, match="missing"):
        make_content_batch([row], vocabulary, {}, encoder)
    key = next(iter(entries))
    wrong = dict(entries)
    wrong[key] = make_entry("Other text", "problem-text", encoder, [1., 2., 3.])
    with pytest.raises(ValueError, match="identity"):
        make_content_batch([row], vocabulary, wrong, encoder)
    wrong[key] = entries[key].model_copy(update={"vector": (9., 9., 9.)})
    with pytest.raises(ValueError, match="checksum"):
        make_content_batch([row], vocabulary, wrong, encoder)
    wrong[key] = make_entry(row.history[0].problem_text, "problem-text", encoder, [1e300, 1., 2.])
    with pytest.raises(ValueError, match="float32"):
        make_content_batch([row], vocabulary, wrong, encoder)


@pytest.mark.parametrize("payload", [{"version": "future", "concepts": ["a"]},
    {"version": "content-concepts-v1", "concepts": ["a", "a"]},
    {"version": "content-concepts-v1", "concepts": ["b", "a"]},
    {"version": "content-concepts-v1", "concepts": [True]},
    {"version": "content-concepts-v1", "concepts": [], "extra": 1}])
def test_invalid_vocabulary_payloads_rejected(payload):
    with pytest.raises(ValueError):
        ConceptVocabulary.from_dict(payload)
