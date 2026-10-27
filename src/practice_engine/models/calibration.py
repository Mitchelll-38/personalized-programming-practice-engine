"""Validation-fitted grid temperature scaling with portable scalar inference."""

from dataclasses import dataclass
import math
import sys

from practice_engine.data.schema import PredictionExample

EPSILON = 1e-6
DEFAULT_TEMPERATURES = (.5, .75, 1., 1.5, 2., 3., 5.)


def _positive(value) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and 0 < value <= sys.float_info.max)


def _logits(probabilities: list[float]) -> list[float]:
    if any(isinstance(p, bool) or not isinstance(p, (int, float)) or
           not 0 <= p <= 1 or not math.isfinite(p) for p in probabilities):
        raise ValueError("Probabilities must be finite numbers in [0, 1], excluding bool")
    clipped = [min(1 - EPSILON, max(EPSILON, p)) for p in probabilities]
    return [math.log(p) - math.log1p(-p) for p in clipped]


@dataclass(frozen=True)
class TemperatureScaler:
    temperature: float

    def __post_init__(self):
        if not _positive(self.temperature):
            raise ValueError("Temperature must be positive and finite, excluding bool")

    @classmethod
    def fit_validation(cls, examples: list[PredictionExample], probabilities: list[float],
                       *, temperatures=DEFAULT_TEMPERATURES) -> "TemperatureScaler":
        """Choose fixed-grid temperature by validation log loss; caller owns split.

        This simplified scalar calibrator has no bias. It cannot establish
        calibration quality on its fitting partition or authenticate provenance.
        """
        if not examples or len(examples) != len(probabilities):
            raise ValueError("Validation examples must be nonempty and aligned")
        for row in examples:
            if (type(row) is not PredictionExample or type(row.label) is not bool
                    or type(row.student_id) is not str or not row.student_id.strip()):
                raise ValueError("Valid prediction examples with student IDs are required")
            # Frozen models can still be copied with unvalidated nested updates.
            PredictionExample.model_validate(row.model_dump(warnings=False))
        if len({e.label for e in examples}) != 2:
            raise ValueError("Temperature fitting requires both validation classes")
        grid = tuple(temperatures)
        if not grid or any(not _positive(t) for t in grid) or len(set(grid)) != len(grid):
            raise ValueError("Temperature grid must contain unique positive finite values")
        logits = _logits(probabilities)
        def objective(temperature):
            scaled = [z / temperature for z in logits]
            signed = [-z if e.label else z for e, z in zip(examples, scaled)]
            return math.fsum((max(z, 0) + math.log1p(math.exp(-abs(z)))) / len(examples)
                             for z in signed)
        # Prefer identity on a tie, then the smaller temperature; grid order is irrelevant.
        best = min(grid, key=lambda t: (objective(t), abs(math.log(t)), t))
        if not math.isfinite(objective(best)):
            raise ValueError("Temperature grid has no finite fitting objective")
        return cls(float(best))

    def predict(self, probabilities: list[float]) -> list[float]:
        output = []
        for logit in _logits(probabilities):
            scaled = logit / self.temperature
            if scaled >= 0:
                output.append(1 / (1 + math.exp(-scaled)))
            else:
                exponential = math.exp(scaled)
                output.append(exponential / (1 + exponential))
        return output

    def to_dict(self) -> dict:
        return {"version": "temperature-scaling-v1", "temperature": self.temperature,
                "epsilon": EPSILON, "fit_partition": "validation"}

    @classmethod
    def from_dict(cls, payload: dict) -> "TemperatureScaler":
        if (not isinstance(payload, dict) or set(payload) !=
                {"version", "temperature", "epsilon", "fit_partition"} or
                payload.get("version") != "temperature-scaling-v1" or
                type(payload.get("epsilon")) is not float or payload["epsilon"] != EPSILON or
                payload.get("fit_partition") != "validation"):
            raise ValueError("Unsupported temperature scaler payload")
        return cls(payload["temperature"])
