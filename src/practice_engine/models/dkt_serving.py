"""Optional label-free inference for already-loaded strict CPU DKT checkpoints."""

from .dkt_artifacts import DKTCheckpoint
from .serving import PredictionInput, PredictionScore


def predict_dkt_inputs(checkpoint: DKTCheckpoint,
                       inputs: list[PredictionInput]) -> list[PredictionScore]:
    if not isinstance(checkpoint, DKTCheckpoint):
        raise ValueError("A reviewed DKTCheckpoint is required")
    if any(not isinstance(row, PredictionInput) for row in inputs):
        raise ValueError("Queries must be PredictionInput objects")
    queries = [PredictionInput.model_validate(row.model_dump()) for row in inputs]
    # The legacy model interface consumes a fixed internal label sentinel, never
    # a request label; forward inputs retain only the observed prefix/candidate.
    probabilities = checkpoint.predict([row._example() for row in queries])
    if len(probabilities) != len(queries):
        raise ValueError("Checkpoint returned a misaligned prediction batch")
    return [PredictionScore(problem_id=row.candidate.problem_id, predicted_correctness=p)
            for row, p in zip(queries, probabilities)]
