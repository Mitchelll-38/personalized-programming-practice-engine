from dataclasses import fields, replace

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction, PredictionExample
from practice_engine.models.content_inputs import ConceptVocabulary, make_content_batch
from practice_engine.models.content_lstm import ContentLSTM
from practice_engine.models.embedding_cache import EncoderConfig, make_entry


@pytest.fixture
def prepared():
    encoder = EncoderConfig(repository="synthetic/encoder", revision="a" * 40,
        tokenizer="synthetic/tokenizer", tokenizer_revision="b" * 40, pooling="mean",
        max_tokens=32, truncation="right", dimension=3)
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
        problem_text="Prior", concept_ids=("loops",), correct=False, attempt_number=1, submitted_code="return 1;")
    row = PredictionExample(student_id="synthetic", target_sequence_index=1, history=(prior,), label=True,
        candidate=Candidate(problem_id="next", problem_text="Next", concept_ids=("arrays", "loops")))
    entries = {}
    for text, role, vector in [("Prior", "problem-text", [1., 2., 3.]),
        ("Next", "problem-text", [3., 2., 1.]), ("return 1;", "historical-code", [.2, .3, .4])]:
        entry = make_entry(text, role, encoder, vector)
        entries[entry.key_sha256] = entry
    vocabulary = ConceptVocabulary.fit([row])
    cold = row.model_copy(update={"history": (), "target_sequence_index": 0})
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(7)
        model = ContentLSTM(vocabulary.size, input_size=3, projection_size=4,
                            concept_size=3, correctness_size=2, hidden_size=5)
    batch = make_content_batch([row, cold], vocabulary, entries, encoder)
    return model, batch


def test_forward_is_batch_isolated_finite_and_excludes_target_labels(prepared):
    model, batch = prepared
    output = model(batch.inputs)
    assert output.shape == (2,) and torch.isfinite(output).all()
    assert torch.allclose(model(replace(batch.inputs, **{
        field.name: getattr(batch.inputs, field.name)[:1] for field in fields(batch.inputs)})), output[:1], atol=1e-6)
    batch.labels.logical_not_()
    assert torch.equal(output, model(batch.inputs))
    with pytest.raises(ValueError, match="labels"):
        model(batch)


def test_arbitrary_padding_and_missing_code_values_do_not_change_logits(prepared):
    model, batch = prepared
    original = model(batch.inputs)
    def extend(tensor, value):
        padding = tensor.new_full((tensor.shape[0], 2, *tensor.shape[2:]), value)
        return torch.cat((tensor, padding), dim=1)
    padded = replace(batch.inputs,
        history_problem=extend(batch.inputs.history_problem, float("nan")),
        history_code=extend(batch.inputs.history_code, float("nan")),
        history_code_present=extend(batch.inputs.history_code_present, True),
        history_concepts=extend(batch.inputs.history_concepts, -999),
        history_correct=extend(batch.inputs.history_correct, -999))
    assert torch.allclose(model(padded), original, atol=1e-6)
    missing = replace(batch.inputs, history_code_present=torch.zeros_like(batch.inputs.history_code_present))
    poisoned = replace(missing, history_code=torch.full_like(missing.history_code, float("nan")))
    assert torch.equal(model(missing), model(poisoned))


def test_unknown_concepts_contribute_zero_and_cold_state_is_zero(prepared):
    model, batch = prepared
    with torch.no_grad():
        model.concepts.weight[0].fill_(99)
        model.concepts.weight[1].fill_(88)
    assert torch.count_nonzero(model._concept_mean(torch.tensor([[0, 1]]))) == 0
    assert torch.equal(model._concept_mean(torch.tensor([[2, 0]])), model._concept_mean(torch.tensor([[2, 1]])))
    output = model(batch.inputs)
    candidate = model.problem(batch.inputs.candidate_problem[1:2])
    concepts = model._concept_mean(batch.inputs.candidate_concepts[1:2])
    expected = model.head(torch.cat((torch.zeros((1, model.lstm.hidden_size)), candidate, concepts), -1)).squeeze(-1)
    assert torch.allclose(output[1:], expected, atol=1e-6)
    unknown = replace(batch.inputs, candidate_concepts=torch.ones_like(batch.inputs.candidate_concepts))
    assert torch.isfinite(model(unknown)).all()


def test_candidate_content_conditions_output_and_frozen_vectors_have_no_gradients(prepared):
    model, batch = prepared
    changed = replace(batch.inputs, candidate_problem=batch.inputs.candidate_problem + 2)
    assert not torch.allclose(model(batch.inputs), model(changed))
    inputs = replace(batch.inputs, history_problem=batch.inputs.history_problem.clone().requires_grad_(),
        history_code=batch.inputs.history_code.clone().requires_grad_(),
        candidate_problem=batch.inputs.candidate_problem.clone().requires_grad_())
    loss = torch.nn.functional.binary_cross_entropy_with_logits(model(inputs), batch.labels)
    loss.backward()
    assert all(getattr(inputs, field).grad is None for field in ("history_problem", "history_code", "candidate_problem"))
    for layer in (model.problem, model.code, model.concepts, model.correctness, model.lstm, model.head):
        assert any(parameter.grad is not None and torch.isfinite(parameter.grad).all()
                   and torch.count_nonzero(parameter.grad) > 0 for parameter in layer.parameters())
    assert torch.count_nonzero(model.concepts.weight.grad[:2]) == 0


@pytest.mark.parametrize("change", [
    lambda x: replace(x, lengths=torch.tensor([-1, 0])),
    lambda x: replace(x, lengths=torch.tensor([2, 0])),
    lambda x: replace(x, history_correct=torch.tensor([[2], [0]])),
    lambda x: replace(x, history_concepts=torch.full_like(x.history_concepts, 999)),
    lambda x: replace(x, candidate_concepts=torch.zeros_like(x.candidate_concepts)),
    lambda x: replace(x, candidate_problem=torch.full_like(x.candidate_problem, float("nan"))),
    lambda x: replace(x, history_problem=torch.full_like(x.history_problem, float("nan"))),
    lambda x: replace(x, history_code=torch.full_like(x.history_code, float("inf"))),
    lambda x: replace(x, history_code_present=x.history_code_present.long()),
    lambda x: replace(x, history_problem=x.history_problem.double()),
    lambda x: replace(x, candidate_problem=x.candidate_problem[:, :2]),
])
def test_invalid_observed_features_fail_before_indexing(prepared, change):
    model, batch = prepared
    with pytest.raises(ValueError):
        model(change(batch.inputs))


@pytest.mark.parametrize("configuration", [{"concept_vocabulary_size": 2}, {"input_size": 0},
    {"projection_size": True}, {"hidden_size": 0}, {"concept_size": -1}])
def test_invalid_dimensions_rejected(configuration):
    with pytest.raises(ValueError):
        ContentLSTM(**{"concept_vocabulary_size": 4, **configuration})
