"""Train-only correctness rates with symmetric Beta(alpha, alpha) smoothing."""

from collections import defaultdict
import math

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from practice_engine.data.schema import PredictionExample
from .features import validate_training_examples


class _Counts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    total: StrictInt = Field(ge=1)
    correct: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def valid_successes(self):
        if self.correct > self.total:
            raise ValueError("correct count cannot exceed total")
        return self


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    alpha: float
    global_counts: _Counts
    problem_counts: dict[str, _Counts]

    @model_validator(mode="after")
    def valid_parameters(self):
        _validate_alpha(self.alpha)
        if not self.problem_counts or any(not key.strip() for key in self.problem_counts):
            raise ValueError("problem counts require nonempty problem IDs")
        if sum(c.total for c in self.problem_counts.values()) != self.global_counts.total:
            raise ValueError("problem totals must match global total")
        if sum(c.correct for c in self.problem_counts.values()) != self.global_counts.correct:
            raise ValueError("problem correct counts must match global correct count")
        return self


def _validate_alpha(alpha: float) -> None:
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
        raise ValueError("alpha must be a positive finite number")
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be a positive finite number")


def _rate(counts: _Counts, alpha: float) -> float:
    # Scale before adding so even a very large finite alpha cannot overflow.
    scale = max(counts.total, alpha)
    return (counts.correct / scale + alpha / scale) / (
        counts.total / scale + 2 * (alpha / scale)
    )


class RateBaseline:
    """Fitted global/problem rates. No histories or target metadata are consumed.

    Callers supply the training partition to ``fit``. This model cannot infer
    partition membership; validation/test labels must never be passed to it.
    Predictions are uncalibrated correctness probabilities, not mastery claims.
    """

    def __init__(self, payload: _Payload):
        self._payload = payload

    @classmethod
    def fit(cls, examples: list[PredictionExample], alpha: float = 1.0) -> "RateBaseline":
        _validate_alpha(alpha)
        if not examples:
            raise ValueError("training examples must be nonempty")
        validate_training_examples(examples)
        counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for example in examples:
            problem_id = example.candidate.problem_id
            if not problem_id.strip():
                raise ValueError("training problem IDs must be nonempty")
            counts[problem_id][0] += 1
            counts[problem_id][1] += int(example.label)
        return cls.from_dict({
            "alpha": float(alpha),
            "global_counts": {"total": len(examples), "correct": sum(e.label for e in examples)},
            "problem_counts": {
                key: {"total": total, "correct": correct}
                for key, (total, correct) in sorted(counts.items())
            },
        })

    def predict(self, examples: list[PredictionExample], per_problem: bool = True) -> list[float]:
        """Unknown exercises use the global rate; prediction labels are ignored."""
        if not isinstance(per_problem, bool):
            raise ValueError("per_problem must be a boolean")
        return [
            _rate(
                self._payload.problem_counts.get(e.candidate.problem_id, self._payload.global_counts)
                if per_problem else self._payload.global_counts,
                self._payload.alpha,
            )
            for e in examples
        ]

    def to_dict(self) -> dict:
        """Return detached JSON data with deterministic problem ordering."""
        payload = self._payload.model_dump()
        payload["problem_counts"] = dict(sorted(payload["problem_counts"].items()))
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "RateBaseline":
        """Strictly validate counts and reject unknown fields before loading."""
        return cls(_Payload.model_validate(payload))
