"""Causal content-conditioned LSTM logits from frozen vector batches."""

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

from .content_inputs import ContentInputs, PAD, UNK


class ContentLSTM(nn.Module):
    def __init__(self, concept_vocabulary_size: int, *, input_size: int = 768,
                 projection_size: int = 32, concept_size: int = 16,
                 correctness_size: int = 8, hidden_size: int = 64):
        super().__init__()
        for value, minimum in ((concept_vocabulary_size, 3), (input_size, 1), (projection_size, 1),
                               (concept_size, 1), (correctness_size, 1), (hidden_size, 1)):
            if type(value) is not int or value < minimum:
                raise ValueError("Vocabulary must include PAD/UNK/known tags; dimensions must be positive integers")
        self.problem = nn.Linear(input_size, projection_size)
        self.code = nn.Linear(input_size, projection_size)
        self.concepts = nn.Embedding(concept_vocabulary_size, concept_size, padding_idx=PAD)
        self.correctness = nn.Embedding(2, correctness_size)
        self.lstm = nn.LSTM(2 * projection_size + concept_size + correctness_size + 1,
                            hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size + projection_size + concept_size, 1)

    def _validate(self, inputs):
        if not isinstance(inputs, ContentInputs):
            raise ValueError("ContentInputs are required; labels are not forward features")
        hp, hc, present, tags, correct, lengths, cp, candidate_tags = (
            inputs.history_problem, inputs.history_code, inputs.history_code_present,
            inputs.history_concepts, inputs.history_correct, inputs.lengths,
            inputs.candidate_problem, inputs.candidate_concepts)
        if any(not isinstance(t, torch.Tensor) for t in (hp, hc, present, tags, correct, lengths, cp, candidate_tags)):
            raise ValueError("Content inputs must be tensors")
        if (hp.ndim != 3 or min(hp.shape[:2]) < 1 or hp.shape[-1] != self.problem.in_features
                or hc.shape != hp.shape or present.shape != hp.shape[:2] or correct.shape != hp.shape[:2]
                or lengths.shape != (hp.shape[0],) or cp.shape != (hp.shape[0], hp.shape[2])
                or tags.ndim != 3 or tags.shape[:2] != hp.shape[:2] or tags.shape[2] < 1
                or candidate_tags.ndim != 2 or candidate_tags.shape[0] != hp.shape[0] or candidate_tags.shape[1] < 1):
            raise ValueError("Content input dimensions do not match the model/batch")
        if (any(t.device != self.problem.weight.device for t in (hp, hc, present, tags, correct, lengths, cp, candidate_tags))
                or any(t.dtype != self.problem.weight.dtype for t in (hp, hc, cp))
                or any(t.dtype != torch.long for t in (tags, correct, lengths, candidate_tags))
                or present.dtype != torch.bool):
            raise ValueError("Content inputs require matching model dtype/device and integer IDs/lengths")
        if torch.any((lengths < 0) | (lengths > hp.shape[1])):
            raise ValueError("History lengths must fit the padded width")
        observed = torch.arange(hp.shape[1], device=hp.device)[None, :] < lengths[:, None]
        valid_tags = (tags >= PAD) & (tags < self.concepts.num_embeddings)
        if (torch.any(observed.unsqueeze(-1) & ~valid_tags)
                or torch.any((candidate_tags < PAD) | (candidate_tags >= self.concepts.num_embeddings))
                or torch.any(observed & ~(tags > PAD).any(-1)) or torch.any(~(candidate_tags > PAD).any(-1))
                or torch.any(observed & ((correct < 0) | (correct > 1)))):
            raise ValueError("Observed concept IDs and historical outcomes are invalid")
        if (not torch.isfinite(hp[observed]).all() or not torch.isfinite(hc[observed & present]).all()
                or not torch.isfinite(cp).all()):
            raise ValueError("Observed frozen vectors must be finite")
        return observed

    def _concept_mean(self, tags):
        known = tags > UNK
        ids = torch.where(known, tags, PAD)
        # UNK has no training observations after train-only vocabulary fitting.
        # Ignoring it avoids a random untrained concept representation.
        embeddings = self.concepts(ids).masked_fill(~known.unsqueeze(-1), 0)
        return embeddings.sum(-2) / known.sum(-1, keepdim=True).clamp_min(1)

    def forward(self, inputs: ContentInputs) -> torch.Tensor:
        observed = self._validate(inputs)
        hp = torch.where(observed.unsqueeze(-1), inputs.history_problem.detach(), 0)
        code_observed = observed & inputs.history_code_present
        hc = torch.where(code_observed.unsqueeze(-1), inputs.history_code.detach(), 0)
        tags = torch.where(observed.unsqueeze(-1), inputs.history_concepts, PAD)
        correct = torch.where(observed, inputs.history_correct, 0)
        code = self.code(hc).masked_fill(~code_observed.unsqueeze(-1), 0)
        history = torch.cat((self.problem(hp), code, self._concept_mean(tags),
                             self.correctness(correct), code_observed.unsqueeze(-1).to(hp.dtype)), dim=-1)
        hidden = hp.new_zeros((hp.shape[0], self.lstm.hidden_size))
        active = (inputs.lengths > 0).nonzero(as_tuple=True)[0]
        if active.numel():
            packed = pack_padded_sequence(history[active], inputs.lengths[active].cpu(),
                                          batch_first=True, enforce_sorted=False)
            _, (last, _) = self.lstm(packed)
            hidden = hidden.index_copy(0, active, last[-1])
        candidate = self.problem(inputs.candidate_problem.detach())
        logits = self.head(torch.cat((hidden, candidate, self._concept_mean(inputs.candidate_concepts)), dim=-1)).squeeze(-1)
        if not torch.isfinite(logits).all():
            raise ValueError("Content model produced nonfinite logits")
        return logits
