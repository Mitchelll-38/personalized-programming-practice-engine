"""Causal frozen content vectors and training-only concept IDs, without a model."""

from bisect import bisect_left
from dataclasses import dataclass
from collections.abc import Mapping

import torch

from practice_engine.data.schema import PredictionExample
from .embedding_cache import EmbeddingEntry, EncoderConfig, cache_key
from .serving import PredictionInput

PAD, UNK = 0, 1


def _validated(examples):
    if (not isinstance(examples, (list, tuple)) or not examples
            or any(not isinstance(row, PredictionExample) for row in examples)):
        raise ValueError("Content batches require nonempty PredictionExample objects")
    rows = [PredictionExample.model_validate(row.model_dump()) for row in examples]
    queries = [PredictionInput.model_validate({k: v for k, v in row.model_dump().items() if k != "label"})
               for row in rows]
    return rows, queries


@dataclass(frozen=True)
class ConceptVocabulary:
    concepts: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.concepts, tuple) or not self.concepts
                or any(not isinstance(tag, str) or not tag.strip() for tag in self.concepts)
                or tuple(sorted(set(self.concepts))) != self.concepts):
            raise ValueError("Concept vocabulary requires sorted unique nonempty strings")

    @classmethod
    def fit(cls, train_examples):
        _, queries = _validated(train_examples)
        names = {tag for query in queries for tag in query.candidate.concept_ids}
        names.update(tag for query in queries for row in query.history for tag in row.concept_ids)
        return cls(tuple(sorted(names)))

    @property
    def size(self):
        return len(self.concepts) + 2

    def encode(self, concept):
        if not isinstance(concept, str) or not concept.strip():
            raise ValueError("Concept tags must be nonempty strings")
        index = bisect_left(self.concepts, concept)
        return index + 2 if index < len(self.concepts) and self.concepts[index] == concept else UNK

    def to_dict(self):
        return {"version": "content-concepts-v1", "concepts": list(self.concepts)}

    @classmethod
    def from_dict(cls, payload):
        if (not isinstance(payload, dict) or set(payload) != {"version", "concepts"}
                or payload["version"] != "content-concepts-v1" or not isinstance(payload["concepts"], list)):
            raise ValueError("Unsupported content concept vocabulary")
        return cls(tuple(payload["concepts"]))


@dataclass(frozen=True)
class ContentInputs:
    history_problem: torch.Tensor
    history_code: torch.Tensor
    history_code_present: torch.Tensor
    history_concepts: torch.Tensor
    history_correct: torch.Tensor
    lengths: torch.Tensor
    candidate_problem: torch.Tensor
    candidate_concepts: torch.Tensor


@dataclass(frozen=True)
class ContentBatch:
    inputs: ContentInputs
    labels: torch.Tensor


def make_content_batch(examples, vocabulary: ConceptVocabulary,
                       entries: Mapping[str, EmbeddingEntry], encoder: EncoderConfig) -> ContentBatch:
    rows, queries = _validated(examples)
    if not isinstance(vocabulary, ConceptVocabulary) or not isinstance(encoder, EncoderConfig):
        raise ValueError("Content vocabulary and encoder configuration are required")
    ConceptVocabulary(vocabulary.concepts)
    encoder = EncoderConfig.model_validate(encoder.model_dump())
    if not isinstance(entries, Mapping):
        raise ValueError("Frozen entries must be supplied as a key mapping")
    validated = {}
    def vector(text, role):
        key = cache_key(text, role, encoder)
        if key not in validated:
            entry = entries.get(key)
            if not isinstance(entry, EmbeddingEntry):
                raise ValueError("Required frozen content embedding is missing")
            entry = EmbeddingEntry.model_validate(entry.to_dict())
            if entry.key_sha256 != key or entry.encoder != encoder:
                raise ValueError("Frozen content embedding differs from its requested identity")
            values = torch.tensor(entry.vector, dtype=torch.float32)
            if not torch.isfinite(values).all():
                raise ValueError("Frozen vector cannot be represented by finite float32 values")
            validated[key] = values
        return validated[key]
    count = len(queries)
    lengths = torch.tensor([len(query.history) for query in queries], dtype=torch.long)
    width = max(1, int(lengths.max()))
    tags = max(len(item.concept_ids) for query in queries for item in (*query.history, query.candidate))
    problem = torch.zeros((count, width, encoder.dimension), dtype=torch.float32)
    code = torch.zeros_like(problem)
    present = torch.zeros((count, width), dtype=torch.bool)
    concepts = torch.zeros((count, width, tags), dtype=torch.long)
    correct = torch.zeros((count, width), dtype=torch.long)
    candidates = torch.zeros((count, encoder.dimension), dtype=torch.float32)
    candidate_concepts = torch.zeros((count, tags), dtype=torch.long)
    for index, query in enumerate(queries):
        candidates[index] = vector(query.candidate.problem_text, "problem-text")
        ids = [vocabulary.encode(tag) for tag in query.candidate.concept_ids]
        candidate_concepts[index, :len(ids)] = torch.tensor(ids)
        for position, row in enumerate(query.history):
            problem[index, position] = vector(row.problem_text, "problem-text")
            if row.submitted_code is not None and row.submitted_code.strip():
                code[index, position] = vector(row.submitted_code, "historical-code")
                present[index, position] = True
            ids = [vocabulary.encode(tag) for tag in row.concept_ids]
            concepts[index, position, :len(ids)] = torch.tensor(ids)
            correct[index, position] = int(row.correct)
    inputs = ContentInputs(problem, code, present, concepts, correct, lengths, candidates, candidate_concepts)
    return ContentBatch(inputs, torch.tensor([float(row.label) for row in rows], dtype=torch.float32))
