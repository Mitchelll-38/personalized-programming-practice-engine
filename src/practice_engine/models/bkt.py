"""Shared-parameter, conditional grid-likelihood Bayesian Knowledge Tracing."""

from itertools import product
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from practice_engine.data.schema import PredictionExample
from .features import historical_features, validate_training_examples


class _Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    initial: float = Field(ge=0, le=1, allow_inf_nan=False)
    learn: float = Field(ge=0, le=1, allow_inf_nan=False)
    guess: float = Field(gt=0, lt=1, allow_inf_nan=False)
    slip: float = Field(gt=0, lt=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def informative_observation(self):
        if self.guess + self.slip >= 1:
            raise ValueError("guess + slip must be less than 1")
        return self


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: Literal["shared-bkt-v1"]
    parameters: _Parameters


def _validate_examples(examples: list[PredictionExample]) -> None:
    historical_features(examples)  # Reuse the established causal/first-attempt checks.
    if any(not e.candidate.concept_ids or any(not c.strip() for c in e.candidate.concept_ids)
           for e in examples):
        raise ValueError("Candidates require nonempty concept IDs")


def _predict_one(example: PredictionExample, parameters: _Parameters) -> float:
    posterior: dict[str, float] = {}
    for observation in example.history:
        for concept in observation.concept_ids:
            prior = posterior.get(concept, parameters.initial)
            if observation.correct:
                numerator = prior * (1 - parameters.slip)
                denominator = numerator + (1 - prior) * parameters.guess
            else:
                numerator = prior * parameters.slip
                denominator = numerator + (1 - prior) * (1 - parameters.guess)
            updated = numerator / denominator
            posterior[concept] = updated + (1 - updated) * parameters.learn
    concepts = sorted(set(example.candidate.concept_ids))
    return math.fsum(
        posterior.get(c, parameters.initial) * (1 - parameters.slip)
        + (1 - posterior.get(c, parameters.initial)) * parameters.guess
        for c in concepts
    ) / len(concepts)


class BKTBaseline:
    """One parameter set shared across concepts; no forgetting or fitted vocabulary.

    Multi-concept observations update each tagged concept independently. Candidate
    success averages its concept probabilities. These are predictive assumptions,
    not measured mastery or a claim of improved learning.
    """

    def __init__(self, payload: _Payload):
        self._payload = payload

    @classmethod
    def fit(cls, examples: list[PredictionExample], parameter_grid: list[dict] | None = None) -> "BKTBaseline":
        """Choose conditional maximum likelihood on supplied training examples only."""
        if not examples:
            raise ValueError("Training examples must be nonempty")
        validate_training_examples(examples)
        _validate_examples(examples)
        if parameter_grid is None:
            parameter_grid = [dict(zip(("initial", "learn", "guess", "slip"), values))
                              for values in product((0.2, 0.5), (0.0, 0.1, 0.2), (0.1, 0.2), (0.1, 0.2))]
        if not isinstance(parameter_grid, list) or not parameter_grid:
            raise ValueError("Parameter grid must be a nonempty list of parameter dictionaries")
        configurations = [_Parameters.model_validate(config) for config in parameter_grid]
        configurations.sort(key=lambda p: (p.initial, p.learn, p.guess, p.slip))

        def loss(parameters):
            terms = []
            for example in examples:
                p = min(1 - 1e-15, max(1e-15, _predict_one(example, parameters)))
                terms.append(-math.log(p) if example.label else -math.log1p(-p))
            return math.fsum(terms) / len(examples)

        selected = min(configurations, key=loss)
        return cls.from_dict({"version": "shared-bkt-v1", "parameters": selected.model_dump()})

    def predict(self, examples: list[PredictionExample]) -> list[float]:
        """Use permitted prior observations and candidate concepts; ignore target labels."""
        _validate_examples(examples)
        return [_predict_one(e, self._payload.parameters) for e in examples]

    def to_dict(self) -> dict:
        return self._payload.model_dump()

    @classmethod
    def from_dict(cls, payload: dict) -> "BKTBaseline":
        return cls(_Payload.model_validate(payload))
