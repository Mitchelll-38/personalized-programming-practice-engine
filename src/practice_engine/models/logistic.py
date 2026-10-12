"""Train-only standardized logistic regression with portable JSON inference."""

import math
import warnings

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from practice_engine.data.schema import PredictionExample
from .features import FEATURE_NAMES, FEATURE_VERSION, historical_features


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    feature_version: str
    feature_names: list[str]
    means: list[float]
    scales: list[float]
    coefficients: list[float]
    intercept: float
    C: float = Field(gt=0)
    max_iter: StrictInt = Field(gt=0)
    seed: StrictInt = Field(ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def valid_parameters(self):
        if self.feature_version != FEATURE_VERSION or self.feature_names != list(FEATURE_NAMES):
            raise ValueError("unsupported feature contract")
        vectors = (self.means, self.scales, self.coefficients)
        if any(len(v) != len(FEATURE_NAMES) for v in vectors):
            raise ValueError("parameter dimensions must match features")
        if any(not math.isfinite(x) for v in vectors for x in v):
            raise ValueError("parameters must be finite")
        if not math.isfinite(self.intercept) or not math.isfinite(self.C):
            raise ValueError("parameters must be finite")
        if any(scale <= 0 for scale in self.scales):
            raise ValueError("scales must be positive")
        return self


class LogisticBaseline:
    """Interpretable historical features, fitted solely on supplied training data.

    Scaling and regression never see validation/test examples unless the caller
    incorrectly supplies them to fit. Outputs are uncalibrated p(correct).
    JSON inference avoids pickle and requires no scikit-learn import.
    """

    def __init__(self, payload: _Payload):
        self._payload = payload

    @classmethod
    def fit(cls, examples: list[PredictionExample], C: float = 1.0,
            max_iter: int = 1000, seed: int = 38) -> "LogisticBaseline":
        if isinstance(C, bool) or not isinstance(C, (int, float)) or not math.isfinite(C) or C <= 0:
            raise ValueError("C must be a positive finite number")
        if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter <= 0:
            raise ValueError("max_iter must be a positive integer")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
            raise ValueError("seed must be an integer in [0, 2**32)")
        if not examples or len({e.label for e in examples}) != 2:
            raise ValueError("training examples must contain both outcome classes")
        # Import optional training dependencies only when fitting.
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler()
        features = scaler.fit_transform(historical_features(examples))
        model = LogisticRegression(C=C, max_iter=max_iter, random_state=seed,
                                   tol=1e-8, solver="lbfgs")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(features, [int(e.label) for e in examples])
        except ConvergenceWarning as error:
            raise ValueError("logistic training did not converge; increase max_iter") from error
        return cls.from_dict({
            "feature_version": FEATURE_VERSION, "feature_names": list(FEATURE_NAMES),
            "means": scaler.mean_.tolist(), "scales": scaler.scale_.tolist(),
            "coefficients": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
            "C": float(C), "max_iter": max_iter, "seed": seed,
        })

    def predict(self, examples: list[PredictionExample]) -> list[float]:
        probabilities = []
        for features in historical_features(examples):
            score = self._payload.intercept + sum(
                coefficient * ((value - mean) / scale)
                for value, mean, scale, coefficient in zip(
                    features, self._payload.means, self._payload.scales, self._payload.coefficients,
                )
            )
            if not math.isfinite(score):
                raise ValueError("nonfinite prediction score from saved parameters")
            if score >= 0:
                probabilities.append(1 / (1 + math.exp(-score)))
            else:
                exponential = math.exp(score)
                probabilities.append(exponential / (1 + exponential))
        return probabilities

    def to_dict(self) -> dict:
        return self._payload.model_dump()

    @classmethod
    def from_dict(cls, payload: dict) -> "LogisticBaseline":
        return cls(_Payload.model_validate(payload))
