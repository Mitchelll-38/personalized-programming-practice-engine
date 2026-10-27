"""Label-free baseline inference inputs, separate from evaluation examples."""

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator

from practice_engine.data.schema import Candidate, Interaction, PredictionExample

from .artifacts import RateArtifact
from .calibrated_artifacts import CalibratedBaselineArtifact
from .features import historical_features
from .portable import PortableBaselineArtifact


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    student_id: str = Field(min_length=1, pattern=r"\S")
    target_sequence_index: StrictInt = Field(ge=0)
    history: tuple[Interaction, ...]
    candidate: Candidate

    @model_validator(mode="after")
    def valid_query(self):
        candidate = self.candidate
        if (not candidate.problem_id.strip() or not candidate.problem_text.strip() or
                not candidate.concept_ids or any(not c.strip() for c in candidate.concept_ids) or
                len(set(candidate.concept_ids)) != len(candidate.concept_ids)):
            raise ValueError("Candidate requires nonempty ID, statement and distinct concepts")
        historical_features([self._example()])
        return self

    def _example(self) -> PredictionExample:
        # Existing model interfaces consume PredictionExample but never its label
        # at inference. A fixed internal sentinel cannot come from client input.
        return PredictionExample(student_id=self.student_id,
            target_sequence_index=self.target_sequence_index, history=self.history,
            candidate=self.candidate, label=False)


class PredictionScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_id: str = Field(min_length=1)
    predicted_correctness: StrictFloat = Field(ge=0, le=1, allow_inf_nan=False)


def predict_inputs(artifact: RateArtifact | PortableBaselineArtifact | CalibratedBaselineArtifact,
                   inputs: list[PredictionInput] | tuple[PredictionInput, ...]) -> list[PredictionScore]:
    """Preserve query order and revalidate causal boundaries before prediction.

    Supported artifacts recheck their payload integrity during prediction. This
    adapter does not fit a model, expose target labels or activate an API model.
    """
    if not isinstance(artifact, (RateArtifact, PortableBaselineArtifact, CalibratedBaselineArtifact)):
        raise ValueError("Only reviewed portable baseline artifacts are supported")
    if not isinstance(inputs, (list, tuple)) or any(not isinstance(row, PredictionInput) for row in inputs):
        raise ValueError("Queries must be a list or tuple of PredictionInput objects")
    # Recheck direct model_copy updates and mutable nested objects at the boundary.
    queries = [PredictionInput.model_validate(row.model_dump()) for row in inputs]
    probabilities = artifact.predict([row._example() for row in queries])
    if len(probabilities) != len(queries):
        raise ValueError("Model returned a misaligned prediction batch")
    return [PredictionScore(problem_id=row.candidate.problem_id, predicted_correctness=p)
            for row, p in zip(queries, probabilities)]
