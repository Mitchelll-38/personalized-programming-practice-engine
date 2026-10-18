"""Optional label-free content inference from loaded checkpoints and supplied entries."""

from collections.abc import Mapping

import torch

from .content_artifacts import ContentCheckpoint
from .content_inputs import ConceptVocabulary, make_content_batch
from .serving import PredictionInput, PredictionScore


def predict_content_inputs(checkpoint: ContentCheckpoint, inputs: list[PredictionInput],
                           entries: Mapping, *, batch_size: int = 32) -> list[PredictionScore]:
    if not isinstance(checkpoint, ContentCheckpoint):
        raise ValueError("A loaded ContentCheckpoint is required")
    if not isinstance(inputs, (list, tuple)) or any(not isinstance(row, PredictionInput) for row in inputs):
        raise ValueError("Queries must be a sequence of PredictionInput objects")
    if not isinstance(entries, Mapping):
        raise ValueError("Supplied frozen entries must be a mapping")
    if type(batch_size) is not int or not 1 <= batch_size <= 256:
        raise ValueError("batch_size must be an integer in [1,256]")
    queries = [PredictionInput.model_validate(row.model_dump()) for row in inputs]
    checkpoint.validate_integrity()  # Also required for an empty query batch.
    vocabulary = ConceptVocabulary.from_dict(checkpoint.metadata.vocabulary)
    encoder = checkpoint.metadata.encoder
    scores = []
    with torch.device("cpu"), torch.inference_mode():
        for start in range(0, len(queries), batch_size):
            group = queries[start:start + batch_size]
            # Only the batch producer's legacy example carries a fixed False
            # sentinel. Labels never enter ContentInputs or checkpoint inference.
            batch = make_content_batch([row._example() for row in group], vocabulary, entries, encoder)
            logits = checkpoint.logits(batch.inputs)
            if (not isinstance(logits, torch.Tensor) or logits.device.type != "cpu"
                    or logits.dtype != torch.float32 or logits.shape != (len(group),)
                    or not torch.isfinite(logits).all()):
                raise ValueError("Checkpoint returned invalid/misaligned logits")
            scores.extend(PredictionScore(problem_id=row.candidate.problem_id, predicted_correctness=probability)
                          for row, probability in zip(group, torch.sigmoid(logits).tolist()))
    return scores
