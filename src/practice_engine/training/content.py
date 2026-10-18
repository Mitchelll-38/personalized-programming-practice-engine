"""Bounded deterministic CPU content fitting; supplied partitions, no data loading."""

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn

from practice_engine.evaluation import evaluate
from practice_engine.models.content_inputs import ConceptVocabulary, make_content_batch
from practice_engine.models.content_lstm import ContentLSTM
from practice_engine.models.embedding_cache import EncoderConfig


@dataclass(frozen=True)
class ContentTrainingConfig:
    seed: int = 38
    max_epochs: int = 30
    patience: int = 5
    batch_size: int = 32
    projection_size: int = 32
    concept_size: int = 16
    correctness_size: int = 8
    hidden_size: int = 64
    learning_rate: float = .01

    def __post_init__(self):
        for name, upper in (("seed", 2**32 - 1), ("max_epochs", 500), ("patience", 500),
                            ("batch_size", 256), ("projection_size", 256), ("concept_size", 128),
                            ("correctness_size", 32), ("hidden_size", 256)):
            value = getattr(self, name)
            if type(value) is not int or not (0 if name == "seed" else 1) <= value <= upper:
                raise ValueError(f"Invalid bounded integer configuration: {name}")
        if (isinstance(self.learning_rate, bool) or not isinstance(self.learning_rate, (int, float))
                or not 0 < self.learning_rate <= 1 or not math.isfinite(self.learning_rate)):
            raise ValueError("learning_rate must be finite in (0, 1]")


@dataclass(frozen=True)
class ContentEpoch:
    epoch: int
    training_bce: float
    validation_log_loss: float


@dataclass(frozen=True)
class ContentFit:
    model: ContentLSTM
    vocabulary: ConceptVocabulary
    validation_probabilities: tuple[float, ...]
    epochs: tuple[ContentEpoch, ...]
    best_epoch: int


def _validation_probabilities(model, rows, vocabulary, entries, encoder, batch_size):
    model.eval()
    probabilities = []
    with torch.inference_mode():
        for start in range(0, len(rows), batch_size):
            batch = make_content_batch(rows[start:start + batch_size], vocabulary, entries, encoder)
            probabilities.extend(torch.sigmoid(model(batch.inputs)).tolist())
    return probabilities


def _fit(train, validation, entries, encoder, config):
    vocabulary = ConceptVocabulary.fit(train)
    if vocabulary.size > 10000 or encoder.dimension > 4096:
        raise ValueError("Content fit exceeds checkpoint vocabulary/input bounds")
    model = ContentLSTM(vocabulary.size, input_size=encoder.dimension,
        projection_size=config.projection_size, concept_size=config.concept_size,
        correctness_size=config.correctness_size, hidden_size=config.hidden_size).float()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.BCEWithLogitsLoss()
    epochs, best_state, best_loss, best_epoch, stale = [], None, math.inf, 0, 0
    for epoch in range(1, config.max_epochs + 1):
        model.train()
        indices = torch.randperm(len(train)).tolist()
        loss_sum = 0.
        for start in range(0, len(indices), config.batch_size):
            rows = [train[index] for index in indices[start:start + config.batch_size]]
            batch = make_content_batch(rows, vocabulary, entries, encoder)
            optimizer.zero_grad()
            loss = criterion(model(batch.inputs), batch.labels)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite content training loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5., error_if_nonfinite=True)
            optimizer.step()
            loss_sum += loss.item() * len(rows)
        probabilities = _validation_probabilities(model, validation, vocabulary, entries, encoder, config.batch_size)
        validation_loss = evaluate(validation, probabilities)["aggregate"]["log_loss"]
        epochs.append(ContentEpoch(epoch, loss_sum / len(train), validation_loss))
        if validation_loss < best_loss:
            best_loss, best_epoch, stale = validation_loss, epoch, 0
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        else:
            stale += 1
            if stale >= config.patience:
                break
    model.load_state_dict(best_state)
    probabilities = _validation_probabilities(model, validation, vocabulary, entries, encoder, config.batch_size)
    return ContentFit(model, vocabulary, tuple(probabilities), tuple(epochs), best_epoch)


def fit_content(train, validation, entries, encoder: EncoderConfig, *, config=None) -> ContentFit:
    """Caller owns partition/provenance verification; never supply held-out test rows."""
    config = ContentTrainingConfig() if config is None else config
    if not isinstance(config, ContentTrainingConfig) or not isinstance(encoder, EncoderConfig):
        raise ValueError("Typed content configuration and encoder required")
    config = ContentTrainingConfig(**asdict(config))
    encoder = EncoderConfig.model_validate(encoder.model_dump())
    if any(not isinstance(rows, (list, tuple)) or not rows for rows in (train, validation)):
        raise ValueError("Nonempty train and validation sequences required")
    previous_threads = torch.get_num_threads()
    previous_determinism = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(config.seed)
            return _fit(train, validation, entries, encoder, config)
    finally:
        torch.use_deterministic_algorithms(previous_determinism, warn_only=previous_warn_only)
        torch.set_num_threads(previous_threads)
