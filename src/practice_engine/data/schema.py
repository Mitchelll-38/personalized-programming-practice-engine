"""Strict canonical schema. Target responses never belong to candidate inputs."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


class Interaction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    student_id: str = Field(min_length=1)
    problem_id: str = Field(min_length=1)
    sequence_index: StrictInt = Field(ge=0)
    problem_text: str = Field(min_length=1)
    concept_ids: tuple[str, ...] = Field(min_length=1)
    correct: StrictBool
    attempt_number: StrictInt = Field(ge=1)
    submitted_code: str | None = None

    @model_validator(mode="after")
    def valid_concepts(self):
        if any(not tag.strip() for tag in self.concept_ids):
            raise ValueError("concept IDs must be nonempty")
        if len(set(self.concept_ids)) != len(self.concept_ids):
            raise ValueError("concept IDs must be unique")
        return self


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    problem_id: str
    problem_text: str
    concept_ids: tuple[str, ...]


class PredictionExample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    student_id: str
    target_sequence_index: int
    history: tuple[Interaction, ...]
    candidate: Candidate
    label: StrictBool
