"""ID-only DKT: causal histories in, candidate correctness logits out."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

from practice_engine.data.schema import PredictionExample
from practice_engine.models.features import historical_features

PAD, UNK = 0, 1


class _VocabularyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: str
    problem_ids: dict[str, StrictInt]

    @model_validator(mode="after")
    def valid_ids(self):
        if self.version != "dkt-exercise-v1":
            raise ValueError("unsupported DKT vocabulary version")
        if not self.problem_ids or any(not key.strip() for key in self.problem_ids):
            raise ValueError("vocabulary requires nonempty exercise IDs")
        if sorted(self.problem_ids.values()) != list(range(2, len(self.problem_ids) + 2)):
            raise ValueError("exercise IDs must be unique and contiguous from 2")
        return self


class ExerciseVocabulary:
    """Training-only IDs. Callers, not this class, determine partition membership."""

    def __init__(self, payload: _VocabularyPayload):
        self._payload = payload

    @classmethod
    def fit(cls, train_examples: list[PredictionExample]) -> "ExerciseVocabulary":
        if not train_examples:
            raise ValueError("training examples must be nonempty")
        historical_features(train_examples)  # Reuse canonical causal validation.
        names = {example.candidate.problem_id for example in train_examples}
        names.update(row.problem_id for example in train_examples for row in example.history)
        return cls.from_dict({"version": "dkt-exercise-v1", "problem_ids": {
            name: index for index, name in enumerate(sorted(names), 2)
        }})

    @property
    def size(self) -> int:
        return len(self._payload.problem_ids) + 2

    def encode(self, problem_id: str) -> int:
        return self._payload.problem_ids.get(problem_id, UNK)

    def to_dict(self) -> dict:
        return self._payload.model_dump()

    @classmethod
    def from_dict(cls, payload: dict) -> "ExerciseVocabulary":
        return cls(_VocabularyPayload.model_validate(payload))


@dataclass(frozen=True)
class DKTInputs:
    history_ids: torch.Tensor
    history_correct: torch.Tensor
    lengths: torch.Tensor
    candidate_ids: torch.Tensor


@dataclass(frozen=True)
class DKTBatch:
    inputs: DKTInputs
    labels: torch.Tensor


def make_batch(examples: list[PredictionExample], vocabulary: ExerciseVocabulary) -> DKTBatch:
    """Right-pad validated prefixes; target labels are kept outside forward inputs."""
    if not examples:
        raise ValueError("batch must be nonempty")
    historical_features(examples)
    lengths = torch.tensor([len(example.history) for example in examples], dtype=torch.long)
    width = max(1, int(lengths.max()))
    ids = torch.zeros((len(examples), width), dtype=torch.long)
    correct = torch.zeros_like(ids)
    for index, example in enumerate(examples):
        count = len(example.history)
        ids[index, :count] = torch.tensor([vocabulary.encode(row.problem_id) for row in example.history], dtype=torch.long)
        correct[index, :count] = torch.tensor([int(row.correct) for row in example.history], dtype=torch.long)
    inputs = DKTInputs(ids, correct, lengths, torch.tensor([
        vocabulary.encode(example.candidate.problem_id) for example in examples
    ], dtype=torch.long))
    return DKTBatch(inputs, torch.tensor([float(example.label) for example in examples]))


class DKT(nn.Module):
    """Single-layer LSTM with per-exercise heads; no persistent learner state."""

    def __init__(self, vocabulary_size: int, embedding_size: int = 16, hidden_size: int = 32):
        super().__init__()
        if any(type(value) is not int or value < minimum for value, minimum in (
            (vocabulary_size, 3), (embedding_size, 1), (hidden_size, 1),
        )):
            raise ValueError("vocabulary must include PAD/UNK/known IDs; dimensions must be positive integers")
        self.embedding = nn.Embedding(2 * vocabulary_size, embedding_size, padding_idx=PAD)
        self.lstm = nn.LSTM(embedding_size, hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size, vocabulary_size)

    def forward(self, inputs: DKTInputs) -> torch.Tensor:
        ids, correct, lengths, candidates = (
            inputs.history_ids, inputs.history_correct, inputs.lengths, inputs.candidate_ids,
        )
        if any(tensor.dtype != torch.long for tensor in (ids, correct, lengths, candidates)):
            raise ValueError("DKT inputs must be integer tensors")
        if ids.ndim != 2 or correct.shape != ids.shape or ids.shape[0] == 0 or ids.shape[1] == 0:
            raise ValueError("history tensors must share a nonempty batch/time shape")
        if lengths.shape != (ids.shape[0],) or candidates.shape != lengths.shape:
            raise ValueError("lengths and candidates must match batch size")
        if any(tensor.device != ids.device for tensor in (correct, lengths, candidates)):
            raise ValueError("DKT inputs must share a device")
        if torch.any((lengths < 0) | (lengths > ids.shape[1])):
            raise ValueError("history lengths must fit padded width")
        if torch.any((candidates < UNK) | (candidates >= self.head.out_features)):
            raise ValueError("candidate IDs must be known or UNK")
        observed = torch.arange(ids.shape[1], device=ids.device)[None, :] < lengths[:, None]
        if torch.any(observed & ((ids < UNK) | (ids >= self.head.out_features) | (correct < 0) | (correct > 1))):
            raise ValueError("observed history requires valid IDs and binary outcomes")
        # Mask before embedding as padded values must never be observed or indexed.
        pairs = torch.where(observed, ids * 2 + correct, PAD)
        hidden = self.head.weight.new_zeros((ids.shape[0], self.lstm.hidden_size))
        active = (lengths > 0).nonzero(as_tuple=True)[0]
        if active.numel():
            packed = pack_padded_sequence(self.embedding(pairs[active]), lengths[active].cpu(),
                                          batch_first=True, enforce_sorted=False)
            _, (last, _) = self.lstm(packed)
            hidden = hidden.index_copy(0, active, last[-1])
        return self.head(hidden).gather(1, candidates[:, None]).squeeze(1)
